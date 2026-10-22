import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from openpyxl import Workbook
from openpyxl.styles import Font
from ..database import get_db
from ..models import Customer, Conversation, CollectedInfo, User
from ..schemas import CustomerIn, CollectedInfoIn, CollectedInfoUpdate
from ..deps import get_current_user, require_admin
from ..services.extraction_service import CAC_TRUONG
from ..services.phan_trang import co_phan_trang, trang_hoa

router = APIRouter(prefix="/api/khach-hang", tags=["Khách hàng"])

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

def out(c): return {"id": c.id, "external_id": c.external_id, "display_name": c.display_name, "phone": c.phone, "email": c.email or "", "labels": c.labels, "group_name": c.group_name, "notes": c.notes, "assignee": c.assignee, "memory_summary": getattr(c, "memory_summary", "") or "", "last_interaction_at": str(c.last_interaction_at) if c.last_interaction_at else "", "created_at": str(c.created_at) if c.created_at else ""}

@router.get("")
def list_c(tu_khoa: str = "", nhan: str = "", trang: int = 0, kich_thuoc_trang: int = 20, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    q = db.query(Customer)
    if tu_khoa:
        tk = f"%{tu_khoa}%"
        q = q.filter((Customer.display_name.like(tk)) | (Customer.phone.like(tk)) | (Customer.notes.like(tk)))
    if nhan: q = q.filter(Customer.labels.contains(nhan))
    ds = [out(c) for c in q.order_by(Customer.id.desc()).all()]
    if co_phan_trang(trang):
        return trang_hoa(ds, trang, kich_thuoc_trang)
    return ds

def _loc_khach(db: Session, tu_khoa: str = "", nhan: str = "", tu_ngay: str = "", den_ngay: str = ""):
    q = db.query(Customer)
    if tu_khoa:
        tk = f"%{tu_khoa}%"
        q = q.filter((Customer.display_name.like(tk)) | (Customer.phone.like(tk)) | (Customer.email.like(tk)) | (Customer.notes.like(tk)))
    if nhan:
        q = q.filter(Customer.labels.contains(nhan))
    if tu_ngay:
        try: q = q.filter(Customer.last_interaction_at >= datetime.fromisoformat(tu_ngay))
        except ValueError: pass
    if den_ngay:
        try: q = q.filter(Customer.last_interaction_at <= datetime.fromisoformat(den_ngay))
        except ValueError: pass
    return q

@router.get("/xuat-excel")
def xuat_excel(tu_khoa: str = "", nhan: str = "", tu_ngay: str = "", den_ngay: str = "",
               db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    """Xuất danh sách khách hàng + thông tin thu thập chính ra .xlsx (tên cột tiếng Việt)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Khách hàng"
    tieu_de = ["Họ tên", "Số điện thoại", "Email", "Nhãn", "Nhóm", "Dịch vụ quan tâm",
                "Nhu cầu", "Ngân sách", "Lần tương tác cuối", "Số hội thoại"]
    ws.append(tieu_de)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for c in _loc_khach(db, tu_khoa, nhan, tu_ngay, den_ngay).order_by(Customer.id.desc()).all():
        thu_thap = {}
        for tt in (db.query(CollectedInfo)
                   .filter(CollectedInfo.customer_id == c.id,
                           CollectedInfo.field.in_(["dich_vu_quan_tam", "nhu_cau", "ngan_sach"]))
                   .order_by(CollectedInfo.id.desc()).all()):
            thu_thap.setdefault(tt.field, tt.value)  # bản ghi mới nhất của từng trường
        so_hoi_thoai = db.query(Conversation).filter(Conversation.customer_id == c.id).count()
        ws.append([
            c.display_name or "", c.phone or "", c.email or "", c.labels or "", c.group_name or "",
            thu_thap.get("dich_vu_quan_tam", ""), thu_thap.get("nhu_cau", ""), thu_thap.get("ngan_sach", ""),
            c.last_interaction_at.strftime("%d/%m/%Y %H:%M") if c.last_interaction_at else "",
            so_hoi_thoai,
        ])
    for col, rong in zip("ABCDEFGHIJ", [26, 15, 28, 20, 16, 24, 30, 16, 18, 12]):
        ws.column_dimensions[col].width = rong
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    ten_file = f"danh-sach-khach-hang-{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    return StreamingResponse(buf, media_type=XLSX_MEDIA,
                             headers={"Content-Disposition": f'attachment; filename="{ten_file}"'})

@router.post("")
def create_c(data: CustomerIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    c = Customer(**data.model_dump()); db.add(c); db.commit(); db.refresh(c); return out(c)
@router.get("/{cid}")
def get_c(cid: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    c=db.get(Customer,cid)
    if not c: raise HTTPException(404,"Không tìm thấy")
    return out(c)
@router.put("/{cid}")
def upd_c(cid: int, data: CustomerIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    c=db.get(Customer,cid)
    if not c: raise HTTPException(404,"Không tìm thấy")
    for k,v in data.model_dump(exclude_unset=True).items(): setattr(c,k,v)
    db.commit(); return out(c)
@router.delete("/{cid}")
def del_c(cid: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    c=db.get(Customer,cid)
    if not c: raise HTTPException(404,"Không tìm thấy")
    db.delete(c); db.commit(); return {"da_xoa": True}

@router.post("/{cid}/tom-tat-bo-nho")
def tom_tat_bo_nho(cid: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    """Tóm tắt lại hồ sơ dài hạn của khách NGAY (không chờ đủ số tin)."""
    from ..services import memory_service
    c = _khach_hoac_404(db, cid)
    tom_tat = memory_service.cap_nhat_tom_tat_bo_nho(db, c, force=True)
    db.refresh(c)
    return {"id": c.id, "memory_summary": c.memory_summary or "",
            "da_tom_tat": bool(tom_tat),
            "thong_bao": "Đã tóm tắt lại hồ sơ khách." if tom_tat else "Chưa tóm tắt được (khách chưa có tin nhắn nào hoặc nhà cung cấp AI đang lỗi)."}

# ---- Thông tin thu thập (GĐ mở rộng 1) ----
def tt_out(t): return {"id": t.id, "customer_id": t.customer_id, "field": t.field, "value": t.value,
                        "source_message_id": t.source_message_id, "confidence": t.confidence,
                        "verified": bool(t.verified),
                        "created_at": str(t.created_at) if t.created_at else "",
                        "updated_at": str(t.updated_at) if t.updated_at else ""}

def _khach_hoac_404(db: Session, cid: int):
    c = db.get(Customer, cid)
    if not c: raise HTTPException(404, "Không tìm thấy khách hàng")
    return c

@router.get("/{cid}/thong-tin-thu-thap")
def ds_thu_thap(cid: int, trang: int = 0, kich_thuoc_trang: int = 20, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    _khach_hoac_404(db, cid)
    ds = [tt_out(t) for t in db.query(CollectedInfo).filter(CollectedInfo.customer_id == cid).order_by(CollectedInfo.id.desc()).all()]
    if co_phan_trang(trang):
        return trang_hoa(ds, trang, kich_thuoc_trang)
    return ds

@router.post("/{cid}/thong-tin-thu-thap")
def them_thu_thap(cid: int, data: CollectedInfoIn, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    _khach_hoac_404(db, cid)
    if data.field not in CAC_TRUONG: raise HTTPException(400, f"Trường không hợp lệ. Chỉ chấp nhận: {', '.join(CAC_TRUONG)}")
    if not data.value.strip(): raise HTTPException(400, "Giá trị không được để trống")
    t = CollectedInfo(customer_id=cid, field=data.field, value=data.value.strip(), source_message_id=None,
                      confidence=1.0, verified=data.verified)
    db.add(t); db.commit(); db.refresh(t); return tt_out(t)

@router.put("/{cid}/thong-tin-thu-thap/{tid}")
def sua_thu_thap(cid: int, tid: int, data: CollectedInfoUpdate, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    _khach_hoac_404(db, cid)
    t = db.get(CollectedInfo, tid)
    if not t or t.customer_id != cid: raise HTTPException(404, "Không tìm thấy thông tin thu thập")
    if data.value is not None:
        if not data.value.strip(): raise HTTPException(400, "Giá trị không được để trống")
        t.value = data.value.strip()
    if data.verified is not None: t.verified = data.verified
    db.commit(); db.refresh(t); return tt_out(t)

@router.delete("/{cid}/thong-tin-thu-thap/{tid}")
def xoa_thu_thap(cid: int, tid: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    _khach_hoac_404(db, cid)
    t = db.get(CollectedInfo, tid)
    if not t or t.customer_id != cid: raise HTTPException(404, "Không tìm thấy thông tin thu thập")
    db.delete(t); db.commit(); return {"da_xoa": True}
