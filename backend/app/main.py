"""Điểm khởi động FastAPI - Zalo AI Hub."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine, SessionLocal
from . import models  # noqa
from .models import User, AIProviderConfig, ZaloAccount, SystemLog
from .security import hash_password, encrypt_secret
import os
from .config import settings
from .routers import auth, ai_providers, customers, conversations, services_router, knowledge, memories, automation, zalo, logs_analytics, backup, ai_test, cai_dat, notifications, ban_be, cau_hinh_chat

app = FastAPI(title="Zalo AI Hub", description="Nền tảng AI tự động hóa Zalo - giao diện và API tiếng Việt", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://localhost:3000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

for r in [auth.router, ai_providers.router, customers.router, conversations.router, services_router.router, knowledge.router, memories.router, automation.router, zalo.router, logs_analytics.router, backup.router, ai_test.router, cai_dat.router, notifications.router, ban_be.router, cau_hinh_chat.router]:
    app.include_router(r)

def seed():
    Base.metadata.create_all(bind=engine)
    # Nâng cấp nhẹ cho DB đã tồn tại: thêm cột channel vào conversations, email vào customers nếu chưa có
    try:
        from sqlalchemy import inspect, text
        insp = inspect(engine)
        cols = [c["name"] for c in insp.get_columns("conversations")]
        if "channel" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE conversations ADD COLUMN channel VARCHAR DEFAULT 'mo_phong'"))
        cust_cols = [c["name"] for c in insp.get_columns("customers")]
        if "email" not in cust_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE customers ADD COLUMN email VARCHAR DEFAULT ''"))
        # Bộ nhớ dài hạn theo khách: hồ sơ tóm tắt (TEXT hợp lệ cả Postgres lẫn SQLite)
        if "memory_summary" not in cust_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE customers ADD COLUMN memory_summary TEXT DEFAULT ''"))
        # Đợt nâng cấp 2: users.username (đăng nhập chỉ bằng username) + last_login_at
        # Mỗi cột một giao dịch riêng; dùng TIMESTAMP (hợp lệ cả PostgreSQL lẫn SQLite,
        # DATETIME chỉ có ở SQLite/MySQL — từng gây lỗi khởi động trên Postgres thật).
        user_cols = [c["name"] for c in insp.get_columns("users")]
        if "username" not in user_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR"))
        if "last_login_at" not in user_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP"))
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)"))
        except Exception:
            pass
        # Đợt nâng cấp 3, mục 3 (Vector DB): cột embedding (JSON text) cho
        # knowledge_chunks + memories — kiểu TEXT chạy được cả Postgres lẫn SQLite.
        for bang in ("knowledge_chunks", "memories"):
            try:
                cot = [c["name"] for c in insp.get_columns(bang)]
                if "embedding" not in cot:
                    with engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE {bang} ADD COLUMN embedding TEXT DEFAULT ''"))
            except Exception:
                pass
        # Trên Postgres (image pgvector): thử bật extension vector để sẵn sàng
        # cho nâng cấp sau. Việc truy hồi hiện tại vẫn dùng JSON + cosine Python
        # (đã ghi rõ trong BAO_CAO) nên bật extension thất bại cũng KHÔNG sao.
        try:
            if engine.dialect.name == "postgresql":
                with engine.begin() as conn:
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            pass
    except Exception:
        pass
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == settings.admin_email).first()
        if not admin:
            db.add(User(email=settings.admin_email, username="admin", hashed_password=hash_password(settings.admin_password), full_name="Quản trị viên", role="QuanTriVienCaoNhat")); db.commit()
            admin = db.query(User).filter(User.email == settings.admin_email).first()
        # Gán username "admin" cho tài khoản quản trị đã tồn tại từ trước (migration nhẹ)
        if admin and not getattr(admin, "username", None):
            admin.username = "admin"; db.commit()
        # Người dùng cũ chưa có username: lấy phần trước @ của email làm username tạm
        try:
            for u in db.query(User).filter(User.username == None).all():  # noqa: E711
                co_so = (u.email or f"user{u.id}").split("@")[0] or f"user{u.id}"
                ung_vien, dem = co_so, 1
                while db.query(User).filter(User.username == ung_vien, User.id != u.id).first():
                    dem += 1; ung_vien = f"{co_so}{dem}"
                u.username = ung_vien
            db.commit()
        except Exception:
            db.rollback()
        if not db.query(AIProviderConfig).filter(AIProviderConfig.provider == "mock").first():
            db.add(AIProviderConfig(name="Mock AI (mô phỏng)", provider="mock", model="mock-model", api_key_encrypted=encrypt_secret("mock-key-123456"), is_default=True, status="da_ket_noi")); db.commit()
        # Cấu hình mẫu LAM Token - code: KHÔNG hard-code khóa API.
        # Chỉ seed khóa khi env TEST_AI_API_KEY tồn tại; ngược lại khóa rỗng + trạng thái chưa cấu hình.
        lam = db.query(AIProviderConfig).filter(AIProviderConfig.name == "LAM Token - code").first()
        test_key = os.getenv("TEST_AI_API_KEY", "")
        if not lam:
            db.add(AIProviderConfig(name="LAM Token - code", provider="openai_compatible", base_url="https://token.lamndvn.id.vn/v1", model="code", api_key_encrypted=encrypt_secret(test_key) if test_key else "", is_default=False, is_active=True, status="chua_kiem_tra" if test_key else "chua_cau_hinh", last_error="" if test_key else "Chưa cấu hình khóa API")); db.commit()
        elif test_key and not lam.api_key_encrypted:
            lam.api_key_encrypted = encrypt_secret(test_key); lam.status = "chua_kiem_tra"; lam.last_error = ""; db.commit()
        if not db.query(ZaloAccount).filter(ZaloAccount.account_type == "mock").first():
            db.add(ZaloAccount(name="Tài khoản Zalo mô phỏng", account_type="mock", status="da_ket_noi")); db.commit()
        if not db.query(ZaloAccount).filter(ZaloAccount.account_type == "ca_nhan").first():
            db.add(ZaloAccount(name="Tài khoản Zalo cá nhân (zca-js)", account_type="ca_nhan", status="chua_ket_noi", last_error="Chưa chạy dịch vụ Zalo cá nhân")); db.commit()
        db.add(SystemLog(level="info", module="he_thong", message="Khởi động hệ thống")); db.commit()
    finally:
        db.close()

@app.on_event("startup")
def on_startup(): seed()

@app.get("/api/suc-khoe-truc-tiep")
def health_direct(): return {"trang_thai": "khoe"}
# Health cũng ở logs_analytics: GET /api/suc-khoe
