from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import BackupRecord, User
from ..deps import get_current_user, require_admin
from ..services.backup_service import export_backup, restore_backup
import os, datetime
router = APIRouter(prefix="/api/sao-luu", tags=["Sao lưu và khôi phục"])
@router.post("")
def create_b(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    os.makedirs("backups", exist_ok=True)
    fname=f"backup-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.zip"; path=os.path.join("backups", fname)
    _, size, _ = export_backup(db, path)
    rec=BackupRecord(filename=fname, path=path, size=size, status="thanh_cong"); db.add(rec); db.commit(); db.refresh(rec)
    return {"id": rec.id, "filename": fname, "size": size, "status": rec.status}
@router.get("")
def list_b(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return [{"id": b.id, "filename": b.filename, "size": b.size, "status": b.status, "created_at": str(b.created_at)} for b in db.query(BackupRecord).all()]
@router.post("/{bid}/khoi-phuc")
def restore(bid:int, payload: dict = Body(default={}), db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if not payload.get("xac_nhan"): raise HTTPException(400, "Cần xác nhận khôi phục: {\"xac_nhan\": true}")
    rec=db.get(BackupRecord,bid)
    if not rec or not os.path.exists(rec.path): raise HTTPException(404, "Không tìm thấy bản sao lưu")
    counts=restore_backup(db, rec.path); return {"da_khoi_phuc": True, "chi_tiet": counts}

@router.delete("/{bid}")
def delete_b(bid: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    rec = db.get(BackupRecord, bid)
    if not rec: raise HTTPException(404, "Không tìm thấy bản sao lưu")
    if rec.path and os.path.exists(rec.path):
        try: os.remove(rec.path)
        except OSError: pass
    db.delete(rec); db.commit(); return {"da_xoa": True}
