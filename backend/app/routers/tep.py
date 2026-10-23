"""Phục vụ tệp đính kèm đã tải về máy chủ (ảnh khách gửi).

GET /api/tep/{ten_file} — BẮT BUỘC đăng nhập (JWT như mọi API khác).
Chống path traversal: tên tệp phải là tên thuần (basename), đường dẫn
tuyệt đối sau khi chuẩn hoá phải nằm TRONG thư mục uploads.
"""
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..models import User
from ..deps import get_current_user
from ..services import anh_service

router = APIRouter(prefix="/api/tep", tags=["Tệp đính kèm"])


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
