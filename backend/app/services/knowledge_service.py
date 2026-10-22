"""Kho tri thức: chia đoạn, truy xuất từ khóa có chấm điểm."""
from sqlalchemy.orm import Session
from ..models import KnowledgeDocument, KnowledgeChunk
from .text_utils import normalize_vi, chunk_text

def create_document(db: Session, title, content, source_type="van_ban", service_id=None):
    doc = KnowledgeDocument(title=title, content=content, source_type=source_type, service_id=service_id)
    db.add(doc); db.flush()
    for idx, ch in enumerate(chunk_text(content)):
        db.add(KnowledgeChunk(document_id=doc.id, content=ch, normalized=normalize_vi(ch), chunk_index=idx))
    db.commit(); db.refresh(doc); return doc

def retrieve(db: Session, query: str, limit: int = 5, service_id=None):
    nq = normalize_vi(query); words = [w for w in nq.split() if len(w) > 1]
    q = db.query(KnowledgeChunk).join(KnowledgeDocument).filter(KnowledgeDocument.is_active == True)
    if service_id: q = q.filter(KnowledgeDocument.service_id == service_id)
    scored = []
    for ch in q.all():
        score = sum(1 for w in words if w in ch.normalized)
        if nq and nq in ch.normalized: score += 3
        if score > 0: scored.append((score, ch))
    scored.sort(key=lambda x: -x[0])
    return [{"chunk_id": c.id, "document_id": c.document_id, "title": c.document.title, "content": c.content, "score": s} for s, c in scored[:limit]]
