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
    return [{"id": a.id, "name": a.name, "account_type": a.account_type, "status": a.status, "last_error": a.last_error} for a in db.query(ZaloAccount).all()]
@router.post("/mock/nhan-tin-nhan")
def mock_inbound(data: InboundIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return process_inbound(db, data.external_id, data.customer_external_id, data.customer_name, data.content, data.zalo_account_id)
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
@router.post("/ca-nhan/gui-tin-nhan")
async def ca_nhan_send(req: Request, u: User = Depends(get_current_user)):
    body = await req.json()
    try:
        return ZaloPersonalConnector().send_text(body.get("thread_id") or body.get("conversation_id") or "", body.get("content") or "")
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
    if not external_id or not content:
        raise HTTPException(400, "Thiếu external_id hoặc nội dung tin nhắn")
    return process_inbound(db, str(external_id), str(customer_external_id), str(customer_name), str(content), body.get("zalo_account_id"))
