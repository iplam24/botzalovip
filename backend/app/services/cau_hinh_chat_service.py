"""Trợ lý cấu hình qua đoạn chat (Đợt nâng cấp 3, mục 2).

Quản trị viên gõ lệnh tự nhiên ("bật chế độ trò chuyện tự do", "đặt nhiệt độ
AI thành 0.7", "đổi giọng bot sang ngắn gọn") — hệ thống phân tích thành danh
sách thay đổi cài đặt để quản trị viên DUYỆT trước; chỉ khi bấm Áp dụng mới
ghi thật (qua cùng cổng kiểm tra registry như PUT /api/cai-dat) và ghi nhật
ký module "cau_hinh_qua_chat".

Hai đường phân tích:
- Provider thật (mặc định, không phải Mock): gọi AI với danh sách khóa rút gọn
  của registry, yêu cầu trả JSON thuần; MỌI khóa/giá trị đều được kiểm tra lại
  bằng registry ở server — model bịa khóa -> bị loại bỏ.
- Provider Mock: bộ phân tích quy tắc tối thiểu (bật/tắt <tên gần đúng>,
  đặt <khóa> thành/= <giá trị>) để bản mô phỏng + kiểm thử vẫn dùng được.
"""
import json
import re
from fastapi import HTTPException
from sqlalchemy.orm import Session
from ..models import SystemLog
from ..routers.cai_dat import DANG_KY_CAI_DAT, _THEO_KHOA, _kiem_tra_gia_tri, ap_dung_thay_doi, doc_cai_dat
from . import ai_gateway
from .text_utils import normalize_vi

LENH_MAU = [
    "Bật chế độ trò chuyện tự do",
    "Tắt thả tim",
    "Đặt nhiệt độ AI thành 0.7",
    "Đổi giọng bot sang ngắn gọn",
    "Bật bot chủ động giới thiệu dịch vụ",
    "Tắt tìm kiếm ngữ nghĩa",
]

# Bí danh thường gặp (đã bỏ dấu) -> khóa cài đặt, phục vụ bộ phân tích quy tắc
_BI_DANH = [
    ("che do tro chuyen tu do", "che_do_tro_chuyen_tu_do"),
    ("tro chuyen tu do", "che_do_tro_chuyen_tu_do"),
    ("che do tu do", "che_do_tro_chuyen_tu_do"),
    ("nhiet do tu do", "nhiet_do_tu_do"),
    ("nhiet do ai", "ai_temperature"),
    ("nhiet do", "ai_temperature"),
    ("giong dieu", "bot_giong_dieu"),
    ("giong bot", "bot_giong_dieu"),
    ("do dai tra loi", "ai_do_dai_tra_loi"),
    ("tra loi ngoai gio", "cau_tra_loi_ngoai_gio"),
    ("chu dong pr", "bot_chu_dong_pr"),
    ("gioi thieu dich vu", "bot_chu_dong_pr"),
    ("gui tin chia nho", "gui_tin_chia_nho"),
    ("chia nho tin", "gui_tin_chia_nho"),
    ("tha tim", "bot_tha_tim"),
    ("hoi so dien thoai", "thu_thap_tu_hoi_sdt"),
    ("hoi sdt", "thu_thap_tu_hoi_sdt"),
    ("tu dong tra loi", "tu_dong_tra_loi_toan_cuc"),
    ("duyet truoc khi gui", "che_do_duyet_truoc_khi_gui"),
    ("tim kiem ngu nghia", "tim_kiem_ngu_nghia"),
    ("tim ngu nghia", "tim_kiem_ngu_nghia"),
]


def _danh_sach_khoa_rut_gon() -> list:
    """Danh sách khóa gửi cho AI: chỉ các trường cần để map lệnh -> thay đổi."""
    ds = []
    for d in DANG_KY_CAI_DAT:
        muc = {"khoa": d["khoa"], "nhan": d["nhan"], "kieu": d["kieu"]}
        if d["kieu"] == "select":
            muc["lua_chon"] = d.get("lua_chon", [])
            if d.get("nhan_lua_chon"):
                muc["nhan_lua_chon"] = d["nhan_lua_chon"]
        if d["kieu"] in ("so", "gio"):
            if "min" in d:
                muc["min"] = d["min"]
            if "max" in d:
                muc["max"] = d["max"]
        ds.append(muc)
    return ds


def _loc_thay_doi_hop_le(db: Session, tho: list) -> list:
    """Lọc + ép kiểu danh sách thay đổi thô [{khoa, gia_tri}] bằng registry.

    Khóa không có trong registry (AI bịa) hoặc giá trị sai kiểu/ràng buộc đều
    bị LOẠI BỎ. Trả về các mục kèm nhãn + giá trị cũ/mới để hiển thị thẻ
    xác nhận cho quản trị viên duyệt."""
    hien_tai = doc_cai_dat(db)
    theo_khoa = {}
    for muc in tho or []:
        if not isinstance(muc, dict):
            continue
        khoa = muc.get("khoa")
        if khoa not in _THEO_KHOA:
            continue
        gia_tri = muc.get("gia_tri", muc.get("gia_tri_moi"))
        try:
            gia_tri = _kiem_tra_gia_tri(_THEO_KHOA[khoa], gia_tri)
        except HTTPException:
            continue
        theo_khoa[khoa] = {
            "khoa": khoa,
            "nhan": _THEO_KHOA[khoa]["nhan"],
            "kieu": _THEO_KHOA[khoa]["kieu"],
            "gia_tri_cu": hien_tai.get(khoa, _THEO_KHOA[khoa]["mac_dinh"]),
            "gia_tri_moi": gia_tri,
        }
    return list(theo_khoa.values())


# ---- Đường AI (provider thật) ----

def _phan_tich_bang_ai(db: Session, provider, cau_lenh: str) -> list:
    """Gọi provider mặc định để map câu lệnh -> [{khoa, gia_tri}] (JSON thuần).

    Kết quả ở đây CHƯA tin được: hàm gọi sẽ lọc lại bằng registry."""
    from ..security import decrypt_secret
    key = decrypt_secret(provider.api_key_encrypted)
    if not key or not provider.base_url:
        raise ai_gateway.AIError("Nhà cung cấp AI mặc định chưa có khóa API/địa chỉ API")
    huong_dan = (
        "Bạn là bộ phân tích lệnh cấu hình hệ thống. Dưới đây là danh sách khóa cài đặt hợp lệ (JSON):\n"
        + json.dumps(_danh_sach_khoa_rut_gon(), ensure_ascii=False)
        + "\n\nCâu lệnh của quản trị viên: " + json.dumps(cau_lenh, ensure_ascii=False)
        + "\n\nHãy trích xuất các thay đổi thành một JSON array: "
          "[{\"khoa\": \"<một khóa trong danh sách>\", \"gia_tri\": <giá trị đúng kiểu>}]. "
          "bool -> true/false; so -> số; gio -> số giờ 0-24; select -> đúng một giá trị trong lua_chon; "
          "text/textarea/mau -> chuỗi. Chỉ dùng khóa có trong danh sách. "
          "Không trích xuất được thay đổi nào thì trả về []. "
          "CHỈ trả về đúng JSON array, không giải thích, không bọc trong markdown."
    )
    payload = {"model": provider.model, "stream": False, "temperature": 0,
               "messages": [{"role": "user", "content": huong_dan}]}
    with ai_gateway.http_client(timeout=provider.timeout or 30) as client:
        r = client.post(f"{provider.base_url.rstrip('/')}/chat/completions",
                        headers={"Authorization": f"Bearer {key}"}, json=payload)
        if r.status_code >= 400:
            raise ai_gateway.AIError(f"Provider trả lỗi {r.status_code} khi phân tích lệnh cấu hình")
        parsed = ai_gateway.parse_chat_response(r.text, r.headers.get("content-type", ""))
    text = (parsed.get("content") or "").strip()
    bat_dau, ket_thuc = text.find("["), text.rfind("]")
    if bat_dau < 0 or ket_thuc <= bat_dau:
        return []
    try:
        du_lieu = json.loads(text[bat_dau:ket_thuc + 1])
    except Exception:
        return []
    return du_lieu if isinstance(du_lieu, list) else []


# ---- Đường quy tắc (provider Mock) ----

def _tim_khoa(doan_chuan: str, chi_bool: bool = False):
    """Tìm khóa cài đặt gần đúng nhất với một đoạn chữ (đã bỏ dấu)."""
    for cum, khoa in _BI_DANH:
        if cum in doan_chuan and (not chi_bool or _THEO_KHOA[khoa]["kieu"] == "bool"):
            return khoa
    ung_vien = []
    for d in DANG_KY_CAI_DAT:
        if chi_bool and d["kieu"] != "bool":
            continue
        for mau in (d["khoa"].replace("_", " "), normalize_vi(d["nhan"])):
            if len(mau) >= 4 and (mau in doan_chuan or doan_chuan in mau):
                ung_vien.append((len(mau), d["khoa"]))
    if ung_vien:
        ung_vien.sort(reverse=True)
        return ung_vien[0][1]
    return None


def _gia_tri_theo_kieu(dinh_nghia: dict, doan_gia_tri: str, gia_tri_goc: str):
    """Ép một đoạn chữ thành giá trị theo kiểu của khóa (None nếu không ép được)."""
    kieu = dinh_nghia["kieu"]
    n = normalize_vi(doan_gia_tri)
    if kieu == "bool":
        if n in ("bat", "on", "true", "1", "co", "kich hoat", "mo"):
            return True
        if n in ("tat", "off", "false", "0", "khong", "vo hieu hoa", "dong"):
            return False
        return None
    if kieu in ("so", "gio"):
        m = re.search(r"[-+]?\d+(?:[.,]\d+)?", doan_gia_tri)
        return float(m.group(0).replace(",", ".")) if m else None
    if kieu == "select":
        nhan_lc = dinh_nghia.get("nhan_lua_chon", {})
        for lua_chon in dinh_nghia.get("lua_chon", []):
            for mau in (normalize_vi(nhan_lc.get(lua_chon, "")), normalize_vi(lua_chon.replace("_", " "))):
                if mau and (mau in n or n in mau):
                    return lua_chon
        return None
    # text / textarea / mau: lấy nguyên văn phần giá trị từ câu lệnh gốc
    return gia_tri_goc.strip() or None


def _phan_tich_quy_tac(cau_lenh: str) -> list:
    n = normalize_vi(cau_lenh)
    tho = []
    # Mẫu 1: bật/tắt <tên gần đúng của một cài đặt đúng/sai>
    m = re.match(r"^(?:hay\s+|xin\s+)*(bat|tat|mo|dong)\s+(.+)$", n)
    if m:
        khoa = _tim_khoa(m.group(2).strip(), chi_bool=True)
        if khoa:
            tho.append({"khoa": khoa, "gia_tri": m.group(1) in ("bat", "mo")})
        return tho
    # Mẫu 2: đặt/đổi <khóa> thành|sang|= <giá trị>
    m = re.match(r"^(?:dat|doi|chuyen|thiet lap)\s+(.+?)\s+(?:thanh|sang|=)\s+(.+)$", n)
    if m:
        khoa = _tim_khoa(m.group(1).strip())
        if khoa:
            dinh_nghia = _THEO_KHOA[khoa]
            # Giá trị gốc (giữ dấu tiếng Việt) cho khóa dạng chữ: lấy phần sau
            # từ khóa nối cuối cùng trong câu lệnh gốc.
            gia_tri_goc = re.split(r"(?i)(?:thành|sang|=)\s*", cau_lenh)[-1]
            gia_tri = _gia_tri_theo_kieu(dinh_nghia, m.group(2), gia_tri_goc)
            if gia_tri is not None:
                tho.append({"khoa": khoa, "gia_tri": gia_tri})
        return tho
    return tho


# ---- API của service ----

def phan_tich(db: Session, cau_lenh: str) -> dict:
    """Phân tích câu lệnh -> danh sách thay đổi CHỜ DUYỆT (chưa áp dụng gì)."""
    cau_lenh = (cau_lenh or "").strip()
    if not cau_lenh:
        return {"thay_doi": [], "loi_nhan": "Hãy nhập một câu lệnh cấu hình.", "goi_y": LENH_MAU, "nguon": "quy_tac"}
    provider = ai_gateway.get_default_provider(db)
    nguon = "quy_tac"
    if provider and provider.provider != "mock":
        nguon = "ai"
        try:
            tho = _phan_tich_bang_ai(db, provider, cau_lenh)
        except Exception as e:
            return {"thay_doi": [],
                    "loi_nhan": f"Không gọi được nhà cung cấp AI để phân tích lệnh ({e}). Chưa có thay đổi nào được tạo.",
                    "goi_y": LENH_MAU, "nguon": nguon}
    else:
        tho = _phan_tich_quy_tac(cau_lenh)
    thay_doi = _loc_thay_doi_hop_le(db, tho)
    if not thay_doi:
        return {"thay_doi": [],
                "loi_nhan": "Chưa hiểu được lệnh này hoặc lệnh nhắc tới cài đặt không tồn tại. Hãy thử một trong các lệnh mẫu dưới đây — hệ thống chỉ thay đổi các khóa có thật trong Trung tâm cấu hình.",
                "goi_y": LENH_MAU, "nguon": nguon}
    return {"thay_doi": thay_doi,
            "loi_nhan": f"Đã hiểu lệnh thành {len(thay_doi)} thay đổi. Kiểm tra thẻ xác nhận rồi bấm Áp dụng — chưa bấm là chưa đổi gì.",
            "goi_y": [], "nguon": nguon}


def _tom_tat_gia_tri(gia_tri) -> str:
    s = gia_tri if isinstance(gia_tri, str) else json.dumps(gia_tri, ensure_ascii=False)
    return s if len(s) <= 120 else s[:117] + "..."


def ap_dung(db: Session, user, thay_doi: list) -> dict:
    """Áp dụng danh sách thay đổi ĐÃ ĐƯỢC DUYỆT. Kiểm tra lại toàn bộ bằng
    registry (có khóa lạ -> 400, không áp dụng một phần), ghi nhật ký."""
    if not thay_doi:
        raise HTTPException(400, "Chưa có thay đổi nào để áp dụng")
    hien_tai = doc_cai_dat(db)
    tap = {}
    for muc in thay_doi:
        if not isinstance(muc, dict):
            continue
        khoa = muc.get("khoa")
        if khoa not in _THEO_KHOA:
            raise HTTPException(400, f"Khóa cài đặt không tồn tại: {khoa}")
        tap[khoa] = muc.get("gia_tri", muc.get("gia_tri_moi"))
    if not tap:
        raise HTTPException(400, "Chưa có thay đổi hợp lệ nào để áp dụng")
    # ap_dung_thay_doi kiểm tra kiểu/ràng buộc từng khóa rồi mới lưu + commit
    cai_dat_moi = ap_dung_thay_doi(db, tap)
    da_ap_dung = []
    for khoa, gia_tri_moi in tap.items():
        da_ap_dung.append({
            "khoa": khoa, "nhan": _THEO_KHOA[khoa]["nhan"],
            "gia_tri_cu": hien_tai.get(khoa, _THEO_KHOA[khoa]["mac_dinh"]),
            "gia_tri_moi": cai_dat_moi.get(khoa, gia_tri_moi),
        })
    mo_ta = "; ".join(
        f"{m['khoa']}: {_tom_tat_gia_tri(m['gia_tri_cu'])} -> {_tom_tat_gia_tri(m['gia_tri_moi'])}"
        for m in da_ap_dung)
    db.add(SystemLog(level="info", module="cau_hinh_qua_chat",
                     message=f"{user.username or user.email} (id={user.id}) cấu hình qua chat: {mo_ta}"))
    db.commit()
    return {"da_ap_dung": da_ap_dung, "cai_dat": cai_dat_moi}
