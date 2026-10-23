"""Dịch vụ ảnh đính kèm: tải ảnh khách gửi (từ URL Zalo) về máy chủ, lưu
trong thư mục `uploads` cạnh thư mục ứng dụng backend, và đọc lại thành
data URI base64 để gửi cho provider AI dạng multimodal.

Quy tắc an toàn:
- Chỉ tải từ URL http/https, chỉ chấp nhận content-type dạng ảnh.
- Giới hạn kích thước ~10MB (đọc theo luồng, vượt là hủy).
- Tên file là hash SHA-256 của nội dung → không trùng/không đoán được từ URL,
  không dùng tên do phía ngoài cung cấp (tránh path traversal ngay từ đầu).
- Mọi lỗi tải đều trả None để pipeline chính rơi về lưu URL gốc, không sập.
"""
import base64
import hashlib
import os

_THU_MUC_BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
THU_MUC_UPLOADS = os.path.join(_THU_MUC_BACKEND, "uploads")

GIOI_HAN_ANH_BYTES = 10 * 1024 * 1024  # ~10MB

_DUOI_THEO_MIME = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
}
_MIME_THEO_DUOI = {v: k for k, v in _DUOI_THEO_MIME.items()}
_MIME_THEO_DUOI[".jpg"] = "image/jpeg"


def _dam_bao_thu_muc():
    os.makedirs(THU_MUC_UPLOADS, exist_ok=True)


def tai_anh_tu_url(url: str):
    """Tải ảnh từ URL về thư mục uploads.

    Trả {"ten_file", "duong_dan", "mime", "kich_thuoc"} khi thành công,
    None khi bất kỳ lỗi nào (URL sai, không phải ảnh, quá lớn, mạng lỗi...).
    Hàm này được orchestrator gọi qua module (anh_service.tai_anh_tu_url)
    để kiểm thử có thể monkeypatch thay bằng bản giả lập.
    """
    try:
        u = str(url or "").strip()
        if not (u.startswith("http://") or u.startswith("https://")):
            return None
        from .ai_gateway import http_client
        with http_client(timeout=20) as client:
            with client.stream("GET", u, follow_redirects=True) as r:
                if r.status_code >= 400:
                    return None
                mime = (r.headers.get("content-type") or "").split(";")[0].strip().lower()
                if not mime.startswith("image/"):
                    return None
                do_dai_khai = r.headers.get("content-length")
                if do_dai_khai:
                    try:
                        if int(do_dai_khai) > GIOI_HAN_ANH_BYTES:
                            return None
                    except ValueError:
                        pass
                chunks = []
                tong = 0
                for chunk in r.iter_bytes(65536):
                    tong += len(chunk)
                    if tong > GIOI_HAN_ANH_BYTES:
                        return None
                    chunks.append(chunk)
        du_lieu = b"".join(chunks)
        if not du_lieu:
            return None
        duoi = _DUOI_THEO_MIME.get(mime, ".img")
        ten_file = hashlib.sha256(du_lieu).hexdigest()[:40] + duoi
        _dam_bao_thu_muc()
        duong_dan = os.path.join(THU_MUC_UPLOADS, ten_file)
        if not os.path.exists(duong_dan):
            with open(duong_dan, "wb") as f:
                f.write(du_lieu)
        return {"ten_file": ten_file, "duong_dan": duong_dan, "mime": mime, "kich_thuoc": len(du_lieu)}
    except Exception:
        return None


def doc_anh_data_uri(duong_dan: str) -> str:
    """Đọc file ảnh local → data URI base64 (data:image/...;base64,...).
    Lỗi (file mất/quá lớn) → trả "" để pipeline bỏ qua ảnh, không sập."""
    try:
        if not duong_dan or not os.path.isfile(duong_dan):
            return ""
        if os.path.getsize(duong_dan) > GIOI_HAN_ANH_BYTES:
            return ""
        duoi = os.path.splitext(duong_dan)[1].lower()
        mime = _MIME_THEO_DUOI.get(duoi, "image/jpeg")
        with open(duong_dan, "rb") as f:
            du_lieu = f.read()
        return f"data:{mime};base64," + base64.b64encode(du_lieu).decode("ascii")
    except Exception:
        return ""
