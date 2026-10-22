from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import KnowledgeDocument, User
from ..schemas import KnowledgeIn, RetrieveIn
from ..deps import get_current_user, require_admin
from ..services import knowledge_service
from ..services.phan_trang import co_phan_trang, trang_hoa
router = APIRouter(prefix="/api/tri-thuc", tags=["Kho tri thức"])
def out(d): return {"id": d.id, "title": d.title, "content": d.content, "source_type": d.source_type, "service_id": d.service_id, "version": d.version, "is_active": d.is_active}
@router.get("/tai-lieu")
def list_d(trang: int = 0, kich_thuoc_trang: int = 20, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    ds = [out(d) for d in db.query(KnowledgeDocument).order_by(KnowledgeDocument.id.desc()).all()]
    if co_phan_trang(trang):
        return trang_hoa(ds, trang, kich_thuoc_trang)
    return ds
@router.post("/tai-lieu")
def create_d(data: KnowledgeIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    d=knowledge_service.create_document(db, data.title, data.content, data.source_type, data.service_id); return out(d)
@router.post("/nhap-van-ban")
def nhap(data: KnowledgeIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    d=knowledge_service.create_document(db, data.title, data.content, "van_ban", data.service_id); return out(d)
@router.get("/tai-lieu/{did}")
def get_d(did:int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    d=db.get(KnowledgeDocument,did)
    if not d: raise HTTPException(404,"Không tìm thấy")
    return out(d)
@router.put("/tai-lieu/{did}")
def upd_d(did:int, data: KnowledgeIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    d=db.get(KnowledgeDocument,did)
    if not d: raise HTTPException(404,"Không tìm thấy")
    # tạo version mới bằng cách xóa chunks cũ và tạo lại (kèm nhúng vector mới)
    from ..models import KnowledgeChunk
    db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id==did).delete()
    d.title=data.title; d.content=data.content; d.version+=1; db.flush()
    knowledge_service.tao_chunks_cho_tai_lieu(db, d)
    db.commit(); return out(d)
@router.delete("/tai-lieu/{did}")
def del_d(did:int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    d=db.get(KnowledgeDocument,did)
    if not d: raise HTTPException(404,"Không tìm thấy")
    db.delete(d); db.commit(); return {"da_xoa": True}
@router.post("/truy-xuat")
def retrieve(data: RetrieveIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return {"ket_qua": knowledge_service.retrieve(db, data.query, data.limit)}
# ---- Đợt nâng cấp 3, mục 3: Vector DB ----
@router.get("/trang-thai-vector")
def trang_thai_vector(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return knowledge_service.trang_thai_vector(db)
@router.post("/nhung-lai-tat-ca")
def nhung_lai_tat_ca(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return knowledge_service.nhung_lai_tat_ca(db)
