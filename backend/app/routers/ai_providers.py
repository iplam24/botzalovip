from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import AIProviderConfig, User
from ..schemas import ProviderIn, ProviderUpdate
from ..security import encrypt_secret, mask_secret
from ..deps import get_current_user, require_admin
from ..services.ai_gateway import test_provider
router = APIRouter(prefix="/api/ai-providers", tags=["Nhà cung cấp AI"])
def out(p): return {"id": p.id, "name": p.name, "provider": p.provider, "base_url": p.base_url, "api_key_masked": mask_secret(p.api_key_encrypted), "model": p.model, "embedding_model": p.embedding_model, "max_tokens": p.max_tokens, "timeout": p.timeout, "is_active": p.is_active, "is_default": p.is_default, "status": p.status, "last_error": p.last_error}
@router.get("")
def list_p(db: Session = Depends(get_db), u: User = Depends(get_current_user)): return [out(p) for p in db.query(AIProviderConfig).all()]
@router.post("")
def create_p(data: ProviderIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    if data.is_default: db.query(AIProviderConfig).update({"is_default": False})
    p = AIProviderConfig(name=data.name, provider=data.provider, base_url=data.base_url, api_key_encrypted=encrypt_secret(data.api_key), model=data.model, embedding_model=data.embedding_model, max_tokens=data.max_tokens, timeout=data.timeout, is_active=data.is_active, is_default=data.is_default)
    db.add(p); db.commit(); db.refresh(p); return out(p)
@router.get("/{pid}")
def get_p(pid: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    p = db.get(AIProviderConfig, pid)
    if not p: raise HTTPException(404, "Không tìm thấy")
    return out(p)
@router.put("/{pid}")
def update_p(pid: int, data: ProviderUpdate, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    p = db.get(AIProviderConfig, pid)
    if not p: raise HTTPException(404, "Không tìm thấy")
    for k, v in data.model_dump(exclude_unset=True).items():
        if k=="api_key": p.api_key_encrypted = encrypt_secret(v)
        elif k=="is_default" and v: db.query(AIProviderConfig).update({"is_default": False}); p.is_default=True
        else: setattr(p, k, v)
    db.commit(); db.refresh(p); return out(p)
@router.delete("/{pid}")
def delete_p(pid: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    p = db.get(AIProviderConfig, pid)
    if not p: raise HTTPException(404, "Không tìm thấy")
    db.delete(p); db.commit(); return {"da_xoa": True}
@router.post("/{pid}/kiem-tra")
def kiem_tra(pid: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    p = db.get(AIProviderConfig, pid)
    if not p: raise HTTPException(404, "Không tìm thấy")
    return test_provider(db, p)
