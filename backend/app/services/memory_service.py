"""Bộ nhớ dài hạn: lưu, chống trùng, truy xuất theo khách hàng và từ khóa."""
from sqlalchemy.orm import Session
from ..models import MemoryItem
from .text_utils import normalize_vi

def remember(db: Session, customer_id, content, memory_type="ngu_nghia", source="he_thong", confidence=0.8):
    # Chống trùng: cùng khách + cùng nội dung chuẩn hóa
    existing = db.query(MemoryItem).filter(MemoryItem.customer_id == customer_id).all()
    for m in existing:
        if normalize_vi(m.content) == normalize_vi(content): return m, False
    item = MemoryItem(customer_id=customer_id, content=content, memory_type=memory_type, source=source, confidence=confidence)
    db.add(item); db.commit(); db.refresh(item); return item, True

def retrieve_memories(db: Session, customer_id, query="", limit=5):
    q = db.query(MemoryItem)
    if customer_id: q = q.filter(MemoryItem.customer_id == customer_id)
    items = q.order_by(MemoryItem.pinned.desc(), MemoryItem.created_at.desc()).all()
    if query:
        nq = normalize_vi(query); items = sorted(items, key=lambda m: -sum(1 for w in nq.split() if w in normalize_vi(m.content)))
    return items[:limit]
