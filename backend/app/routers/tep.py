"""Phục vụ tệp đính kèm đã tải về máy chủ (ảnh khách gửi).

GET /api/tep/{ten_file} — BẮT BUỘC đăng nhập (JWT như mọi API khác).
Chống path traversal: tên tệp phải là tên thuần (basename), đường dẫn
tuyệt đối sau khi chuẩn hoá phải nằm TRONG thư mục uploads.
"""
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..deps import get_current_user, require_admin
from ..services import anh_service

router = APIRouter(prefix="/api/tep", tags=["Tệp đính kèm"])


def _so_ngay_luu(db: Session) -> int:
    from .cai_dat import doc_cai_dat
    try:
        return max(1, int(doc_cai_dat(db).get("so_ngay_luu_anh_khach") or 7))
    except (TypeError, ValueError):
        return 7


@router.get("/thong-ke")
def thong_ke_anh(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    """Thống kê ảnh khách đang lưu trên máy chủ + hạn lưu theo cài đặt."""
    return {**anh_service.thong_ke_anh(), "so_ngay_luu": _so_ngay_luu(db)}


@router.post("/don-dep")
def don_dep_ngay(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Dọn ngay các ảnh quá hạn lưu (theo cài đặt so_ngay_luu_anh_khach).
    Chỉ quản trị viên. Trả {da_xoa, giai_phong_mb, ...}."""
    return anh_service.don_dep_anh_cu(db, _so_ngay_luu(db))


@router.get("/{ten_file}")
def tai_tep(ten_file: str, u: User = Depends(get_current_user)):
    if (not ten_file or "/" in ten_file or "\\" in ten_file or ".." in ten_file
            or ten_file != os.path.basename(ten_file)):
        raise HTTPException(400, "Tên tệp không hợp lệ")
    goc = os.path.abspath(anh_service.THU_MUC_UPLOADS)
    duong_dan = os.path.abspath(os.path.join(goc, ten_file))
    if not duong_dan.startswith(goc + os.sep):
        raise HTTPException(400, "Tên tệp không hợp lệ")
    if not os.path.isfile(duong_dan):
        raise HTTPException(404, "Không tìm thấy tệp")
    return FileResponse(duong_dan)
