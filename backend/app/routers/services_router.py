from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import ServiceItem, User
from ..schemas import ServiceIn
from ..deps import get_current_user, require_admin
import uuid
router = APIRouter(prefix="/api/dich-vu", tags=["Dịch vụ"])
def out(s): return {"id": s.id, "code": s.code, "name": s.name, "description": s.description, "category": s.category, "price": s.price, "price_text": s.price_text, "policy": s.policy, "faq": s.faq, "keywords": s.keywords, "is_active": s.is_active, "version": s.version}
@router.get("")
def list_s(db: Session = Depends(get_db), u: User = Depends(get_current_user)): return [out(s) for s in db.query(ServiceItem).all()]
@router.post("")
def create_s(data: ServiceIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    d=data.model_dump(); d["code"]=d.get("code") or f"DV-{uuid.uuid4().hex[:6].upper()}"
    s=ServiceItem(**d); db.add(s); db.commit(); db.refresh(s); return out(s)
@router.get("/{sid}")
def get_s(sid:int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    s=db.get(ServiceItem,sid)
    if not s: raise HTTPException(404,"Không tìm thấy")
    return out(s)
@router.put("/{sid}")
def upd_s(sid:int, data: ServiceIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    s=db.get(ServiceItem,sid)
    if not s: raise HTTPException(404,"Không tìm thấy")
    for k,v in data.model_dump(exclude_unset=True).items():
        if k!="code" or v: setattr(s,k,v)
    s.version+=1; db.commit(); return out(s)
@router.delete("/{sid}")
def del_s(sid:int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    s=db.get(ServiceItem,sid)
    if not s: raise HTTPException(404,"Không tìm thấy")
    db.delete(s); db.commit(); return {"da_xoa": True}
