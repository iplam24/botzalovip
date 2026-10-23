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
import time

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


def _cac_file_anh() -> list:
    """Mọi file trong thư mục uploads (đều là ảnh khách đã tải về — tên file
    là hash nội dung). Thư mục chưa có -> coi như rỗng, tự tạo."""
    try:
        _dam_bao_thu_muc()
        return [os.path.join(THU_MUC_UPLOADS, ten) for ten in os.listdir(THU_MUC_UPLOADS)
                if os.path.isfile(os.path.join(THU_MUC_UPLOADS, ten))]
    except Exception:
        return []


def thong_ke_anh() -> dict:
    """Thống kê lưu trữ ảnh khách: số file + tổng dung lượng."""
    files = _cac_file_anh()
    tong = 0
    for duong_dan in files:
        try:
            tong += os.path.getsize(duong_dan)
        except OSError:
            pass
    return {"so_anh": len(files), "tong_bytes": tong,
            "tong_mb": round(tong / 1024 / 1024, 3)}


def don_dep_anh_cu(db, so_ngay) -> dict:
    """Xóa file ảnh có mtime cũ hơn `so_ngay` ngày (chính sách lưu ảnh của LAM:
    ảnh KHÔNG lưu lâu kẻo nặng server — bot chỉ cần ảnh ở thời điểm trả lời).

    Nguồn thời gian nhất quán: mtime của file vật lý (đúng bản chất lưu trữ).
    CHỈ xóa file, KHÔNG sửa DB: tin nhắn cũ vẫn trỏ /api/tep/<file>, API trả
    404 và giao diện hiện ô "Ảnh đã hết hạn lưu trữ" thay cho ảnh vỡ.
    Ghi 1 SystemLog tổng kết (số file + MB giải phóng). Lỗi từng file bị bỏ
    qua, không bao giờ làm sập tiến trình gọi (kể cả luồng nền).
    """
    try:
        so_ngay = int(so_ngay)
    except (TypeError, ValueError):
        so_ngay = 7
    so_ngay = max(1, so_ngay)
    nguong = time.time() - so_ngay * 86400
    da_xoa = 0
    giai_phong = 0
    for duong_dan in _cac_file_anh():
        try:
            if os.path.getmtime(duong_dan) < nguong:
                kich_thuoc = os.path.getsize(duong_dan)
                os.remove(duong_dan)
                da_xoa += 1
                giai_phong += kich_thuoc
        except OSError:
            continue
    giai_phong_mb = round(giai_phong / 1024 / 1024, 3)
    if db is not None:
        try:
            from ..models import SystemLog
            db.add(SystemLog(
                level="info", module="don_dep_anh",
                message=f"Dọn ảnh khách quá hạn {so_ngay} ngày: đã xóa {da_xoa} file, "
                        f"giải phóng {giai_phong_mb} MB"))
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
    return {"da_xoa": da_xoa, "giai_phong_bytes": giai_phong,
            "giai_phong_mb": giai_phong_mb}


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
