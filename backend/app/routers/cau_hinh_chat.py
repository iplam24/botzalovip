"""Trợ lý cấu hình qua đoạn chat (Đợt nâng cấp 3, mục 2).

- POST /api/cau-hinh-chat/phan-tich: phân tích câu lệnh tự nhiên -> danh sách
  thay đổi CHỜ DUYỆT kèm giá trị cũ/mới. KHÔNG thay đổi cài đặt ở bước này.
- POST /api/cau-hinh-chat/ap-dung (chỉ quản trị viên): áp dụng các thay đổi
  đã duyệt qua cùng cổng kiểm tra như PUT /api/cai-dat + ghi SystemLog.
"""
from typing import Any, List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..deps import get_current_user, require_admin
from ..services import cau_hinh_chat_service

router = APIRouter(prefix="/api/cau-hinh-chat", tags=["Trợ lý cấu hình"])


class PhanTichIn(BaseModel):
    cau_lenh: str


class ThayDoiIn(BaseModel):
    khoa: str
    gia_tri: Optional[Any] = None
    gia_tri_moi: Optional[Any] = None


class ApDungIn(BaseModel):
    thay_doi: List[ThayDoiIn]


@router.post("/phan-tich")
def phan_tich(data: PhanTichIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return cau_hinh_chat_service.phan_tich(db, data.cau_lenh)


@router.post("/ap-dung")
def ap_dung(data: ApDungIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    thay_doi = [m.model_dump() for m in data.thay_doi]
    return cau_hinh_chat_service.ap_dung(db, admin, thay_doi)
