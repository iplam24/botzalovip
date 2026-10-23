from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
import os
from ..database import get_db
from ..models import ZaloAccount, User
from ..schemas import InboundIn
from ..deps import get_current_user
from ..services.orchestrator import process_inbound
from ..services.zalo_connector import MockZaloConnector, ZaloOAStubConnector, ZaloPersonalConnector
router = APIRouter(prefix="/api/zalo", tags=["Tài khoản Zalo"])
@router.get("/tai-khoan")
def list_a(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    # Trạng thái tài khoản cá nhân phải lấy TRỰC TIẾP từ sidecar mỗi lần xem,
    # không dùng trạng thái tĩnh đã seed trong DB (từng hiển thị sai "chua_ket_noi" khi đã kết nối).
    ket_qua = []
    for a in db.query(ZaloAccount).all():
        trang_thai, loi = a.status, a.last_error
        if a.account_type == "ca_nhan":
            try:
                s = ZaloPersonalConnector().status()
                trang_thai = s.get("trang_thai", trang_thai)
                loi = "" if trang_thai == "da_ket_noi" else (s.get("thong_bao", "") or loi)
            except Exception:
                pass
        ket_qua.append({"id": a.id, "name": a.name, "account_type": a.account_type, "status": trang_thai, "last_error": loi})
    return ket_qua
@router.post("/mock/nhan-tin-nhan")
def mock_inbound(data: InboundIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return process_inbound(db, data.external_id, data.customer_external_id, data.customer_name, data.content,
                           data.zalo_account_id, mentions=data.mentions, la_nhom=data.la_nhom,
                           bot_uid=data.bot_uid, nguoi_gui_id=data.nguoi_gui_id, cli_msg_id=data.cli_msg_id,
                           dinh_kem=data.dinh_kem)
@router.post("/kiem-tra-connector")
def check_connector(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    mock = MockZaloConnector().status(); oa = ZaloOAStubConnector("").status(); ca_nhan = ZaloPersonalConnector().status()
    return {"mock": mock, "oa_stub": oa, "ca_nhan": ca_nhan, "gioi_han": "Zalo cá nhân dùng thư viện không chính thức zca-js qua sidecar, có rủi ro bị hạn chế/khóa tài khoản; OA cần token/app phê duyệt"}
@router.get("/trang-thai")
def status(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return MockZaloConnector().status()

# ---- Zalo cá nhân qua sidecar zca-js ----
@router.get("/ca-nhan/trang-thai")
def ca_nhan_status(u: User = Depends(get_current_user)):
    return ZaloPersonalConnector().status()
@router.post("/ca-nhan/dang-nhap-qr")
def ca_nhan_qr(u: User = Depends(get_current_user)):
    return ZaloPersonalConnector().connect()
@router.post("/ca-nhan/ngat-ket-noi")
def ca_nhan_disconnect(u: User = Depends(get_current_user)):
    return ZaloPersonalConnector().disconnect()
@router.post("/ca-nhan/ngat-lien-ket")
def ca_nhan_unlink(u: User = Depends(get_current_user)):
    """Ngắt LIÊN KẾT hẳn: sidecar dừng phiên + xóa dữ liệu phiên đã lưu
    (phải quét QR lại). Chỉ tồn tại vì sidecar hỗ trợ thật thao tác này."""
    return ZaloPersonalConnector().ngat_lien_ket()
@router.get("/ca-nhan/sticker-goi-y")
def ca_nhan_sticker_goi_y(q: str = "", u: User = Depends(get_current_user)):
    """Gợi ý sticker thật từ Zalo (sidecar -> zca-js getStickers) để admin
    lấy {id, cate_id, type} đưa vào cài đặt 'Danh sách sticker của bot'."""
    try:
        return {"ket_qua": ZaloPersonalConnector().goi_y_sticker(q)}
    except (RuntimeError, NotImplementedError) as e:
        raise HTTPException(502, str(e))

@router.post("/ca-nhan/gui-tin-nhan")
async def ca_nhan_send(req: Request, u: User = Depends(get_current_user)):
    body = await req.json()
    # Gửi thủ công: nếu client truyền loai_thread/thread_type (1 = nhóm) thì
    # truyền tiếp xuống connector; không truyền -> 0 (User) như hành vi cũ.
    try:
        loai_thread = int(body.get("loai_thread", body.get("thread_type", 0)) or 0)
    except (TypeError, ValueError):
        loai_thread = 0
    try:
        return ZaloPersonalConnector().send_text(body.get("thread_id") or body.get("conversation_id") or "", body.get("content") or "", loai_thread)
    except (RuntimeError, NotImplementedError) as e:
        raise HTTPException(502, str(e))

@router.post("/webhook/ca-nhan")
async def webhook_ca_nhan(req: Request, db: Session = Depends(get_db), x_connector_secret: str = Header(default="")):
    """Nhận tin thật từ sidecar. Nếu env ZALO_CONNECTOR_SECRET / CONNECTOR_SECRET
    đã đặt thì bắt buộc khớp header X-Connector-Secret, sai -> 401.
    Không ghi secret vào log."""
    expected = os.getenv("ZALO_CONNECTOR_SECRET") or os.getenv("CONNECTOR_SECRET") or ""
    if expected and x_connector_secret != expected:
        raise HTTPException(401, "Mã bí mật connector không hợp lệ")
    body = await req.json()
    external_id = body.get("external_id") or body.get("message_id") or body.get("msg_id") or ""
    customer_external_id = body.get("customer_external_id") or body.get("thread_id") or body.get("sender_id") or "ca-nhan-khong-ro"
    customer_name = body.get("customer_name") or body.get("sender_name") or "Khách Zalo cá nhân"
    content = body.get("content") or body.get("message") or body.get("text") or ""
    # Đính kèm (ảnh khách gửi): sidecar trích thành [{loai: "anh", url, url_thumb}].
    # Tin CHỈ có ảnh (không có chữ) vẫn hợp lệ — không còn bắt buộc content.
    dinh_kem = [dk for dk in (body.get("dinh_kem") or [])
                if isinstance(dk, dict) and dk.get("loai") == "anh" and dk.get("url")] \
        if isinstance(body.get("dinh_kem"), list) else []
    if not external_id or (not content and not dinh_kem):
        raise HTTPException(400, "Thiếu external_id hoặc nội dung tin nhắn")
    # Trường nhóm Zalo (mục 7): sidecar gửi kèm mentions + cờ nhóm + UID của bot
    mentions = body.get("mentions") if isinstance(body.get("mentions"), list) else None
    la_nhom = bool(body.get("la_nhom") or body.get("loai_thread") == 1 or body.get("thread_type") == 1)
    return process_inbound(db, str(external_id), str(customer_external_id), str(customer_name), str(content),
                           body.get("zalo_account_id"), channel="ca_nhan",
                           mentions=mentions, la_nhom=la_nhom,
                           bot_uid=str(body.get("bot_uid") or body.get("tai_khoan_id") or ""),
                           nguoi_gui_id=str(body.get("nguoi_gui_id") or body.get("uid_from") or ""),
                           cli_msg_id=str(body.get("cli_msg_id") or body.get("cliMsgId") or ""),
                           dinh_kem=dinh_kem)
