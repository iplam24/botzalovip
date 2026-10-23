from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Conversation, Message, User
from ..schemas import SendMessageIn
from ..deps import get_current_user
from ..services.phan_trang import co_phan_trang, trang_hoa
router = APIRouter(prefix="/api/hoi-thoai", tags=["Hội thoại"])
def out(c, db=None):
    d = {"id": c.id, "customer_id": c.customer_id, "status": c.status, "channel": getattr(c, "channel", "mo_phong"), "bot_enabled": c.bot_enabled, "human_takeover": c.human_takeover, "labels": c.labels, "priority": c.priority, "assignee": c.assignee, "created_at": str(c.created_at) if c.created_at else "", "updated_at": str(c.updated_at) if c.updated_at else ""}
    if getattr(c, "customer", None):
        d["customer_name"] = c.customer.display_name or ""
        d["customer_phone"] = c.customer.phone or ""
        d["customer_labels"] = c.customer.labels or ""
    if db is not None:
        last = db.query(Message).filter(Message.conversation_id == c.id).order_by(Message.id.desc()).first()
        d["last_message"] = last.content if last else ""
        d["last_sender_type"] = last.sender_type if last else ""
        d["last_message_at"] = str(last.created_at) if last else ""
        d["message_count"] = db.query(Message).filter(Message.conversation_id == c.id).count()
    return d
@router.get("")
def list_c(trang_thai: str = "", tu_khoa: str = "", loc_tin: str = "", trang: int = 0, kich_thuoc_trang: int = 20, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    """Danh sách hội thoại — sắp xếp theo HOẠT ĐỘNG GẦN NHẤT (tin cuối mới nhất
    lên đầu, hội thoại chưa có tin xếp theo thời gian cập nhật). loc_tin:
    'da_nhan_tin' (>= 1 tin) | 'chua_nhan_tin' (0 tin) — mục 9.2."""
    q = db.query(Conversation)
    if trang_thai: q = q.filter(Conversation.status == trang_thai)
    ds = q.order_by(Conversation.id.desc()).all()
    ket_qua = [out(c, db) for c in ds]
    if loc_tin == "da_nhan_tin":
        ket_qua = [c for c in ket_qua if (c.get("message_count") or 0) >= 1]
    elif loc_tin == "chua_nhan_tin":
        ket_qua = [c for c in ket_qua if (c.get("message_count") or 0) == 0]
    if tu_khoa:
        tk = tu_khoa.lower()
        ket_qua = [c for c in ket_qua if tk in (c.get("customer_name","") + " " + c.get("last_message","")).lower()]
    ket_qua.sort(key=lambda c: (c.get("last_message_at") or "", c.get("updated_at") or ""), reverse=True)
    # Phân trang phía máy chủ (mục 1 đợt 3): chỉ khi client truyền trang >= 1,
    # bộ lọc ở trên được giữ nguyên cho mọi trang.
    if co_phan_trang(trang):
        return trang_hoa(ket_qua, trang, kich_thuoc_trang)
    return ket_qua
@router.get("/{cid}")
def get_c(cid:int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    c=db.get(Conversation,cid)
    if not c: raise HTTPException(404,"Không tìm thấy")
    msgs=db.query(Message).filter(Message.conversation_id==cid).order_by(Message.created_at).all()
    return {**out(c, db), "messages": [{"id": m.id, "sender_type": m.sender_type, "content": m.content, "external_id": m.external_id, "status": m.status, "error": m.error, "attachment_url": getattr(m, "attachment_url", "") or "", "attachment_type": getattr(m, "attachment_type", "") or "", "created_at": str(m.created_at) if m.created_at else ""} for m in msgs]}
@router.post("/{cid}/tam-dung-bot")
def pause(cid:int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    c=db.get(Conversation,cid)
    if not c: raise HTTPException(404,"Không tìm thấy")
    c.bot_enabled=False; db.commit(); return out(c, db)
@router.post("/{cid}/tra-lai-bot")
def resume(cid:int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    c=db.get(Conversation,cid)
    if not c: raise HTTPException(404,"Không tìm thấy")
    c.bot_enabled=True; c.human_takeover=False; db.commit(); return out(c, db)
@router.post("/{cid}/chuyen-nhan-vien")
def transfer(cid:int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    c=db.get(Conversation,cid)
    if not c: raise HTTPException(404,"Không tìm thấy")
    c.human_takeover=True; db.commit(); return out(c, db)
@router.post("/{cid}/gui-tin-nhan")
def send(cid:int, data: SendMessageIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    c=db.get(Conversation,cid)
    if not c: raise HTTPException(404,"Không tìm thấy")
    # Hội thoại kênh cá nhân: gửi THẬT qua sidecar Zalo, lỗi thì ghi loi_gui chứ không giả da_gui
    status="da_gui"; error=""
    if getattr(c, "channel", "mo_phong") == "ca_nhan" and data.sender_type in ("bot", "nhan_vien"):
        from ..services.zalo_connector import ZaloPersonalConnector
        cust = c.customer
        try:
            ZaloPersonalConnector().send_text(str(cust.external_id), data.content)
        except Exception as e:
            status="loi_gui"; error=str(e)
    m=Message(conversation_id=cid, sender_type=data.sender_type, content=data.content, status=status, error=error); db.add(m); db.commit(); db.refresh(m)
    return {"id": m.id, "content": m.content, "sender_type": m.sender_type, "status": m.status, "error": m.error, "created_at": str(m.created_at) if m.created_at else ""}

@router.post("/{cid}/doi-trang-thai")
def doi_trang_thai(cid: int, payload: dict, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    c = db.get(Conversation, cid)
    if not c: raise HTTPException(404, "Không tìm thấy")
    if payload.get("status") in ("dang_xu_ly", "da_giai_quyet", "cho_phan_hoi"): c.status = payload["status"]
    if "labels" in payload: c.labels = payload.get("labels") or ""
    if "priority" in payload: c.priority = payload.get("priority") or c.priority
    db.commit(); return out(c, db)
