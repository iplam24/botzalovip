"""Bạn bè Zalo + phân bổ admin phụ trách (Đợt nâng cấp 2, mục 9.5).

- Danh sách bạn bè lấy THẬT từ sidecar zca-js (getAllFriends). Sidecar
  offline/chưa đăng nhập/thư viện không hỗ trợ -> trả lỗi thật 502/501,
  TUYỆT ĐỐI không chế dữ liệu bạn bè.
- Đồng bộ = UPSERT theo zalo_friend_id: bạn mới thì thêm, bạn cũ chỉ cập
  nhật tên/avatar — admin đã phân bổ và ghi chú được GIỮ NGUYÊN.
- Gán/đổi/bỏ admin phụ trách cho 1 bạn hoặc nhiều bạn cùng lúc; lọc theo
  admin / trạng thái phân bổ; thống kê số bạn theo admin.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import PhanBoBanBe, User
from ..schemas import PhanBoIn, PhanBoHangLoatIn
from ..deps import get_current_user, require_admin
from ..services.zalo_connector import ZaloPersonalConnector
from ..services.phan_trang import co_phan_trang, trang_hoa

router = APIRouter(prefix="/api/ban-be-zalo", tags=["Bạn bè Zalo"])


def out(b: PhanBoBanBe):
    return {
        "id": b.id, "zalo_friend_id": b.zalo_friend_id, "ten_hien_thi": b.ten_hien_thi,
        "avatar_url": b.avatar_url, "admin_user_id": b.admin_user_id,
        "admin_username": b.admin.username if b.admin else None,
        "admin_full_name": b.admin.full_name if b.admin else None,
        "ghi_chu": b.ghi_chu,
        "updated_at": str(b.updated_at) if b.updated_at else "",
        "created_at": str(b.created_at) if b.created_at else "",
    }


@router.get("")
def danh_sach(tu_khoa: str = "", admin_id: str = "", trang: int = 0, kich_thuoc_trang: int = 20, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    """admin_id: '' = tất cả | 'chua_phan_bo' = chưa có admin | '<id>' = của admin đó."""
    q = db.query(PhanBoBanBe)
    if admin_id == "chua_phan_bo":
        q = q.filter(PhanBoBanBe.admin_user_id == None)  # noqa: E711
    elif admin_id:
        try:
            q = q.filter(PhanBoBanBe.admin_user_id == int(admin_id))
        except ValueError:
            raise HTTPException(400, "admin_id không hợp lệ")
    ds = q.order_by(PhanBoBanBe.ten_hien_thi).all()
    if tu_khoa:
        tk = tu_khoa.lower()
        ds = [b for b in ds if tk in (b.ten_hien_thi or "").lower() or tk in (b.zalo_friend_id or "").lower()]
    ket_qua = [out(b) for b in ds]
    if co_phan_trang(trang):
        return trang_hoa(ket_qua, trang, kich_thuoc_trang)
    return ket_qua


@router.get("/thong-ke")
def thong_ke(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    tong = db.query(PhanBoBanBe).count()
    chua = db.query(PhanBoBanBe).filter(PhanBoBanBe.admin_user_id == None).count()  # noqa: E711
    theo_admin = []
    for admin in db.query(User).order_by(User.id).all():
        so = db.query(PhanBoBanBe).filter(PhanBoBanBe.admin_user_id == admin.id).count()
        theo_admin.append({"admin_user_id": admin.id, "username": admin.username or admin.email,
                           "full_name": admin.full_name, "so_ban": so})
    return {"tong_ban": tong, "chua_phan_bo": chua, "da_phan_bo": tong - chua, "theo_admin": theo_admin}


@router.post("/dong-bo")
def dong_bo(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Đồng bộ danh sách bạn bè từ tài khoản Zalo cá nhân đang đăng nhập."""
    try:
        ban_be = ZaloPersonalConnector().danh_sach_ban_be()
    except NotImplementedError as e:
        raise HTTPException(501, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    moi = cap_nhat = 0
    for b in ban_be:
        fid = str(b.get("id") or b.get("zalo_friend_id") or "")
        if not fid:
            continue
        ten = str(b.get("ten_hien_thi") or b.get("display_name") or "")
        avatar = str(b.get("avatar_url") or b.get("avatar") or "")
        dong = db.query(PhanBoBanBe).filter(PhanBoBanBe.zalo_friend_id == fid).first()
        if dong:
            dong.ten_hien_thi = ten or dong.ten_hien_thi
            dong.avatar_url = avatar or dong.avatar_url
            cap_nhat += 1
        else:
            db.add(PhanBoBanBe(zalo_friend_id=fid, ten_hien_thi=ten, avatar_url=avatar))
            moi += 1
    db.commit()
    return {"tong_tu_zalo": len(ban_be), "moi": moi, "cap_nhat": cap_nhat,
            "tong_trong_he_thong": db.query(PhanBoBanBe).count()}


def _kiem_admin(db: Session, admin_user_id):
    if admin_user_id is None:
        return None
    admin = db.get(User, admin_user_id)
    if not admin:
        raise HTTPException(400, "Không tìm thấy người dùng được phân bổ")
    return admin


@router.put("/{bid}/phan-bo")
def phan_bo_mot(bid: int, data: PhanBoIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    b = db.get(PhanBoBanBe, bid)
    if not b:
        raise HTTPException(404, "Không tìm thấy bạn bè")
    _kiem_admin(db, data.admin_user_id)
    b.admin_user_id = data.admin_user_id
    if data.ghi_chu is not None:
        b.ghi_chu = data.ghi_chu
    db.commit(); db.refresh(b)
    return out(b)


@router.put("/phan-bo-hang-loat")
def phan_bo_hang_loat(data: PhanBoHangLoatIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    _kiem_admin(db, data.admin_user_id)
    da_cap_nhat = 0
    for bid in data.ids:
        b = db.get(PhanBoBanBe, bid)
        if b:
            b.admin_user_id = data.admin_user_id
            da_cap_nhat += 1
    db.commit()
    return {"da_cap_nhat": da_cap_nhat, "admin_user_id": data.admin_user_id}
