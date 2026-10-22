"""Bảo mật: băm mật khẩu pbkdf2, JWT, mã hóa khóa API."""
import hashlib, hmac, os, base64, jwt
from datetime import datetime, timedelta, timezone
from .config import settings

def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000)
    return f"pbkdf2${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"

def verify_password(pw: str, hashed: str) -> bool:
    try:
        _, s, d = hashed.split("$")
        salt = base64.b64decode(s); expected = base64.b64decode(d)
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False

def create_token(user_id: int, email: str, role: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": str(user_id), "email": email, "role": role, "exp": exp}, settings.secret_key, algorithm="HS256")

def decode_token(token: str):
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])

# Mã hóa khóa API: ưu tiên Fernet, fallback obfuscate có cảnh báo (không dùng cho production)
def _fernet():
    try:
        from cryptography.fernet import Fernet
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
        return Fernet(key)
    except Exception:
        return None

def encrypt_secret(v: str) -> str:
    if not v: return ""
    f = _fernet()
    if f: return "fernet:" + f.encrypt(v.encode()).decode()
    return "b64:" + base64.b64encode(v.encode()).decode()  # CẢNH BÁO: chỉ fallback dev

def decrypt_secret(v: str) -> str:
    if not v: return ""
    try:
        if v.startswith("fernet:"):
            f = _fernet(); return f.decrypt(v[7:].encode()).decode() if f else ""
        if v.startswith("b64:"): return base64.b64decode(v[4:]).decode()
    except Exception: return ""
    return ""

def mask_secret(v: str) -> str:
    plain = decrypt_secret(v) if v and (v.startswith("fernet:") or v.startswith("b64:")) else v
    if not plain: return ""
    if len(plain) <= 8: return "****"
    return plain[:3] + "****" + plain[-3:]
