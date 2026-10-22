"""Cấu hình hệ thống - đọc từ biến môi trường, không chứa secret thật."""
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Zalo AI Hub"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./zalo_ai_hub.db")
    secret_key: str = os.getenv("SECRET_KEY", "doi-secret-nay-trong-production-32-ky-tu-tro-len")
    admin_email: str = os.getenv("ADMIN_EMAIL", "admin@local")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "Admin@12345")
    access_token_expire_minutes: int = 60 * 24
    timezone: str = "Asia/Ho_Chi_Minh"
    zalo_personal_service_url: str = "http://localhost:8791"
    zalo_connector_secret: str = ""
    test_ai_api_key: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
