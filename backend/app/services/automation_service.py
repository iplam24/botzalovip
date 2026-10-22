"""Quy tắc tự động hóa: điều kiện từ khóa/intent/nhãn -> hành động."""
from sqlalchemy.orm import Session
from ..models import AutomationRule, RuleRun
from .text_utils import normalize_vi, classify_intent

def evaluate_rules(db: Session, conversation, content: str, intent: str):
    """Trả về (action, rule) đầu tiên khớp theo priority tăng dần, hoặc None."""
    rules = db.query(AutomationRule).filter(AutomationRule.is_active == True).order_by(AutomationRule.priority).all()
    for r in rules:
        matched = False
        if r.condition_type == "chua_tu_khoa" and r.condition_value and normalize_vi(r.condition_value) in normalize_vi(content): matched = True
        if r.condition_type == "intent" and r.condition_value == intent: matched = True
        if r.condition_type == "nhan" and r.condition_value and r.condition_value in (conversation.labels or ""): matched = True
        if matched:
            db.add(RuleRun(rule_id=r.id, conversation_id=conversation.id, result=r.action_type)); db.commit()
            return r
    return None
