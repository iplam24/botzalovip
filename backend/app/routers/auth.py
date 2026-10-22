"""Xác thực + quản lý người dùng.

Đăng nhập bằng USERNAME + MẬT KHẨU (đính chính của LAM 22/10: đợt nâng cấp 2
đã hiểu nhầm thành bỏ mật khẩu — ý gốc là dùng username thay cho email, mật
khẩu vẫn bắt buộc). Mật khẩu được kiểm tra bằng hash PBKDF2 (verify_password),
không bao giờ trả ra ngoài. Tài khoản bị khóa (is_active=False) không đăng
nhập được và phiên cũ cũng bị chặn ở deps.get_current_user.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Customer, PhanBoBanBe
from ..schemas import LoginIn, UserCreate, UserUpdate
from ..security import hash_password, verify_password, create_token
from ..deps import get_current_user, require_admin

router = APIRouter(prefix="/api/auth", tags=["Xác thực"])

def user_out(db: Session, u: User) -> dict:
    """Thông tin người dùng + số khách / số bạn bè Zalo được phân bổ phụ trách."""
    ten_gan = u.username or u.email
    so_khach = db.query(Customer).filter(Customer.assignee == ten_gan).count() if ten_gan else 0
    so_ban_be = db.query(PhanBoBanBe).filter(PhanBoBanBe.admin_user_id == u.id).count()
    return {
        "id": u.id, "username": u.username or "", "email": u.email, "full_name": u.full_name,
        "role": u.role, "is_active": bool(u.is_active),
        "last_login_at": str(u.last_login_at) if u.last_login_at else None,
        "created_at": str(u.created_at) if u.created_at else "",
        "so_khach_phu_trach": so_khach, "so_ban_be_phu_trach": so_ban_be,
    }

@router.post("/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    ten = (data.username or "").strip()
    if not ten:
        raise HTTPException(400, "Hãy nhập tên đăng nhập")
    if not data.password:
        raise HTTPException(400, "Hãy nhập mật khẩu")
    u = db.query(User).filter(func.lower(User.username) == ten.lower()).first()
    if not u:
        raise HTTPException(401, "Tên đăng nhập không đúng")
    if not u.is_active:
        raise HTTPException(403, "Tài khoản đã bị khóa, vui lòng liên hệ quản trị viên")
    if not verify_password(data.password, u.hashed_password or ""):
        raise HTTPException(401, "Mật khẩu không đúng")
    u.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return {"access_token": create_token(u.id, u.email, u.role), "token_type": "bearer",
            "role": u.role, "email": u.email, "username": u.username}

@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_out(db, user)

@router.post("/nguoi-dung")
def create_user(data: UserCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    # Không truyền username -> dùng nguyên email làm tên đăng nhập (dễ đoán, hiển thị rõ ở trang Người dùng)
    username = (data.username or "").strip() or (data.email or "").strip()
    email = (data.email or "").strip() or f"{username}@local"
    if not username:
        raise HTTPException(400, "Thiếu tên đăng nhập (username)")
    if db.query(User).filter(func.lower(User.username) == username.lower()).first():
        raise HTTPException(400, "Tên đăng nhập đã tồn tại")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "Email đã tồn tại")
    if not (data.password or "").strip():
        raise HTTPException(400, "Hãy đặt mật khẩu cho người dùng mới")
    u = User(email=email, username=username,
             hashed_password=hash_password(data.password),
             full_name=data.full_name, role=data.role)
    db.add(u); db.commit(); db.refresh(u)
    return user_out(db, u)

@router.get("/nguoi-dung")
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return [user_out(db, u) for u in db.query(User).order_by(User.id).all()]

@router.put("/nguoi-dung/{uid}")
def update_user(uid: int, data: UserUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "Không tìm thấy người dùng")
    du_lieu = data.model_dump(exclude_unset=True)
    if "username" in du_lieu and du_lieu["username"] is not None:
        ten = du_lieu["username"].strip()
        if not ten:
            raise HTTPException(400, "Tên đăng nhập không được để trống")
        trung = db.query(User).filter(func.lower(User.username) == ten.lower(), User.id != uid).first()
        if trung:
            raise HTTPException(400, "Tên đăng nhập đã tồn tại")
        u.username = ten
    if "email" in du_lieu and du_lieu["email"] is not None:
        email = du_lieu["email"].strip()
        if email and db.query(User).filter(User.email == email, User.id != uid).first():
            raise HTTPException(400, "Email đã tồn tại")
        u.email = email
    for k in ("full_name", "role", "is_active"):
        if k in du_lieu and du_lieu[k] is not None:
            setattr(u, k, du_lieu[k])
    # Đổi mật khẩu: chỉ khi gửi mật khẩu mới khác trống — lưu dạng hash, không trả ra
    if du_lieu.get("password"):
        u.hashed_password = hash_password(du_lieu["password"])
    db.commit(); db.refresh(u)
    return user_out(db, u)
