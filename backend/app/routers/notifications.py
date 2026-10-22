"""Router Thông báo admin (GĐ mở rộng 1) — dữ liệu từ bảng thong_bao."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Notification, User
from ..deps import get_current_user
from ..services.phan_trang import co_phan_trang, trang_hoa

router = APIRouter(prefix="/api/thong-bao", tags=["Thông báo"])


def out(n):
    return {
        "id": n.id, "type": n.type, "title": n.title, "content": n.content,
        "conversation_id": n.conversation_id, "customer_id": n.customer_id,
        "level": n.level, "is_read": bool(n.is_read), "sent_via_zalo": bool(n.sent_via_zalo),
        "created_at": str(n.created_at) if n.created_at else "",
    }


@router.get("")
def danh_sach(chua_doc: bool = False, loai: str = "", gioi_han: int = 100,
              trang: int = 0, kich_thuoc_trang: int = 20,
              db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    q = db.query(Notification)
    if chua_doc:
        q = q.filter(Notification.is_read == False)  # noqa: E712
    if loai:
        q = q.filter(Notification.type == loai)
    q = q.order_by(Notification.id.desc())
    # Phân trang (mục 1 đợt 3): khi có trang, phân trang trên TOÀN BỘ kết quả lọc
    # thay cho giới hạn gioi_han cũ; không truyền trang -> giữ hành vi cũ.
    if co_phan_trang(trang):
        return trang_hoa([out(n) for n in q.all()], trang, kich_thuoc_trang)
    return [out(n) for n in q.limit(min(gioi_han, 500)).all()]


@router.get("/dem-chua-doc")
def dem_chua_doc(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return {"chua_doc": db.query(Notification).filter(Notification.is_read == False).count()}  # noqa: E712


@router.post("/danh-dau-tat-ca-da-doc")
def danh_dau_tat_ca(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    so = db.query(Notification).filter(Notification.is_read == False).update({"is_read": True})  # noqa: E712
    db.commit()
    return {"da_danh_dau": so}


@router.post("/{tid}/da-doc")
def danh_dau_da_doc(tid: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    n = db.get(Notification, tid)
    if not n:
        raise HTTPException(404, "Không tìm thấy thông báo")
    n.is_read = True
    db.commit()
    return out(n)
