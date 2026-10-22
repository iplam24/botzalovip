from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, AIProviderConfig
from ..schemas import AITestIn
from ..deps import get_current_user
from ..services import knowledge_service, ai_gateway
router = APIRouter(prefix="/api/kiem-thu-ai", tags=["Trung tâm kiểm thử AI"])
@router.post("")
def test_ai(data: AITestIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    chunks=knowledge_service.retrieve(db, data.question, limit=5, service_id=data.service_id)
    provider=db.get(AIProviderConfig, data.provider_id) if data.provider_id else ai_gateway.get_default_provider(db)
    try:
        reply, model = ai_gateway.generate_reply(db, provider, data.question, chunks, [])
    except ai_gateway.AIError as e:
        raise HTTPException(502, f"Lỗi nhà cung cấp AI: {e}")
    return {"cau_tra_loi": reply, "model": model, "nguon": chunks}
@router.get("/cong-cu")
def tools(u: User = Depends(get_current_user)):
    return [{"ten": "tra_cuu_tri_thuc", "mo_ta": "Tìm kiếm trong kho tri thức", "trang_thai": "bat"}, {"ten": "gan_nhan", "mo_ta": "Gắn nhãn khách hàng", "trang_thai": "bat"}, {"ten": "chuyen_nhan_vien", "mo_ta": "Chuyển hội thoại cho nhân viên", "trang_thai": "bat"}]
