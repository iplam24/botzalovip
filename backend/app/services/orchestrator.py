"""Bộ điều phối AI - pipeline rút gọn nhưng thật (19 bước gốc được gom nhóm có log).
1 validate, 2 dedup external_message_id, 3 customer, 4 conversation, 5 automation check (bot paused/human),
6 intent, 7 entities (lấy từ khóa), 8-9 retrieve knowledge+memory+service, 10 policy, 11 chọn model,
12 generate, 13 output check, 14 action check, 15 quyết định gửi/chuyển, 16 send qua connector,
17 lưu, 18 cập nhật memory, 19 log/usage.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..models import Customer, Conversation, Message, SystemLog, ServiceItem
from .text_utils import classify_intent, normalize_vi
from . import knowledge_service, memory_service, ai_gateway, automation_service, extraction_service, notification_service
from .zalo_connector import mock_connector, ZaloPersonalConnector

CAU_HOI_SDT = "Anh/chị cho em xin số điện thoại để tư vấn viên liên hệ tư vấn chi tiết hơn ạ."

def _thong_bao(db, loai, title, content, cust=None, conv=None, level="thong_tin", channel="mo_phong"):
    """Tạo thông báo admin — bọc try/except ở notification_service, không chặn pipeline."""
    try:
        notification_service.notify(db, loai, title, content,
                                    customer_id=cust.id if cust else None,
                                    conversation_id=conv.id if conv else None,
                                    level=level, channel=channel)
    except Exception:
        pass

def _da_hoi_sdt(db, conversation_id) -> bool:
    """Đã hỏi xin SĐT trong hội thoại này chưa (đánh dấu bằng SystemLog module thu_thap)."""
    return db.query(SystemLog).filter(
        SystemLog.module == "thu_thap",
        SystemLog.message == f"da_hoi_sdt conv={conversation_id}",
    ).first() is not None

def _ghi_da_hoi_sdt(db, conversation_id, trace=""):
    db.add(SystemLog(level="info", module="thu_thap", message=f"da_hoi_sdt conv={conversation_id}", trace_id=trace)); db.commit()

def process_inbound(db: Session, external_id: str, customer_external_id: str, customer_name: str, content: str, zalo_account_id=None, channel: str = "mo_phong"):
    trace = str(uuid.uuid4())[:8]
    # Dedup trước khi tạo
    if external_id and db.query(Message).filter(Message.external_id == external_id).first():
        db.add(SystemLog(level="warning", module="orchestrator", message=f"Tin trùng bị bỏ qua {external_id}", trace_id=trace)); db.commit()
        return {"trung": True, "trace_id": trace, "tra_loi": None}
    cust = db.query(Customer).filter(Customer.external_id == customer_external_id).first()
    khach_moi = False
    if not cust:
        cust = Customer(external_id=customer_external_id, display_name=customer_name); db.add(cust); db.commit(); db.refresh(cust)
        khach_moi = True
    conv = db.query(Conversation).filter(Conversation.customer_id == cust.id).order_by(Conversation.created_at.desc()).first()
    if not conv or conv.status == "da_giai_quyet":
        conv = Conversation(customer_id=cust.id, zalo_account_id=zalo_account_id, channel=channel); db.add(conv); db.commit(); db.refresh(conv)
    elif getattr(conv, "channel", None) != channel:
        # Hội thoại cũ tạo từ kênh khác: cập nhật theo nguồn tin mới nhất
        conv.channel = channel; db.commit()
    msg = Message(conversation_id=conv.id, external_id=external_id, sender_type="khach", content=content, status="da_nhan")
    db.add(msg)
    try: db.commit()
    except IntegrityError:
        db.rollback(); return {"trung": True, "trace_id": trace, "tra_loi": None}
    db.add(SystemLog(level="info", module="orchestrator", message=f"Nhận tin từ {cust.display_name}: {content[:80]}", trace_id=trace)); db.commit()
    cust.last_interaction_at = msg.created_at or datetime.now(timezone.utc); db.commit()
    # GĐ mở rộng 1: thông báo khách mới + tự thu thập thông tin từ tin nhắn.
    # Chạy kể cả khi bot đang tạm dừng (thu thập dữ liệu độc lập với trả lời);
    # mọi lỗi ở bước này chỉ ghi log, không chặn pipeline.
    if khach_moi:
        _thong_bao(db, "khach_moi", "Khách hàng mới", f"Khách {cust.display_name or cust.external_id} vừa nhắn tin lần đầu qua kênh {channel}.", cust, conv, "thong_tin", channel)
    try:
        kq_thu_thap = extraction_service.extract_and_save(db, cust, msg)
        ten_khach = cust.display_name or cust.external_id
        if kq_thu_thap.get("sdt_moi"):
            _thong_bao(db, "co_so_dien_thoai", "Khách đã để lại số điện thoại", f"Khách {ten_khach} đã cung cấp số điện thoại {cust.phone}.", cust, conv, "thong_tin", channel)
        if kq_thu_thap.get("du_thong_tin_moi"):
            _thong_bao(db, "du_thong_tin", "Đã thu thập đủ thông tin khách", f"Khách {ten_khach} đã có đủ thông tin cơ bản (số điện thoại + nhu cầu/dịch vụ quan tâm).", cust, conv, "thong_tin", channel)
    except Exception as e:
        db.add(SystemLog(level="warning", module="thu_thap", message=f"Lỗi trích xuất thông tin khách: {e}", trace_id=trace)); db.commit()
    # Automation check: bot tạm dừng hoặc nhân viên tiếp quản -> không trả lời tự động
    if not conv.bot_enabled or conv.human_takeover:
        return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "bot_da_tam_dung_hoac_nhan_vien_tiep_quan", "conversation_id": conv.id, "customer_id": cust.id}
    intent = classify_intent(content)
    if intent == "khieu_nai":
        _thong_bao(db, "khieu_nai", "Khách hàng khiếu nại", f"Khách {cust.display_name or cust.external_id} có dấu hiệu khiếu nại: {content[:120]}", cust, conv, "canh_bao", channel)
    if intent == "gap_nhan_vien":
        _thong_bao(db, "gap_nhan_vien", "Khách yêu cầu gặp nhân viên", f"Khách {cust.display_name or cust.external_id} yêu cầu gặp nhân viên: {content[:120]}", cust, conv, "canh_bao", channel)
        conv.human_takeover = True; db.commit()
        return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "chuyen_nhan_vien_theo_yeu_cau", "conversation_id": conv.id, "customer_id": cust.id, "intent": intent}
    rule = automation_service.evaluate_rules(db, conv, content, intent)
    if rule:
        if rule.action_type == "tra_loi" and rule.action_value:
            return _send_reply(db, conv, cust, rule.action_value, trace, rule=rule, channel=channel)
        if rule.action_type == "gan_nhan":
            conv.labels = (conv.labels + "," + rule.action_value).strip(","); db.commit()
        if rule.action_type == "chuyen_nhan_vien":
            _thong_bao(db, "gap_nhan_vien", "Khách được chuyển cho nhân viên theo quy tắc", f"Quy tắc tự động hóa đã chuyển hội thoại của khách {cust.display_name or cust.external_id} cho nhân viên.", cust, conv, "canh_bao", channel)
            conv.human_takeover = True; db.commit(); return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "quy_tac_chuyen_nhan_vien", "conversation_id": conv.id, "customer_id": cust.id}
        if rule.action_type == "tam_dung_bot":
            conv.bot_enabled = False; db.commit(); return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "quy_tac_tam_dung_bot", "conversation_id": conv.id, "customer_id": cust.id}
    chunks = knowledge_service.retrieve(db, content, limit=5)
    # Dịch vụ liên quan: cộng điểm nếu tên dịch vụ xuất hiện
    for s in db.query(ServiceItem).filter(ServiceItem.is_active == True).all():
        if normalize_vi(s.name) in normalize_vi(content) and s.description:
            chunks = [{"document_id": None, "title": s.name, "content": f"{s.name}: {s.description} Giá: {s.price_text or s.price}", "score": 99}] + chunks
            break
    memories = memory_service.retrieve_memories(db, cust.id, content, limit=3)
    # GĐ mở rộng 1: khách chưa có SĐT + intent tư vấn/báo giá -> hỏi xin SĐT,
    # tối đa 1 lần cho mỗi hội thoại. Provider thật: gợi ý trong prompt;
    # Mock: nối hậu tố vào câu trả lời (vẫn chỉ 1 tin bot duy nhất).
    chuoi_chuan = normalize_vi(content)
    can_hoi_sdt = (not (cust.phone or "").strip()) and (
        intent == "hoi_gia" or "tu van" in chuoi_chuan or "bao gia" in chuoi_chuan)
    hoi_sdt = can_hoi_sdt and not _da_hoi_sdt(db, conv.id)
    provider = ai_gateway.get_default_provider(db)
    la_mock = (not provider) or provider.provider == "mock"
    try:
        reply, model_used = ai_gateway.generate_reply(db, provider, content, chunks, memories, goi_y_hoi_sdt=(hoi_sdt and not la_mock))
    except ai_gateway.AIError as e:
        db.add(SystemLog(level="error", module="orchestrator", message=f"Lỗi AI: {e}", trace_id=trace)); db.commit()
        _thong_bao(db, "bot_khong_tra_loi_duoc", "Bot không trả lời được", f"Bot không trả lời được khách {cust.display_name or cust.external_id} do lỗi nhà cung cấp AI: {e}", cust, conv, "canh_bao", channel)
        return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": f"loi_provider: {e}", "conversation_id": conv.id, "customer_id": cust.id}
    if hoi_sdt:
        if la_mock:
            reply = (reply or "").rstrip() + "\n" + CAU_HOI_SDT
        _ghi_da_hoi_sdt(db, conv.id, trace)
    # Policy check đơn giản: không hứa hẹn ngoài dữ liệu - nếu không có nguồn và câu hỏi giá thì vẫn trả lời mẫu 'chưa đủ thông tin' từ mock
    return _send_reply(db, conv, cust, reply, trace, chunks=chunks, model_used=model_used, intent=intent, channel=channel)

def _send_reply(db, conv, cust, reply, trace, chunks=None, model_used="", rule=None, intent="", channel="mo_phong"):
    # Chọn connector theo kênh THẬT của hội thoại. Bản trước luôn gửi qua Mock
    # nên tin từ Zalo cá nhân không bao giờ tới được khách (đã xảy ra thật 22/10/2026).
    try:
        if channel == "ca_nhan":
            # thread của zca-js với khách 1-1 chính là external_id của khách
            ZaloPersonalConnector().send_text(str(cust.external_id), reply)
        else:
            mock_connector.send_text(str(conv.id), reply)
    except Exception as e:
        out = Message(conversation_id=conv.id, external_id=None, sender_type="bot", content=reply, status="loi_gui", error=str(e))
        db.add(out)
        db.add(SystemLog(level="error", module="zalo", message=f"Lỗi gửi tin qua kênh {channel}: {e}", trace_id=trace)); db.commit()
        _thong_bao(db, "loi_he_thong", "Lỗi gửi tin qua connector", f"Gửi tin cho khách {cust.display_name or cust.external_id} qua kênh {channel} thất bại: {e}", cust, conv, "khan_cap", channel)
        return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": f"loi_connector: {e}", "conversation_id": conv.id, "customer_id": cust.id}
    out = Message(conversation_id=conv.id, external_id=None, sender_type="bot", content=reply, status="da_gui")
    db.add(out); db.commit()
    # Cập nhật bộ nhớ: ghi sự kiện tương tác
    memory_service.remember(db, cust.id, f"Khách đã hỏi và được trả lời: {reply[:120]}", memory_type="su_kien", source="orchestrator", confidence=0.7)
    db.add(SystemLog(level="info", module="orchestrator", message=f"Đã trả lời hội thoại {conv.id} model={model_used}", trace_id=trace)); db.commit()
    return {"trung": False, "trace_id": trace, "tra_loi": reply, "conversation_id": conv.id, "customer_id": cust.id, "intent": intent, "nguon": chunks or [], "model": model_used}
