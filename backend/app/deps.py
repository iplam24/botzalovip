"""Phụ thuộc xác thực và phân quyền."""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .database import get_db
from .security import decode_token
from .models import User
import jwt as pyjwt

bearer = HTTPBearer(auto_error=False)
ADMIN_ROLES = {"QuanTriVienCaoNhat", "QuanTriVien"}

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    if not creds: raise HTTPException(401, "Chưa đăng nhập")
    try: payload = decode_token(creds.credentials)
    except pyjwt.PyJWTError: raise HTTPException(401, "Phiên đăng nhập không hợp lệ hoặc đã hết hạn")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user: raise HTTPException(401, "Người dùng không tồn tại")
    return user

def require_admin(user: User = Depends(get_current_user)):
    if user.role not in ADMIN_ROLES: raise HTTPException(403, "Không có quyền thực hiện thao tác này")
    return user

def log(db, level, module, message, trace_id=""):
    from .models import SystemLog
    db.add(SystemLog(level=level, module=module, message=message, trace_id=trace_id)); db.commit()
