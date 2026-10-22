from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import MemoryItem, User
from ..schemas import MemoryIn, MemoryUpdate
from ..deps import get_current_user, require_admin
from ..services import memory_service
from ..services.phan_trang import co_phan_trang, trang_hoa
router = APIRouter(prefix="/api/bo-nho", tags=["Bộ nhớ AI"])
def out(m): return {"id": m.id, "customer_id": m.customer_id, "memory_type": m.memory_type, "content": m.content, "source": m.source, "confidence": m.confidence, "verified": m.verified, "pinned": m.pinned, "created_at": str(m.created_at) if m.created_at else "", "updated_at": str(m.updated_at) if m.updated_at else ""}
@router.get("")
def list_m(customer_id: int = None, memory_type: str = "", tu_khoa: str = "", trang: int = 0, kich_thuoc_trang: int = 20, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    q=db.query(MemoryItem)
    if customer_id: q=q.filter(MemoryItem.customer_id==customer_id)
    if memory_type: q=q.filter(MemoryItem.memory_type==memory_type)
    if tu_khoa: q=q.filter(MemoryItem.content.contains(tu_khoa))
    q=q.order_by(MemoryItem.pinned.desc(), MemoryItem.id.desc())
    ds=[out(m) for m in q.all()]
    if co_phan_trang(trang):
        return trang_hoa(ds, trang, kich_thuoc_trang)
    return ds
@router.post("")
def create_m(data: MemoryIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    item, created = memory_service.remember(db, data.customer_id, data.content, data.memory_type, data.source, data.confidence)
    item.verified = data.verified; item.pinned = data.pinned; db.commit(); db.refresh(item)
    return out(item)
# ---- Đợt nâng cấp 3, mục 3: trạng thái Vector DB của bộ nhớ (khai báo TRƯỚC /{mid}) ----
@router.get("/trang-thai-vector")
def trang_thai_vector(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return memory_service.trang_thai_vector(db)
@router.post("/nhung-lai-tat-ca")
def nhung_lai_tat_ca(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return memory_service.nhung_lai_tat_ca(db)

@router.get("/{mid}")
def get_m(mid:int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    m=db.get(MemoryItem,mid)
    if not m: raise HTTPException(404,"Không tìm thấy")
    return out(m)
@router.put("/{mid}")
def upd_m(mid:int, data: MemoryUpdate, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    m=db.get(MemoryItem,mid)
    if not m: raise HTTPException(404,"Không tìm thấy")
    thay_doi_noi_dung = "content" in data.model_dump(exclude_unset=True)
    for k,v in data.model_dump(exclude_unset=True).items(): setattr(m,k,v)
    db.commit()
    # Sửa nội dung tay -> nhúng lại vector cho khớp nội dung mới (nếu nguồn sẵn sàng)
    if thay_doi_noi_dung:
        memory_service._nhung_cho_muc(db, m)
        db.refresh(m)
    return out(m)
@router.delete("/{mid}")
def del_m(mid:int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    m=db.get(MemoryItem,mid)
    if not m: raise HTTPException(404,"Không tìm thấy")
    db.delete(m); db.commit(); return {"da_xoa": True}
