from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import AutomationRule, RuleRun, User
from ..schemas import RuleIn
from ..deps import get_current_user, require_admin
router = APIRouter(prefix="/api/quy-tac", tags=["Quy tắc tự động hóa"])
def out(r): return {"id": r.id, "name": r.name, "description": r.description, "condition_type": r.condition_type, "condition_value": r.condition_value, "action_type": r.action_type, "action_value": r.action_value, "priority": r.priority, "is_active": r.is_active}
@router.get("")
def list_r(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    ket_qua = []
    for r in db.query(AutomationRule).order_by(AutomationRule.priority).all():
        d = out(r)
        lan_gan_nhat = db.query(RuleRun).filter(RuleRun.rule_id == r.id).order_by(RuleRun.id.desc()).first()
        d["so_lan_chay"] = db.query(RuleRun).filter(RuleRun.rule_id == r.id).count()
        d["lan_chay_gan_nhat"] = ({"id": lan_gan_nhat.id, "result": lan_gan_nhat.result, "conversation_id": lan_gan_nhat.conversation_id, "created_at": str(lan_gan_nhat.created_at)} if lan_gan_nhat else None)
        ket_qua.append(d)
    return ket_qua
@router.get("/{rid}/lan-chay")
def lan_chay(rid: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    if not db.get(AutomationRule, rid): raise HTTPException(404, "Không tìm thấy")
    return [{"id": x.id, "rule_id": x.rule_id, "conversation_id": x.conversation_id, "result": x.result, "created_at": str(x.created_at)} for x in db.query(RuleRun).filter(RuleRun.rule_id == rid).order_by(RuleRun.id.desc()).limit(50).all()]
@router.post("")
def create_r(data: RuleIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    r=AutomationRule(**data.model_dump()); db.add(r); db.commit(); db.refresh(r); return out(r)
@router.put("/{rid}")
def upd_r(rid:int, data: RuleIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    r=db.get(AutomationRule,rid)
    if not r: raise HTTPException(404,"Không tìm thấy")
    for k,v in data.model_dump().items(): setattr(r,k,v)
    db.commit(); return out(r)
@router.delete("/{rid}")
def del_r(rid:int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    r=db.get(AutomationRule,rid)
    if not r: raise HTTPException(404,"Không tìm thấy")
    db.delete(r); db.commit(); return {"da_xoa": True}
