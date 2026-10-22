"""Router Cài đặt hệ thống — lưu trong bảng system_settings (khóa/giá trị JSON).

Các khóa được hỗ trợ (có giá trị mặc định khi chưa lưu):
- tu_dong_tra_loi_toan_cuc (bool): bật/tắt bot trả lời tự động toàn cục
- thoi_gian_gom_tin_ms (int): thời gian chờ gom nhiều tin liên tiếp
- che_do_duyet_truoc_khi_gui (bool): bot chỉ soạn, nhân viên duyệt mới gửi
- mui_gio (str): múi giờ hiển thị, mặc định Asia/Ho_Chi_Minh
- so_tin_nhan_ngu_canh (int): số tin gần nhất đưa vào ngữ cảnh AI
- ten_hien_thi_bot (str): tên/xưng hô của bot khi trả lời
"""
import json
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import SystemSetting, User
from ..deps import get_current_user, require_admin

router = APIRouter(prefix="/api/cai-dat", tags=["Cài đặt hệ thống"])

MAC_DINH = {
    "tu_dong_tra_loi_toan_cuc": True,
    "thoi_gian_gom_tin_ms": 1500,
    "che_do_duyet_truoc_khi_gui": False,
    "mui_gio": "Asia/Ho_Chi_Minh",
    "so_tin_nhan_ngu_canh": 10,
    "ten_hien_thi_bot": "Trợ lý hỗ trợ khách hàng",
}


class CaiDatIn(BaseModel):
    tu_dong_tra_loi_toan_cuc: Optional[bool] = None
    thoi_gian_gom_tin_ms: Optional[int] = None
    che_do_duyet_truoc_khi_gui: Optional[bool] = None
    mui_gio: Optional[str] = None
    so_tin_nhan_ngu_canh: Optional[int] = None
    ten_hien_thi_bot: Optional[str] = None


def doc_cai_dat(db: Session) -> dict:
    """Đọc toàn bộ cài đặt: giá trị đã lưu trong DB ghi đè mặc định."""
    ket_qua = dict(MAC_DINH)
    for dong in db.query(SystemSetting).all():
        try:
            ket_qua[dong.key] = json.loads(dong.value)
        except Exception:
            ket_qua[dong.key] = dong.value
    return ket_qua


@router.get("")
def lay_cai_dat(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return doc_cai_dat(db)


@router.put("")
def cap_nhat_cai_dat(data: CaiDatIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    for khoa, gia_tri in data.model_dump(exclude_unset=True).items():
        if gia_tri is None:
            continue
        dong = db.get(SystemSetting, khoa)
        if dong:
            dong.value = json.dumps(gia_tri, ensure_ascii=False)
        else:
            db.add(SystemSetting(key=khoa, value=json.dumps(gia_tri, ensure_ascii=False)))
    db.commit()
    return doc_cai_dat(db)
