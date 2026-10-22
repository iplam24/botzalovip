from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..schemas import LoginIn, UserCreate
from ..security import verify_password, hash_password, create_token
from ..deps import get_current_user, require_admin
router = APIRouter(prefix="/api/auth", tags=["Xác thực"])
@router.post("/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email==data.email).first()
    if not u or not verify_password(data.password, u.hashed_password): raise HTTPException(401, "Email hoặc mật khẩu không đúng")
    return {"access_token": create_token(u.id, u.email, u.role), "token_type": "bearer", "role": u.role, "email": u.email}
@router.get("/me")
def me(user: User = Depends(get_current_user)): return {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role}
@router.post("/nguoi-dung")
def create_user(data: UserCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if db.query(User).filter(User.email==data.email).first(): raise HTTPException(400, "Email đã tồn tại")
    u = User(email=data.email, hashed_password=hash_password(data.password), full_name=data.full_name, role=data.role); db.add(u); db.commit(); db.refresh(u)
    return {"id": u.id, "email": u.email, "role": u.role}
@router.get("/nguoi-dung")
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return [{"id": u.id, "email": u.email, "role": u.role, "full_name": u.full_name} for u in db.query(User).all()]
