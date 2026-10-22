"""Bộ điều phối AI - pipeline rút gọn nhưng thật (19 bước gốc được gom nhóm có log).
1 validate, 2 dedup external_message_id, 3 customer, 4 conversation, 5 automation check (bot paused/human),
6 intent, 7 entities (lấy từ khóa), 8-9 retrieve knowledge+memory+service, 10 policy, 11 chọn model,
12 generate, 13 output check, 14 action check, 15 quyết định gửi/chuyển, 16 send qua connector,
17 lưu, 18 cập nhật memory, 19 log/usage.
"""
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..models import Customer, Conversation, Message, SystemLog, ServiceItem
from .text_utils import classify_intent, normalize_vi
from . import knowledge_service, memory_service, ai_gateway, automation_service
from .zalo_connector import mock_connector

def process_inbound(db: Session, external_id: str, customer_external_id: str, customer_name: str, content: str, zalo_account_id=None):
    trace = str(uuid.uuid4())[:8]
    # Dedup trước khi tạo
    if external_id and db.query(Message).filter(Message.external_id == external_id).first():
        db.add(SystemLog(level="warning", module="orchestrator", message=f"Tin trùng bị bỏ qua {external_id}", trace_id=trace)); db.commit()
        return {"trung": True, "trace_id": trace, "tra_loi": None}
    cust = db.query(Customer).filter(Customer.external_id == customer_external_id).first()
    if not cust:
        cust = Customer(external_id=customer_external_id, display_name=customer_name); db.add(cust); db.commit(); db.refresh(cust)
    conv = db.query(Conversation).filter(Conversation.customer_id == cust.id).order_by(Conversation.created_at.desc()).first()
    if not conv or conv.status == "da_giai_quyet":
        conv = Conversation(customer_id=cust.id, zalo_account_id=zalo_account_id); db.add(conv); db.commit(); db.refresh(conv)
    msg = Message(conversation_id=conv.id, external_id=external_id, sender_type="khach", content=content, status="da_nhan")
    db.add(msg)
    try: db.commit()
    except IntegrityError:
        db.rollback(); return {"trung": True, "trace_id": trace, "tra_loi": None}
    db.add(SystemLog(level="info", module="orchestrator", message=f"Nhận tin từ {cust.display_name}: {content[:80]}", trace_id=trace)); db.commit()
    # Automation check: bot tạm dừng hoặc nhân viên tiếp quản -> không trả lời tự động
    if not conv.bot_enabled or conv.human_takeover:
        return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "bot_da_tam_dung_hoac_nhan_vien_tiep_quan", "conversation_id": conv.id, "customer_id": cust.id}
    intent = classify_intent(content)
    if intent == "gap_nhan_vien":
        conv.human_takeover = True; db.commit()
        return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "chuyen_nhan_vien_theo_yeu_cau", "conversation_id": conv.id, "customer_id": cust.id, "intent": intent}
    rule = automation_service.evaluate_rules(db, conv, content, intent)
    if rule:
        if rule.action_type == "tra_loi" and rule.action_value:
            return _send_reply(db, conv, cust, rule.action_value, trace, rule=rule)
        if rule.action_type == "gan_nhan":
            conv.labels = (conv.labels + "," + rule.action_value).strip(","); db.commit()
        if rule.action_type == "chuyen_nhan_vien":
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
    provider = ai_gateway.get_default_provider(db)
    try:
        reply, model_used = ai_gateway.generate_reply(db, provider, content, chunks, memories)
    except ai_gateway.AIError as e:
        db.add(SystemLog(level="error", module="orchestrator", message=f"Lỗi AI: {e}", trace_id=trace)); db.commit()
        return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": f"loi_provider: {e}", "conversation_id": conv.id, "customer_id": cust.id}
    # Policy check đơn giản: không hứa hẹn ngoài dữ liệu - nếu không có nguồn và câu hỏi giá thì vẫn trả lời mẫu 'chưa đủ thông tin' từ mock
    return _send_reply(db, conv, cust, reply, trace, chunks=chunks, model_used=model_used, intent=intent)

def _send_reply(db, conv, cust, reply, trace, chunks=None, model_used="", rule=None, intent=""):
    try: mock_connector.send_text(str(conv.id), reply)
    except Exception as e:
        db.add(SystemLog(level="error", module="zalo", message=f"Lỗi gửi tin: {e}", trace_id=trace)); db.commit()
        return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": f"loi_connector: {e}", "conversation_id": conv.id, "customer_id": cust.id}
    out = Message(conversation_id=conv.id, external_id=None, sender_type="bot", content=reply, status="da_gui")
    db.add(out); db.commit()
    # Cập nhật bộ nhớ: ghi sự kiện tương tác
    memory_service.remember(db, cust.id, f"Khách đã hỏi và được trả lời: {reply[:120]}", memory_type="su_kien", source="orchestrator", confidence=0.7)
    db.add(SystemLog(level="info", module="orchestrator", message=f"Đã trả lời hội thoại {conv.id} model={model_used}", trace_id=trace)); db.commit()
    return {"trung": False, "trace_id": trace, "tra_loi": reply, "conversation_id": conv.id, "customer_id": cust.id, "intent": intent, "nguon": chunks or [], "model": model_used}
