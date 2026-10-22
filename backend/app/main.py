"""Điểm khởi động FastAPI - Zalo AI Hub."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine, SessionLocal
from . import models  # noqa
from .models import User, AIProviderConfig, ZaloAccount, SystemLog
from .security import hash_password, encrypt_secret
import os
from .config import settings
from .routers import auth, ai_providers, customers, conversations, services_router, knowledge, memories, automation, zalo, logs_analytics, backup, ai_test, cai_dat

app = FastAPI(title="Zalo AI Hub", description="Nền tảng AI tự động hóa Zalo - giao diện và API tiếng Việt", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://localhost:3000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

for r in [auth.router, ai_providers.router, customers.router, conversations.router, services_router.router, knowledge.router, memories.router, automation.router, zalo.router, logs_analytics.router, backup.router, ai_test.router, cai_dat.router]:
    app.include_router(r)

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == settings.admin_email).first():
            db.add(User(email=settings.admin_email, hashed_password=hash_password(settings.admin_password), full_name="Quản trị viên", role="QuanTriVienCaoNhat")); db.commit()
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
