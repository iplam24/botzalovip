from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Customer, User
from ..schemas import CustomerIn
from ..deps import get_current_user, require_admin
router = APIRouter(prefix="/api/khach-hang", tags=["Khách hàng"])
def out(c): return {"id": c.id, "external_id": c.external_id, "display_name": c.display_name, "phone": c.phone, "labels": c.labels, "group_name": c.group_name, "notes": c.notes, "assignee": c.assignee, "last_interaction_at": str(c.last_interaction_at) if c.last_interaction_at else "", "created_at": str(c.created_at) if c.created_at else ""}
@router.get("")
def list_c(tu_khoa: str = "", nhan: str = "", db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    q = db.query(Customer)
    if tu_khoa:
        tk = f"%{tu_khoa}%"
        q = q.filter((Customer.display_name.like(tk)) | (Customer.phone.like(tk)) | (Customer.notes.like(tk)))
    if nhan: q = q.filter(Customer.labels.contains(nhan))
    return [out(c) for c in q.order_by(Customer.id.desc()).all()]
@router.post("")
def create_c(data: CustomerIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    c = Customer(**data.model_dump()); db.add(c); db.commit(); db.refresh(c); return out(c)
@router.get("/{cid}")
def get_c(cid: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    c=db.get(Customer,cid)
    if not c: raise HTTPException(404,"Không tìm thấy")
    return out(c)
@router.put("/{cid}")
def upd_c(cid: int, data: CustomerIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    c=db.get(Customer,cid)
    if not c: raise HTTPException(404,"Không tìm thấy")
    for k,v in data.model_dump(exclude_unset=True).items(): setattr(c,k,v)
    db.commit(); return out(c)
@router.delete("/{cid}")
def del_c(cid: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    c=db.get(Customer,cid)
    if not c: raise HTTPException(404,"Không tìm thấy")
    db.delete(c); db.commit(); return {"da_xoa": True}
