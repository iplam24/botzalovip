"""Dịch vụ thông báo cho quản trị viên (GĐ mở rộng 1).

- Tạo bản ghi Notification trong DB (Trung tâm thông báo trên giao diện).
- Chống trùng: cùng loại + cùng khách trong 10 phút chỉ tạo 1 thông báo
  (ngoại trừ gap_nhan_vien — yêu cầu gặp người thật luôn phải báo).
- Bật/tắt theo từng loại qua Cài đặt hệ thống (khóa thong_bao_<loai>).
- Tùy chọn gửi thêm qua Zalo cá nhân tới thread admin đã cấu hình
  (thong_bao_admin_zalo_thread_id), chỉ khi sự kiện thuộc kênh ca_nhan,
  giới hạn tối thiểu 60 giây giữa hai lần gửi để chống spam. Lỗi gửi chỉ
  ghi nhật ký, không làm sập pipeline xử lý tin nhắn.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from ..models import Notification, SystemLog
from .zalo_connector import ZaloPersonalConnector

CAC_LOAI = [
    "khach_moi", "co_so_dien_thoai", "du_thong_tin", "gap_nhan_vien",
    "khieu_nai", "bot_khong_tra_loi_duoc", "loi_he_thong",
]
CUA_SO_CHONG_TRUNG_PHUT = 10
GIOI_HAN_GUI_ZALO_GIAY = 60


def _doc_cai_dat(db: Session) -> dict:
    try:
        from ..routers.cai_dat import doc_cai_dat
        return doc_cai_dat(db)
    except Exception:
        return {}


def _gui_zalo_admin(db: Session, tb: Notification, cai_dat: dict, channel: str):
    """Gửi thông báo qua Zalo cá nhân cho admin nếu đã cấu hình + đúng kênh
    + qua giới hạn tần suất. Đánh dấu sent_via_zalo khi gửi thành công."""
    thread_id = str(cai_dat.get("thong_bao_admin_zalo_thread_id") or "").strip()
    if not thread_id or channel != "ca_nhan":
        return
    gan_nhat = (
        db.query(Notification)
        .filter(Notification.sent_via_zalo == True, Notification.id != tb.id)  # noqa: E712
        .order_by(Notification.id.desc())
        .first()
    )
    if gan_nhat and gan_nhat.created_at:
        moc = gan_nhat.created_at
        if moc.tzinfo is None:
            moc = moc.replace(tzinfo=timezone.utc)
        if (datetime.now(timezone.utc) - moc).total_seconds() < GIOI_HAN_GUI_ZALO_GIAY:
            return
    ZaloPersonalConnector().send_text(thread_id, f"[{tb.title}] {tb.content}")
    tb.sent_via_zalo = True
    db.commit()


def notify(db: Session, loai: str, title: str, content: str, customer_id=None,
           conversation_id=None, level: str = "thong_tin", channel: str = "mo_phong"):
    """Tạo thông báo (nếu loại đang bật + không trùng). Trả Notification hoặc None.

    Hàm này KHÔNG ném ngoại lệ ra ngoài: thông báo là chức năng phụ trợ,
    tuyệt đối không được làm hỏng luồng xử lý tin nhắn chính.
    """
    try:
        cai_dat = _doc_cai_dat(db)
        if cai_dat.get(f"thong_bao_{loai}", True) is False:
            return None
        if loai != "gap_nhan_vien" and customer_id is not None:
            moc = datetime.now(timezone.utc) - timedelta(minutes=CUA_SO_CHONG_TRUNG_PHUT)
            trung = (
                db.query(Notification)
                .filter(Notification.type == loai, Notification.customer_id == customer_id,
                        Notification.created_at >= moc)
                .first()
            )
            if trung:
                return None
        tb = Notification(type=loai, title=title, content=content,
                          customer_id=customer_id, conversation_id=conversation_id, level=level)
        db.add(tb)
        db.commit()
        db.refresh(tb)
        try:
            _gui_zalo_admin(db, tb, cai_dat, channel)
        except Exception as e:
            try:
                db.add(SystemLog(level="warning", module="thong_bao",
                                 message=f"Lỗi gửi thông báo Zalo cho admin: {e}"))
                db.commit()
            except Exception:
                pass
        return tb
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return None
