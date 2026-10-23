"""Bộ điều phối AI - pipeline rút gọn nhưng thật (19 bước gốc được gom nhóm có log).
1 validate, 2 dedup external_message_id, 3 customer, 4 conversation, 5 automation check (bot paused/human),
6 intent, 7 entities (lấy từ khóa), 8-9 retrieve knowledge+memory+service, 10 policy, 11 chọn model,
12 generate, 13 output check, 14 action check, 15 quyết định gửi/chuyển, 16 send qua connector,
17 lưu, 18 cập nhật memory, 19 log/usage.

Đợt nâng cấp 2 bổ sung (mọi ngưỡng/hành vi đều đọc RUNTIME từ Cài đặt):
- Mục 7: tin NHÓM chỉ được trả lời khi bot được tag đích danh (mention chứa
  UID của bot hoặc tên bot cấu hình); tag @all (uid -1) không tính; bị bỏ qua
  thì ghi log "bo_qua_nhom_khong_tag".
- Mục 10: truyền lịch sử hội thoại đa lượt cho AI + prompt persona theo Cài đặt.
- Mục 5+6: chuẩn hoá định dạng Zalo rồi chia nhỏ tin khi gửi qua kênh cá nhân.
- Mục 4: thả tim tin khách (bot_tha_tim) qua connector cá nhân.
- Mục 9.5: khách là bạn bè Zalo đã phân bổ -> gắn admin phụ trách.
- Gate theo Cài đặt: giờ hoạt động, từ khóa cấm, ngưỡng chuyển nhân viên,
  bật/tắt module (thu thập / tự động hóa / bộ nhớ / trả lời toàn cục).
- Chế độ TRÒ CHUYỆN TỰ DO (che_do_tro_chuyen_tu_do): bỏ qua tri thức/dịch vụ/
  bộ nhớ tư vấn, tắt hỏi SĐT + tắt thông báo lead; luật nhóm, từ khóa cấm,
  chuyển nhân viên, thả tim, chia tin, định dạng Zalo vẫn áp dụng như thường.
"""
import os
import time
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..models import Customer, Conversation, Message, SystemLog, ServiceItem, User, PhanBoBanBe
from .text_utils import classify_intent, normalize_vi
from . import knowledge_service, memory_service, ai_gateway, automation_service, extraction_service, notification_service, anh_service
from .zalo_connector import mock_connector, ZaloPersonalConnector
from .dinh_dang import dinh_dang_tin_zalo, chia_tin_nhan

CAU_HOI_SDT_MAC_DINH = "Anh/chị cho em xin số điện thoại để tư vấn viên liên hệ tư vấn chi tiết hơn ạ."


def _doc_cai_dat(db: Session) -> dict:
    try:
        from ..routers.cai_dat import doc_cai_dat
        return doc_cai_dat(db)
    except Exception:
        return {}


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


def _tach_danh_sach(tho: str):
    if not tho:
        return []
    return [p.strip() for p in str(tho).replace("\n", ",").split(",") if p.strip()]


def _duoc_tra_loi_trong_nhom(cai_dat: dict, content: str, mentions, bot_uid: str, thread_id: str) -> bool:
    """Mục 7: trong nhóm, bot chỉ trả lời khi được tag ĐÍCH DANH.

    - Mention chứa đúng UID của tài khoản bot (bot_uid) -> được trả lời.
    - Mention @all (uid "-1") KHÔNG tính là tag bot.
    - Hoặc nội dung chứa tên bot đã cấu hình (ten_bot_trong_nhom).
    - Danh sách nhóm được phép (danh_sach_nhom_duoc_phep) khác rỗng thì
      nhóm ngoài danh sách bị chặn kể cả khi tag đúng.
    """
    phep = _tach_danh_sach(cai_dat.get("danh_sach_nhom_duoc_phep"))
    if phep and str(thread_id) not in phep:
        return False
    if cai_dat.get("bot_nhom_chi_khi_duoc_tag", True) is False:
        return True
    uids = set()
    for m in (mentions or []):
        if isinstance(m, dict) and m.get("uid") is not None:
            uids.add(str(m["uid"]))
    if bot_uid and str(bot_uid) in uids:
        return True
    ten_bot = str(cai_dat.get("ten_bot_trong_nhom") or "").strip()
    if ten_bot and normalize_vi(ten_bot) in normalize_vi(content or ""):
        return True
    return False


def _trong_gio_lam_viec(cai_dat: dict) -> bool:
    bat = cai_dat.get("gio_hoat_dong_bat_dau", 0)
    ket = cai_dat.get("gio_hoat_dong_ket_thuc", 24)
    try:
        bat = int(bat); ket = int(ket)
    except (TypeError, ValueError):
        return True
    if bat == ket:
        return True
    try:
        from zoneinfo import ZoneInfo
        bay_gio = datetime.now(ZoneInfo(str(cai_dat.get("mui_gio") or "Asia/Ho_Chi_Minh")))
    except Exception:
        bay_gio = datetime.now(timezone.utc)
    gio = bay_gio.hour
    return (bat <= gio < ket) if bat < ket else (gio >= bat or gio < ket)


def _gan_admin_tu_ban_be(db: Session, cust: Customer, conv: Conversation, customer_external_id: str):
    """Mục 9.5: nếu người nhắn là bạn bè Zalo đã được phân bổ admin và
    khách/hội thoại CHƯA có người phụ trách -> gắn admin phụ trách đó."""
    try:
        pb = db.query(PhanBoBanBe).filter(PhanBoBanBe.zalo_friend_id == str(customer_external_id)).first()
        if not pb or not pb.admin_user_id:
            return
        admin_u = db.get(User, pb.admin_user_id)
        if not admin_u:
            return
        ten = admin_u.username or admin_u.full_name or admin_u.email
        thay_doi = False
        if not (cust.assignee or "").strip():
            cust.assignee = ten; thay_doi = True
        if not (conv.assignee or "").strip():
            conv.assignee = ten; thay_doi = True
        if thay_doi:
            db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


def process_inbound(db: Session, external_id: str, customer_external_id: str, customer_name: str, content: str,
                    zalo_account_id=None, channel: str = "mo_phong",
                    mentions=None, la_nhom: bool = False, bot_uid: str = "",
                    nguoi_gui_id: str = "", cli_msg_id: str = "", dinh_kem=None):
    trace = str(uuid.uuid4())[:8]
    cai_dat = _doc_cai_dat(db)
    # Chế độ trò chuyện tự do: bot nghỉ bán hàng — không hỏi SĐT, không báo
    # lead (co_so_dien_thoai/du_thong_tin), không chèn tri thức/doanh nghiệp.
    tu_do = bool(cai_dat.get("che_do_tro_chuyen_tu_do"))
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
    _gan_admin_tu_ban_be(db, cust, conv, customer_external_id)
    msg = Message(conversation_id=conv.id, external_id=external_id, sender_type="khach", content=content, status="da_nhan")
    db.add(msg)
    try: db.commit()
    except IntegrityError:
        db.rollback(); return {"trung": True, "trace_id": trace, "tra_loi": None}
    db.refresh(msg)
    db.add(SystemLog(level="info", module="orchestrator", message=f"Nhận tin từ {cust.display_name}: {content[:80]}", trace_id=trace)); db.commit()
    cust.last_interaction_at = msg.created_at or datetime.now(timezone.utc); db.commit()
    # Đính kèm ẢNH khách gửi: tải về máy chủ (thư mục uploads) để bot "nhìn"
    # được ảnh qua payload multimodal + admin xem lại được trong Hội thoại.
    # Tải lỗi → vẫn lưu URL gốc của Zalo; mọi lỗi ở bước này KHÔNG chặn pipeline.
    anh_data_uri = ""
    for dk in (dinh_kem or []):
        if not isinstance(dk, dict) or dk.get("loai") != "anh" or not dk.get("url"):
            continue
        msg.attachment_type = "anh"
        kq_tai = None
        try:
            kq_tai = anh_service.tai_anh_tu_url(str(dk["url"]))
        except Exception:
            kq_tai = None
        if kq_tai:
            msg.attachment_url = f"/api/tep/{kq_tai['ten_file']}"
            try:
                anh_data_uri = anh_service.doc_anh_data_uri(kq_tai["duong_dan"])
            except Exception:
                anh_data_uri = ""
        else:
            msg.attachment_url = str(dk["url"])
        try:
            db.commit()
        except Exception:
            db.rollback()
        break
    # Mục 7: cổng nhóm Zalo — không được tag đích danh thì IM LẶNG (đã lưu tin
    # + ghi log), không thu thập, không thông báo, không trả lời, không thả tim.
    if la_nhom:
        uid_bot = str(bot_uid or "")
        if not uid_bot and channel == "ca_nhan":
            try:
                uid_bot = str(ZaloPersonalConnector().status().get("tai_khoan_id") or "")
            except Exception:
                uid_bot = ""
        if not _duoc_tra_loi_trong_nhom(cai_dat, content, mentions, uid_bot, str(customer_external_id)):
            db.add(SystemLog(level="info", module="orchestrator",
                             message=f"bo_qua_nhom_khong_tag thread={customer_external_id} conv={conv.id}",
                             trace_id=trace)); db.commit()
            return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "bo_qua_nhom_khong_tag",
                    "bo_qua": True, "conversation_id": conv.id, "customer_id": cust.id}
    # GĐ mở rộng 1: thông báo khách mới + tự thu thập thông tin từ tin nhắn.
    # Chạy kể cả khi bot đang tạm dừng (thu thập độc lập với trả lời);
    # mọi lỗi ở bước này chỉ ghi log, không chặn pipeline.
    if khach_moi:
        _thong_bao(db, "khach_moi", "Khách hàng mới", f"Khách {cust.display_name or cust.external_id} vừa nhắn tin lần đầu qua kênh {channel}.", cust, conv, "thong_tin", channel)
    if cai_dat.get("module_thu_thap_thong_tin", True) is not False:
        try:
            kq_thu_thap = extraction_service.extract_and_save(db, cust, msg)
            ten_khach = cust.display_name or cust.external_id
            # Đang chat giải trí (chế độ tự do) thì KHÔNG báo lead làm phiền admin
            if kq_thu_thap.get("sdt_moi") and not tu_do:
                _thong_bao(db, "co_so_dien_thoai", "Khách đã để lại số điện thoại", f"Khách {ten_khach} đã cung cấp số điện thoại {cust.phone}.", cust, conv, "thong_tin", channel)
            if kq_thu_thap.get("du_thong_tin_moi") and not tu_do:
                _thong_bao(db, "du_thong_tin", "Đã thu thập đủ thông tin khách", f"Khách {ten_khach} đã có đủ thông tin cơ bản theo các trường bắt buộc đã cấu hình.", cust, conv, "thong_tin", channel)
        except Exception as e:
            db.add(SystemLog(level="warning", module="thu_thap", message=f"Lỗi trích xuất thông tin khách: {e}", trace_id=trace)); db.commit()
    # Automation check: bot tạm dừng hoặc nhân viên tiếp quản -> không trả lời tự động
    if not conv.bot_enabled or conv.human_takeover:
        return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "bot_da_tam_dung_hoac_nhan_vien_tiep_quan", "conversation_id": conv.id, "customer_id": cust.id}
    if cai_dat.get("tu_dong_tra_loi_toan_cuc", True) is False:
        return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "tat_tra_loi_toan_cuc", "conversation_id": conv.id, "customer_id": cust.id}
    # Giờ hoạt động: ngoài giờ -> gửi câu ngoài giờ (nếu có) hoặc im lặng
    if not _trong_gio_lam_viec(cai_dat):
        cau_ngoai_gio = str(cai_dat.get("cau_tra_loi_ngoai_gio") or "").strip()
        if cau_ngoai_gio:
            return _send_reply(db, conv, cust, cau_ngoai_gio, trace, channel=channel, cai_dat=cai_dat,
                               tin_khach=_tin_khach(customer_external_id, external_id, cli_msg_id, la_nhom))
        return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "ngoai_gio_lam_viec", "conversation_id": conv.id, "customer_id": cust.id}
    # Từ khóa cấm: bot không tự trả lời, chỉ ghi log cho nhân viên
    chuoi_chuan = normalize_vi(content)
    for tu_cam in _tach_danh_sach(cai_dat.get("tu_khoa_cam")):
        if tu_cam and normalize_vi(tu_cam) in chuoi_chuan:
            db.add(SystemLog(level="warning", module="orchestrator", message=f"Tin chứa từ khóa cấm '{tu_cam}' conv={conv.id} - bot không trả lời", trace_id=trace)); db.commit()
            return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "chua_tu_khoa_cam", "conversation_id": conv.id, "customer_id": cust.id}
    intent = classify_intent(content)
    if intent == "khieu_nai":
        _thong_bao(db, "khieu_nai", "Khách hàng khiếu nại", f"Khách {cust.display_name or cust.external_id} có dấu hiệu khiếu nại: {content[:120]}", cust, conv, "canh_bao", channel)
    if intent == "gap_nhan_vien":
        db.add(SystemLog(level="info", module="orchestrator", message=f"yeu_cau_gap_nhan_vien conv={conv.id}", trace_id=trace)); db.commit()
        so_lan = db.query(SystemLog).filter(
            SystemLog.module == "orchestrator",
            SystemLog.message == f"yeu_cau_gap_nhan_vien conv={conv.id}").count()
        try:
            nguong = int(cai_dat.get("so_lan_yeu_cau_gap_nhan_vien_de_chuyen") or 1)
        except (TypeError, ValueError):
            nguong = 1
        if so_lan >= max(1, nguong):
            _thong_bao(db, "gap_nhan_vien", "Khách yêu cầu gặp nhân viên", f"Khách {cust.display_name or cust.external_id} yêu cầu gặp nhân viên: {content[:120]}", cust, conv, "canh_bao", channel)
            conv.human_takeover = True; db.commit()
            return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "chuyen_nhan_vien_theo_yeu_cau", "conversation_id": conv.id, "customer_id": cust.id, "intent": intent}
        # Chưa đủ ngưỡng: bot tiếp tục hỗ trợ trước, chuyển thật khi đủ số lần yêu cầu
        db.add(SystemLog(level="info", module="orchestrator", message=f"Khách yêu cầu gặp nhân viên lần {so_lan}/{nguong} conv={conv.id} - bot tiếp tục hỗ trợ", trace_id=trace)); db.commit()
    rule = None
    if cai_dat.get("module_tu_dong_hoa", True) is not False:
        rule = automation_service.evaluate_rules(db, conv, content, intent)
    if rule:
        if rule.action_type == "tra_loi" and rule.action_value:
            return _send_reply(db, conv, cust, rule.action_value, trace, rule=rule, channel=channel, cai_dat=cai_dat,
                               tin_khach=_tin_khach(customer_external_id, external_id, cli_msg_id, la_nhom))
        if rule.action_type == "gan_nhan":
            conv.labels = (conv.labels + "," + rule.action_value).strip(","); db.commit()
        if rule.action_type == "chuyen_nhan_vien":
            _thong_bao(db, "gap_nhan_vien", "Khách được chuyển cho nhân viên theo quy tắc", f"Quy tắc tự động hóa đã chuyển hội thoại của khách {cust.display_name or cust.external_id} cho nhân viên.", cust, conv, "canh_bao", channel)
            conv.human_takeover = True; db.commit(); return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "quy_tac_chuyen_nhan_vien", "conversation_id": conv.id, "customer_id": cust.id}
        if rule.action_type == "tam_dung_bot":
            conv.bot_enabled = False; db.commit(); return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "quy_tac_tam_dung_bot", "conversation_id": conv.id, "customer_id": cust.id}
    # Chế độ tự do: KHÔNG truy xuất tri thức/dịch vụ/bộ nhớ tư vấn — chat thuần.
    chunks = []
    memories = []
    if not tu_do:
        chunks = knowledge_service.retrieve(db, content, limit=5)
        # Dịch vụ liên quan: cộng điểm nếu tên dịch vụ xuất hiện
        for s in db.query(ServiceItem).filter(ServiceItem.is_active == True).all():
            if normalize_vi(s.name) in normalize_vi(content) and s.description:
                chunks = [{"document_id": None, "title": s.name, "content": f"{s.name}: {s.description} Giá: {s.price_text or s.price}", "score": 99}] + chunks
                break
        if cai_dat.get("module_bo_nho_ai", True) is not False:
            memories = memory_service.retrieve_memories(db, cust.id, content, limit=3)
    # GĐ mở rộng 1 + registry: khách chưa có SĐT + intent/từ khóa cấu hình ->
    # hỏi xin SĐT, tối đa 1 lần cho mỗi hội thoại (tắt được bằng thu_thap_tu_hoi_sdt).
    # Chế độ tự do: KHÔNG hỏi SĐT (đang chat bạn bè, hỏi số là phá vibe).
    intent_hoi = _tach_danh_sach(cai_dat.get("thu_thap_intent_hoi_sdt"))
    tu_khoa_hoi = _tach_danh_sach(cai_dat.get("thu_thap_tu_khoa_hoi_sdt"))
    kich_hoat_hoi = (not intent_hoi and not tu_khoa_hoi) or intent in intent_hoi or any(
        normalize_vi(tk) in chuoi_chuan for tk in tu_khoa_hoi)
    can_hoi_sdt = (not (cust.phone or "").strip()) and kich_hoat_hoi
    hoi_sdt = (not tu_do) and (cai_dat.get("thu_thap_tu_hoi_sdt", True) is not False) and can_hoi_sdt and not _da_hoi_sdt(db, conv.id)
    # PR chủ động: danh sách dịch vụ đang mở bán để tiêm vào prompt tư vấn
    # (chỉ chế độ tư vấn; giá 0 và không có giá chữ thì bỏ phần giá).
    dich_vu_pr = []
    if not tu_do and cai_dat.get("bot_chu_dong_pr", True) is not False:
        try:
            so_dv = int(cai_dat.get("so_dich_vu_pr") or 5)
        except (TypeError, ValueError):
            so_dv = 5
        for s in (db.query(ServiceItem).filter(ServiceItem.is_active == True)
                  .order_by(ServiceItem.id).limit(max(1, so_dv)).all()):
            gia = (s.price_text or "").strip()
            if not gia and s.price:
                gia = f"{s.price:,.0f}".replace(",", ".") + "đ"
            dich_vu_pr.append({"ten": s.name, "gia": gia, "mo_ta": (s.description or "")[:200]})
    provider = ai_gateway.get_default_provider(db)
    la_mock = (not provider) or provider.provider == "mock"
    # Mục 10: lịch sử hội thoại đa lượt (số tin theo Cài đặt so_tin_nhan_ngu_canh),
    # không tính tin khách hiện tại (nó là câu hỏi đang xử lý).
    try:
        so_tin_ls = int(cai_dat.get("so_tin_nhan_ngu_canh") or 10)
    except (TypeError, ValueError):
        so_tin_ls = 10
    dong_ls = (db.query(Message)
               .filter(Message.conversation_id == conv.id, Message.id != msg.id)
               .order_by(Message.id.desc()).limit(max(1, so_tin_ls)).all())
    lich_su = [{"role": "user" if m.sender_type == "khach" else "assistant", "content": m.content}
               for m in reversed(dong_ls) if m.content]
    try:
        reply, model_used = ai_gateway.generate_reply(
            db, provider, content, chunks, memories,
            goi_y_hoi_sdt=(hoi_sdt and not la_mock), lich_su=lich_su, cai_dat=cai_dat,
            dich_vu=dich_vu_pr, ho_so_khach=(cust.memory_summary or ""),
            anh_data_uri=anh_data_uri)
    except ai_gateway.LoiVision as e:
        # Model phía sau provider KHÔNG hỗ trợ xem ảnh: ghi nhật ký riêng
        # "provider_khong_ho_tro_anh" + đánh dấu lên tin của khách để admin
        # biết, rồi trả câu dự phòng lịch sự thay vì im lặng/sập pipeline.
        db.add(SystemLog(level="warning", module="ai_gateway",
                         message=f"provider_khong_ho_tro_anh conv={conv.id} msg={msg.id}: {e}",
                         trace_id=trace)); db.commit()
        try:
            msg.error = "provider_khong_ho_tro_anh"; db.commit()
        except Exception:
            db.rollback()
        cau_du_phong_anh = ("Dạ em đã nhận được ảnh của anh/chị rồi ạ. Hiện hệ thống bên em chưa xem rõ "
                            "được nội dung ảnh này, anh/chị mô tả thêm giúp em, hoặc em chuyển nhân viên "
                            "xem trực tiếp cho mình nhé.")
        return _send_reply(db, conv, cust, cau_du_phong_anh, trace, intent=intent, channel=channel,
                           cai_dat=cai_dat,
                           tin_khach=_tin_khach(customer_external_id, external_id, cli_msg_id, la_nhom))
    except ai_gateway.AIError as e:
        db.add(SystemLog(level="error", module="orchestrator", message=f"Lỗi AI: {e}", trace_id=trace)); db.commit()
        _thong_bao(db, "bot_khong_tra_loi_duoc", "Bot không trả lời được", f"Bot không trả lời được khách {cust.display_name or cust.external_id} do lỗi nhà cung cấp AI: {e}", cust, conv, "canh_bao", channel)
        cau_du_phong = str(cai_dat.get("cau_khi_bot_khong_tra_loi") or "").strip()
        if cau_du_phong:
            return _send_reply(db, conv, cust, cau_du_phong, trace, channel=channel, cai_dat=cai_dat,
                               tin_khach=_tin_khach(customer_external_id, external_id, cli_msg_id, la_nhom))
        return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": f"loi_provider: {e}", "conversation_id": conv.id, "customer_id": cust.id}
    if hoi_sdt:
        if la_mock:
            cau_hoi = str(cai_dat.get("thu_thap_cau_hoi_sdt") or CAU_HOI_SDT_MAC_DINH)
            reply = (reply or "").rstrip() + "\n" + cau_hoi
        _ghi_da_hoi_sdt(db, conv.id, trace)
    if khach_moi:
        tin_chao = str(cai_dat.get("tin_chao_khach_moi") or "").strip()
        if tin_chao:
            reply = tin_chao + "\n" + (reply or "")
    # Policy check đơn giản: không hứa hẹn ngoài dữ liệu - nếu không có nguồn và câu hỏi giá thì vẫn trả lời mẫu 'chưa đủ thông tin' từ mock
    ket_qua_gui = _send_reply(db, conv, cust, reply, trace, chunks=chunks, model_used=model_used, intent=intent, channel=channel,
                              cai_dat=cai_dat, tin_khach=_tin_khach(customer_external_id, external_id, cli_msg_id, la_nhom))
    # Bộ nhớ dài hạn: đủ số tin mới thì tóm tắt gộp hồ sơ khách (chỉ chế độ tư
    # vấn; hàm tự nuốt lỗi, không chặn pipeline).
    if not tu_do:
        try:
            memory_service.cap_nhat_tom_tat_bo_nho(db, cust, cai_dat)
        except Exception:
            pass
    return ket_qua_gui


def _tin_khach(customer_external_id, external_id, cli_msg_id, la_nhom):
    return {"thread_id": str(customer_external_id), "external_id": str(external_id or ""),
            "cli_msg_id": str(cli_msg_id or ""), "loai_thread": 1 if la_nhom else 0}


def _send_reply(db, conv, cust, reply, trace, chunks=None, model_used="", rule=None, intent="", channel="mo_phong",
                cai_dat=None, tin_khach=None):
    cd = cai_dat if cai_dat is not None else _doc_cai_dat(db)
    # Mục 6: chuẩn hoá định dạng TRƯỚC khi gửi và trước khi lưu hiển thị.
    reply = dinh_dang_tin_zalo(reply or "")
    if not reply:
        return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "tra_loi_rong",
                "conversation_id": conv.id, "customer_id": cust.id}
    ket_qua_chung = {"trung": False, "trace_id": trace, "conversation_id": conv.id,
                     "customer_id": cust.id, "intent": intent, "nguon": chunks or [], "model": model_used}
    # Chế độ duyệt trước khi gửi: chỉ lưu bản nháp, không gửi thật.
    if cd.get("che_do_duyet_truoc_khi_gui"):
        db.add(Message(conversation_id=conv.id, external_id=None, sender_type="bot", content=reply, status="cho_duyet"))
        db.add(SystemLog(level="info", module="orchestrator", message=f"Câu trả lời hội thoại {conv.id} đang chờ duyệt trước khi gửi", trace_id=trace)); db.commit()
        return {**ket_qua_chung, "tra_loi": reply, "ly_do": "cho_duyet_truoc_khi_gui"}
    # Mục 4: thả tim tin khách trước khi trả lời (chỉ kênh cá nhân, đúng 1 lần/lượt).
    if tin_khach and cd.get("bot_tha_tim") and channel == "ca_nhan":
        try:
            ZaloPersonalConnector().tha_tim(tin_khach["thread_id"], tin_khach["external_id"],
                                            tin_khach.get("loai_thread", 0), tin_khach.get("cli_msg_id", ""))
        except Exception as e:
            db.add(SystemLog(level="warning", module="tha_tim", message=f"Không thả tim được cho tin {tin_khach.get('external_id')}: {e}", trace_id=trace)); db.commit()
    # Mục 5: chia nhỏ tin — áp dụng ở kênh cá nhân (bật/tắt + độ dài theo Cài đặt).
    cac_phan = [reply]
    if channel == "ca_nhan" and cd.get("gui_tin_chia_nho", True):
        try:
            do_dai = int(cd.get("do_dai_toi_da_moi_tin") or 350)
        except (TypeError, ValueError):
            do_dai = 350
        cac_phan = chia_tin_nhan(reply, do_dai) or [reply]
    try:
        do_tre_ms = int(os.getenv("GUI_TIN_DELAY_MS") or cd.get("do_tre_giua_cac_tin_ms") or 700)
    except (TypeError, ValueError):
        do_tre_ms = 700
    loi_cuoi = None
    so_phan_ok = 0
    for idx, phan in enumerate(cac_phan):
        if idx > 0 and do_tre_ms > 0:
            time.sleep(do_tre_ms / 1000.0)
        try:
            if channel == "ca_nhan":
                if cd.get("hieu_ung_dang_soan_tin"):
                    try:
                        ZaloPersonalConnector().typing(str(cust.external_id), 1 if (tin_khach and tin_khach.get("loai_thread")) else 0)
                    except Exception:
                        pass
                ZaloPersonalConnector().send_text(str(cust.external_id), phan)
            else:
                mock_connector.send_text(str(conv.id), phan)
            db.add(Message(conversation_id=conv.id, external_id=None, sender_type="bot", content=phan, status="da_gui"))
            so_phan_ok += 1
        except Exception as e:
            loi_cuoi = e
            db.add(Message(conversation_id=conv.id, external_id=None, sender_type="bot", content=phan,
                           status="loi_gui", error=f"Phần {idx + 1}/{len(cac_phan)}: {e}"))
        db.commit()
    if so_phan_ok == 0:
        db.add(SystemLog(level="error", module="zalo", message=f"Lỗi gửi tin qua kênh {channel}: {loi_cuoi}", trace_id=trace)); db.commit()
        _thong_bao(db, "loi_he_thong", "Lỗi gửi tin qua connector", f"Gửi tin cho khách {cust.display_name or cust.external_id} qua kênh {channel} thất bại: {loi_cuoi}", cust, conv, "khan_cap", channel)
        return {**ket_qua_chung, "tra_loi": None, "ly_do": f"loi_connector: {loi_cuoi}"}
    # Cập nhật bộ nhớ: ghi sự kiện tương tác
    if cd.get("module_bo_nho_ai", True) is not False:
        memory_service.remember(db, cust.id, f"Khách đã hỏi và được trả lời: {reply[:120]}", memory_type="su_kien", source="orchestrator", confidence=0.7)
    db.add(SystemLog(level="info", module="orchestrator", message=f"Đã trả lời hội thoại {conv.id} model={model_used} so_phan_tin={len(cac_phan)}", trace_id=trace)); db.commit()
    return {**ket_qua_chung, "tra_loi": reply, "so_phan_tin": len(cac_phan)}
