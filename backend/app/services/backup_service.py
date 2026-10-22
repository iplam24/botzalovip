"""Sao lưu: xuất JSON trong ZIP, khóa API được redact, khôi phục có xác nhận phía router."""
import json, zipfile, os
from sqlalchemy.orm import Session
from ..models import *

MODELS = [Customer, Conversation, Message, ServiceItem, KnowledgeDocument, MemoryItem, AutomationRule, AIProviderConfig, ZaloAccount]
def _row(obj, redact=False):
    d = {}
    for c in obj.__table__.columns:
        v = getattr(obj, c.name)
        if redact and c.name == "api_key_encrypted": v = "[REDACTED]"
        if hasattr(v, "isoformat"): v = v.isoformat()
        d[c.name] = v
    return d

def export_backup(db: Session, path: str):
    data = {}
    for m in MODELS:
        data[m.__tablename__] = [_row(o, redact=True) for o in db.query(m).all()]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("backup.json", json.dumps(data, ensure_ascii=False, indent=2))
    return path, os.path.getsize(path), data

def restore_backup(db: Session, path: str):
    with zipfile.ZipFile(path) as z:
        data = json.loads(z.read("backup.json"))
    # MVP restore: chỉ khôi phục Dịch vụ + Tri thức + Bộ nhớ + Quy tắc nếu chưa tồn tại theo id
    counts = {}
    mapping = {"services": ServiceItem, "knowledge_documents": KnowledgeDocument, "memories": MemoryItem, "automation_rules": AutomationRule}
    for key, model in mapping.items():
        c = 0
        for row in data.get(key, []):
            row = {k: v for k, v in row.items() if k in model.__table__.columns and k not in ("created_at", "updated_at")}
            if not db.query(model).filter(model.id == row.get("id")).first():
                db.add(model(**row)); c += 1
        counts[key] = c
    db.commit(); return counts
