"""Trích xuất thông tin khách hàng tự động từ nội dung tin nhắn (GĐ mở rộng 1).

Hai lớp trích xuất:
1) Quy tắc (chạy mọi lúc, không tốn chi phí AI): số điện thoại Việt Nam và
   email — dữ liệu có mẫu rõ ràng, độ tin cậy cao (0.95).
2) AI có cấu trúc (chỉ khi nhà cung cấp mặc định KHÔNG phải Mock): gọi
   chat/completions với yêu cầu trả JSON thuần theo schema cố định, parse
   an toàn — lỗi/bịa định dạng thì bỏ qua, không bao giờ làm sập pipeline.

Mọi giá trị trích xuất được đều lưu thành bản ghi CollectedInfo (có vết,
có nguồn tin nhắn). Hồ sơ Customer chỉ được cập nhật vào các trường CÒN
TRỐNG; trùng lặp y hệt liên tiếp (cùng khách + trường + giá trị với bản
ghi gần nhất của trường đó) thì không lưu thêm.
"""
import json
import re
from sqlalchemy.orm import Session
from ..models import CollectedInfo, Customer, Message, AIUsage
from ..security import decrypt_secret
from . import ai_gateway

CAC_TRUONG = [
    "ho_ten", "so_dien_thoai", "email", "nhu_cau", "dich_vu_quan_tam",
    "ngan_sach", "thoi_gian_mong_muon", "dia_chi", "ghi_chu",
]
TRUONG_AI = ["ho_ten", "nhu_cau", "dich_vu_quan_tam", "ngan_sach", "thoi_gian_mong_muon", "dia_chi"]

# SĐT di động VN: bắt đầu 03/05/07/08/09, 10 chữ số; chấp nhận dạng quốc tế
# +84 và các dấu phân cách khoảng trắng / chấm / gạch ngang giữa các nhóm.
_SDT_UNG_VIEN = re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s.\-]?\d){9}(?!\d)")
_SDT_HOP_LE = re.compile(r"^0[35789]\d{8}$")
_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def chuan_hoa_sdt(tho: str) -> str:
    """Đưa SĐT về dạng 0xxxxxxxxx; trả '' nếu không phải SĐT di động VN hợp lệ."""
    so = re.sub(r"\D", "", tho or "")
    if so.startswith("84") and len(so) == 11:
        so = "0" + so[2:]
    return so if _SDT_HOP_LE.match(so) else ""


def trich_xuat_quy_tac(content: str) -> dict:
    """Trích xuất bằng quy tắc: SĐT + email. Trả {field: value} đã chuẩn hóa."""
    ket_qua = {}
    if not content:
        return ket_qua
    for ung_vien in _SDT_UNG_VIEN.findall(content):
        sdt = chuan_hoa_sdt(ung_vien)
        if sdt:
            ket_qua["so_dien_thoai"] = sdt
            break
    m = _EMAIL.search(content)
    if m:
        ket_qua["email"] = m.group(0).lower()
    return ket_qua


def _loc_json_ai(data) -> dict:
    """Lọc JSON của AI về đúng schema: chỉ các trường cho phép, chuỗi ngắn, không rỗng."""
    if not isinstance(data, dict):
        return {}
    sach = {}
    for truong in TRUONG_AI:
        gia_tri = data.get(truong)
        if isinstance(gia_tri, str):
            gia_tri = gia_tri.strip()[:500]
            if gia_tri:
                sach[truong] = gia_tri
    return sach


def _goi_ai_json(db: Session, provider, content: str) -> dict:
    """Gọi provider thật yêu cầu JSON cấu trúc. Mọi lỗi đều trả {} (không ném)."""
    try:
        key = decrypt_secret(provider.api_key_encrypted)
        if not key or not provider.base_url:
            return {}
        prompt_he_thong = (
            "Bạn là bộ trích xuất thông tin khách hàng. Chỉ trả về MỘT đối tượng JSON thuần, "
            "không giải thích, không markdown. Các khóa được phép: "
            + ", ".join(TRUONG_AI)
            + ". Chỉ điền khóa có thông tin rõ ràng trong tin nhắn; thiếu thì bỏ qua khóa đó. "
            "ho_ten chỉ điền khi khách tự nêu tên của mình."
        )
        with ai_gateway.http_client(timeout=provider.timeout or 30) as client:
            r = client.post(
                f"{provider.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": provider.model, "stream": False,
                      "messages": [{"role": "system", "content": prompt_he_thong},
                                   {"role": "user", "content": content}]},
            )
            if r.status_code >= 400:
                return {}
            parsed = ai_gateway.parse_chat_response(r.text, r.headers.get("content-type", "") if hasattr(r, "headers") else "")
        van_ban = (parsed.get("content") or "").strip()
        usage = parsed.get("usage") or {}
        db.add(AIUsage(provider_id=provider.id, model=parsed.get("model") or provider.model,
                       prompt_tokens=usage.get("prompt_tokens", 0) or 0,
                       completion_tokens=usage.get("completion_tokens", 0) or 0,
                       status="thanh_cong"))
        db.commit()
        bat_dau, ket_thuc = van_ban.find("{"), van_ban.rfind("}")
        if bat_dau < 0 or ket_thuc <= bat_dau:
            return {}
        return _loc_json_ai(json.loads(van_ban[bat_dau:ket_thuc + 1]))
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return {}


def trich_xuat_ai(db: Session, content: str) -> dict:
    """Trích xuất bằng AI khi provider mặc định là provider thật; Mock -> {}."""
    try:
        provider = ai_gateway.get_default_provider(db)
        if not provider or provider.provider == "mock":
            return {}
        return _goi_ai_json(db, provider, content)
    except Exception:
        return {}


def _la_trung_lien_tiep(db: Session, customer_id: int, field: str, value: str) -> bool:
    """Bản ghi gần nhất của (khách, trường) có cùng giá trị -> coi là trùng liên tiếp."""
    gan_nhat = (
        db.query(CollectedInfo)
        .filter(CollectedInfo.customer_id == customer_id, CollectedInfo.field == field)
        .order_by(CollectedInfo.id.desc())
        .first()
    )
    return bool(gan_nhat and (gan_nhat.value or "") == value)


def _co_truong(db: Session, customer: Customer, truong: str) -> bool:
    if truong == "so_dien_thoai":
        return bool((customer.phone or "").strip()) or (
            db.query(CollectedInfo)
            .filter(CollectedInfo.customer_id == customer.id, CollectedInfo.field == "so_dien_thoai")
            .first() is not None)
    if truong == "email":
        return bool((customer.email or "").strip()) or (
            db.query(CollectedInfo)
            .filter(CollectedInfo.customer_id == customer.id, CollectedInfo.field == "email")
            .first() is not None)
    if truong == "ho_ten":
        return bool((customer.display_name or "").strip()) or (
            db.query(CollectedInfo)
            .filter(CollectedInfo.customer_id == customer.id, CollectedInfo.field == "ho_ten")
            .first() is not None)
    return (
        db.query(CollectedInfo)
        .filter(CollectedInfo.customer_id == customer.id, CollectedInfo.field == truong)
        .first() is not None)


def kiem_tra_du_thong_tin(db: Session, customer: Customer) -> bool:
    """Đủ thông tin = có đủ các trường bắt buộc trong Cài đặt
    (cac_truong_bat_buoc_thu_thap, mặc định "so_dien_thoai,nhu_cau").

    Tương thích ngược: nếu Cài đặt không đọc được thì dùng bộ tối thiểu cũ —
    có SĐT và có nhu cầu hoặc dịch vụ quan tâm.
    """
    bat_buoc = None
    try:
        from ..routers.cai_dat import doc_cai_dat
        tho = str(doc_cai_dat(db).get("cac_truong_bat_buoc_thu_thap") or "")
        bat_buoc = [t.strip() for t in tho.split(",") if t.strip() in CAC_TRUONG]
    except Exception:
        bat_buoc = None
    if not bat_buoc:
        return _co_truong(db, customer, "so_dien_thoai") and (
            _co_truong(db, customer, "nhu_cau") or _co_truong(db, customer, "dich_vu_quan_tam"))
    return all(_co_truong(db, customer, t) for t in bat_buoc)


def extract_and_save(db: Session, customer: Customer, message: Message) -> dict:
    """Chạy trích xuất cho 1 tin nhắn khách, lưu CollectedInfo + cập nhật
    các trường hồ sơ còn trống. Trả về dict tóm tắt:
    {da_luu: {field: value}, sdt_moi: bool, du_thong_tin_moi: bool}."""
    content = message.content or ""
    ket_qua = trich_xuat_quy_tac(content)
    do_tin_cay = {f: 0.95 for f in ket_qua}
    for truong, gia_tri in trich_xuat_ai(db, content).items():
        if truong not in ket_qua and gia_tri:
            ket_qua[truong] = gia_tri
            do_tin_cay[truong] = 0.7

    sdt_truoc = bool((customer.phone or "").strip())
    du_truoc = kiem_tra_du_thong_tin(db, customer)

    da_luu = {}
    for truong, gia_tri in ket_qua.items():
        if _la_trung_lien_tiep(db, customer.id, truong, gia_tri):
            continue
        db.add(CollectedInfo(
            customer_id=customer.id, field=truong, value=gia_tri,
            source_message_id=message.id, confidence=do_tin_cay.get(truong, 0.7),
            verified=False,
        ))
        da_luu[truong] = gia_tri

    # Chỉ điền vào trường hồ sơ đang trống — không ghi đè dữ liệu đã có.
    if "so_dien_thoai" in ket_qua and not (customer.phone or "").strip():
        customer.phone = ket_qua["so_dien_thoai"]
    if "email" in ket_qua and not (customer.email or "").strip():
        customer.email = ket_qua["email"]
    if "ho_ten" in ket_qua and not (customer.display_name or "").strip():
        customer.display_name = ket_qua["ho_ten"]
    db.commit()

    return {
        "da_luu": da_luu,
        "sdt_moi": (not sdt_truoc) and bool((customer.phone or "").strip()),
        "du_thong_tin_moi": (not du_truoc) and kiem_tra_du_thong_tin(db, customer),
    }
