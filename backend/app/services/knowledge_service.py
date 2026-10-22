"""Kho tri thức: chia đoạn, truy xuất từ khóa có chấm điểm + hợp nhất ngữ nghĩa.

Đợt nâng cấp 3 (mục 3, Vector DB): vector nhúng lưu dạng JSON trên từng đoạn;
khi cài đặt tim_kiem_ngu_nghia bật và có nguồn nhúng sẵn sàng, kết quả truy
hồi hợp nhất điểm từ khóa (score) với độ tương đồng cosine (diem_ngu_nghia).
Chưa có vector/nguồn nhúng -> giữ nguyên hành vi tìm từ khóa như cũ.
"""
from sqlalchemy.orm import Session
from ..models import KnowledgeDocument, KnowledgeChunk
from .text_utils import normalize_vi, chunk_text


def tao_chunks_cho_tai_lieu(db: Session, doc):
    """Chia tài liệu thành các đoạn và nhúng vector cho từng đoạn (nếu nguồn
    nhúng sẵn sàng). Dùng chung cho tạo mới/cập nhật tài liệu; nguồn nhúng
    chưa sẵn sàng thì đoạn vẫn được tạo, chỉ chưa có vector."""
    from . import embedding_service
    chunks = []
    for idx, ch in enumerate(chunk_text(doc.content or "")):
        chunk = KnowledgeChunk(document_id=doc.id, content=ch, normalized=normalize_vi(ch), chunk_index=idx)
        db.add(chunk); chunks.append(chunk)
    db.flush()
    try:
        vectors = embedding_service.nhung_nhieu(db, [c.content for c in chunks])
        if vectors:
            for chunk, vec in zip(chunks, vectors):
                chunk.embedding = embedding_service.ghi_vector(vec)
    except Exception:
        pass
    return chunks


def create_document(db: Session, title, content, source_type="van_ban", service_id=None):
    doc = KnowledgeDocument(title=title, content=content, source_type=source_type, service_id=service_id)
    db.add(doc); db.flush()
    tao_chunks_cho_tai_lieu(db, doc)
    db.commit(); db.refresh(doc); return doc


def retrieve(db: Session, query: str, limit: int = 5, service_id=None):
    nq = normalize_vi(query); words = [w for w in nq.split() if len(w) > 1]
    q = db.query(KnowledgeChunk).join(KnowledgeDocument).filter(KnowledgeDocument.is_active == True)
    if service_id: q = q.filter(KnowledgeDocument.service_id == service_id)
    tat_ca = q.all()
    scored = []
    for ch in tat_ca:
        score = sum(1 for w in words if w in ch.normalized)
        if nq and nq in ch.normalized: score += 3
        if score > 0: scored.append((score, ch))
    scored.sort(key=lambda x: -x[0])
    results = [{"chunk_id": c.id, "document_id": c.document_id, "title": c.document.title,
                "content": c.content, "score": s, "diem_ngu_nghia": None} for s, c in scored[:limit]]
    # --- Hợp nhất kết quả NGỮ NGHĨA (Vector DB) ---
    try:
        from ..routers.cai_dat import doc_cai_dat
        from . import embedding_service
        cai_dat = doc_cai_dat(db)
        if cai_dat.get("tim_kiem_ngu_nghia", True):
            so_ngu_nghia = int(cai_dat.get("so_ket_qua_ngu_nghia", 4) or 4)
            qv = embedding_service.nhung_mot(db, query)
            if qv:
                theo_id = {r["chunk_id"]: r for r in results}
                ung_vien = []
                for ch in tat_ca:
                    vec = embedding_service.doc_vector(ch.embedding)
                    if not vec:
                        continue
                    diem = embedding_service.cosine(qv, vec)
                    if diem >= 0.3:
                        ung_vien.append((diem, ch))
                ung_vien.sort(key=lambda x: -x[0])
                for diem, ch in ung_vien[:so_ngu_nghia]:
                    if ch.id in theo_id:
                        theo_id[ch.id]["diem_ngu_nghia"] = round(diem, 4)
                    else:
                        results.append({"chunk_id": ch.id, "document_id": ch.document_id,
                                        "title": ch.document.title, "content": ch.content,
                                        "score": 0, "diem_ngu_nghia": round(diem, 4)})
    except Exception:
        pass
    return results


def trang_thai_vector(db: Session) -> dict:
    """Trạng thái nhúng của kho tri thức: nguồn + đã nhúng/tổng số đoạn."""
    from . import embedding_service
    gia_tri = [h[0] for h in db.query(KnowledgeChunk.embedding).all()]
    da = sum(1 for v in gia_tri if v)
    tt = embedding_service.nguon_hien_tai(db)
    return {"tong_chunk": len(gia_tri), "da_nhung": da, "chua_nhung": len(gia_tri) - da,
            "nguon": tt["nguon"], "san_sang": tt["san_sang"], "mo_ta": tt["mo_ta"]}


def nhung_lai_tat_ca(db: Session) -> dict:
    """Nhúng (lại) vector cho MỌI đoạn tri thức bằng nguồn nhúng hiện tại.
    Nguồn chưa sẵn sàng -> không ghi gì, trả trạng thái trung thực."""
    from . import embedding_service
    chunks = db.query(KnowledgeChunk).all()
    vectors = embedding_service.nhung_nhieu(db, [c.content for c in chunks]) if chunks else []
    if vectors:
        for chunk, vec in zip(chunks, vectors):
            chunk.embedding = embedding_service.ghi_vector(vec)
        db.commit()
    return trang_thai_vector(db)
