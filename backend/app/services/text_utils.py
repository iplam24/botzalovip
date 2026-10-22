"""Chuẩn hóa tiếng Việt: bỏ dấu, hạ chữ thường để tìm kiếm không dấu."""
import re, unicodedata
def normalize_vi(s: str) -> str:
    if not s: return ""
    s = s.replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower()).strip()
def chunk_text(text: str, size: int = 500, overlap: int = 50):
    text = (text or "").strip()
    if not text: return []
    parts, i = [], 0
    while i < len(text):
        parts.append(text[i:i+size]); i += size - overlap if size > overlap else size
    return parts
INTENTS = {
    "hoi_gia": ["gia", "bao nhieu", "chi phi", "bang gia", "phi"],
    "chao_hoi": ["xin chao", "chao", "hello", "hi"],
    "gap_nhan_vien": ["gap nhan vien", "nguoi that", "tu van vien", "nhan vien"],
    "khieu_nai": ["khieu nai", "phan nan", "te qua", "khong hai long"],
    "hoi_chinh_sach": ["chinh sach", "bao hanh", "hoan tien", "quy dinh"],
}
def classify_intent(text: str) -> str:
    n = normalize_vi(text)
    for intent, kws in INTENTS.items():
        if any(k in n for k in kws): return intent
    return "khac"
