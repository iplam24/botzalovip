"""Chuẩn hoá văn bản AI trước khi gửi Zalo + chia nhỏ tin nhắn (Đợt nâng cấp 2).

Mục 6 — Zalo không render Markdown nên mọi câu trả lời phải qua
`dinh_dang_tin_zalo()` trước khi GỬI và trước khi LƯU hiển thị:
- Tiêu đề #, ##, ### -> bỏ ký tự #, viết hoa chữ đầu, giữ thành dòng riêng.
- **đậm** / __đậm__ -> bỏ ký tự bao, giữ nội dung (Zalo cá nhân qua API này
  không có bold thật — không chèn ký tự lạ thay thế).
- *nghiêng* / _nghiêng_ / ~~gạch ngang~~ -> bỏ ký tự bao.
- Gạch đầu dòng -, *, + -> "• "; danh sách số giữ nguyên.
- Bảng Markdown -> danh sách dòng "Tên cột: giá trị".
- Link [chữ](url) -> "chữ (url)"; code block/inline -> bỏ backtick.
- Đợt E: cắt token "[sticker]" lọt vào văn bản AI (AI bắt chước marker từ
  lịch sử cũ). Sticker THẬT của bot là Message riêng (attachment_type=
  "sticker", tạo trực tiếp ở orchestrator._gui_sticker_neu_may) — không đi
  qua hàm này nên không bị ảnh hưởng.

Mục 5 — `chia_tin_nhan()`: tách câu trả lời dài thành nhiều tin liên tiếp
theo đoạn (xuống dòng) -> câu -> cắt cứng theo ranh giới từ, giữ thứ tự,
không phần nào vượt độ dài tối đa.
"""
import re

_BANG_TACH = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")          # dòng |---|---|
_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
_DAM = re.compile(r"\*\*(.+?)\*\*", re.S)
_DAM_GACH = re.compile(r"__(.+?)__", re.S)
_NGHIENG_SAO = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", re.S)
_NGHIENG_GACH = re.compile(r"(?<![\w])_(.+?)_(?![\w])", re.S)
_GACH_NGANG = re.compile(r"~~(.+?)~~", re.S)
_CODE_NGANG = re.compile(r"`([^`]*)`")
_TIEU_DE = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$")
_DAU_DONG = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_DANH_SACH_SO = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
_KET_CAU = re.compile(r"(?<=[.!?…])\s+")
_TOKEN_STICKER = re.compile(r"\[\s*sticker\s*\]", re.I)


def _sach_trong_dong(s: str) -> str:
    """Bỏ định dạng inline kiểu Markdown trong một đoạn văn bản."""
    s = _LINK.sub(lambda m: f"{m.group(1)} ({m.group(2)})" if m.group(1) else m.group(2), s)
    s = _DAM.sub(r"\1", s)
    s = _DAM_GACH.sub(r"\1", s)
    s = _GACH_NGANG.sub(r"\1", s)
    s = _NGHIENG_SAO.sub(r"\1", s)
    s = _NGHIENG_GACH.sub(r"\1", s)
    s = _CODE_NGANG.sub(r"\1", s)
    return s


def _la_dong_bang(dong: str) -> bool:
    return dong.lstrip().startswith("|") and dong.count("|") >= 2


def _o_bang(dong: str):
    return [c.strip() for c in dong.strip().strip("|").split("|")]


def dinh_dang_tin_zalo(text: str) -> str:
    """Chuẩn hoá Markdown -> văn bản thuần hiển thị đẹp trên Zalo."""
    if not text:
        return ""
    # Code block: bỏ hàng rào ``` (giữ nội dung)
    text = re.sub(r"```[a-zA-Z0-9_-]*\n?", "", str(text)).replace("```", "")
    # Đợt E: cắt marker "[sticker]" lọt vào văn bản AI trước khi xử lý dòng:
    # dòng CHỈ chứa token -> bỏ cả dòng; token ở cuối/giữa câu -> xoá token
    # rồi dọn khoảng trắng thừa do việc xoá để lại.
    dong_loc: list[str] = []
    for dong_goc in text.replace("\r\n", "\n").split("\n"):
        if _TOKEN_STICKER.fullmatch(dong_goc.strip()):
            continue
        if _TOKEN_STICKER.search(dong_goc):
            dong_goc = re.sub(r"[ \t]{2,}", " ", _TOKEN_STICKER.sub("", dong_goc))
        dong_loc.append(dong_goc)
    text = "\n".join(dong_loc)
    dong_tho = text.replace("\r\n", "\n").split("\n")
    ket_qua: list[str] = []
    i = 0
    while i < len(dong_tho):
        dong = dong_tho[i]
        # --- Bảng Markdown: header + dòng tách + các dòng dữ liệu ---
        if _la_dong_bang(dong) and i + 1 < len(dong_tho) and _BANG_TACH.match(dong_tho[i + 1]) and "-" in dong_tho[i + 1]:
            tieu_de = _o_bang(dong)
            i += 2
            while i < len(dong_tho) and _la_dong_bang(dong_tho[i]):
                o = _o_bang(dong_tho[i])
                cap = [f"{tieu_de[j]}: {_sach_trong_dong(o[j])}" for j in range(min(len(tieu_de), len(o))) if o[j]]
                if cap:
                    ket_qua.append("• " + "; ".join(cap))
                i += 1
            continue
        m_td = _TIEU_DE.match(dong)
        if m_td:
            noi_dung = _sach_trong_dong(m_td.group(1)).strip()
            if noi_dung:
                noi_dung = noi_dung[0].upper() + noi_dung[1:]
                ket_qua.append(noi_dung)
            i += 1
            continue
        m_dd = _DAU_DONG.match(dong)
        if m_dd:
            ket_qua.append("• " + _sach_trong_dong(m_dd.group(2)).strip())
            i += 1
            continue
        m_so = _DANH_SACH_SO.match(dong)
        if m_so:
            ket_qua.append(f"{m_so.group(2)}. {_sach_trong_dong(m_so.group(3)).strip()}")
            i += 1
            continue
        ket_qua.append(_sach_trong_dong(dong).rstrip())
        i += 1
    sach = "\n".join(ket_qua)
    sach = re.sub(r"\n{3,}", "\n\n", sach)
    return sach.strip()


def _cat_cung(doan: str, toi_da: int) -> list[str]:
    """Cắt một đoạn quá dài theo ranh giới từ, không vượt toi_da ký tự."""
    phan = []
    con_lai = doan.strip()
    while len(con_lai) > toi_da:
        cat = con_lai.rfind(" ", 0, toi_da)
        if cat < toi_da // 2:
            cat = toi_da
        phan.append(con_lai[:cat].strip())
        con_lai = con_lai[cat:].strip()
    if con_lai:
        phan.append(con_lai)
    return phan


def _tach_cau(doan: str) -> list[str]:
    return [c for c in _KET_CAU.split(doan.strip()) if c and c.strip()]


def chia_tin_nhan(text: str, do_dai_toi_da: int = 350) -> list[str]:
    """Chia câu trả lời dài thành nhiều tin: ưu tiên đoạn -> câu -> cắt cứng.

    Giữ nguyên thứ tự; phần tử rỗng bị loại; không phần nào dài quá giới hạn
    (trừ khi một 'từ' duy nhất dài hơn giới hạn — lúc đó cắt cứng theo ký tự).
    """
    if not text:
        return []
    toi_da = max(20, int(do_dai_toi_da or 350))
    text = str(text).strip()
    if len(text) <= toi_da:
        return [text]
    # Đơn vị nhỏ: (nội dung, co_xuong_dong_truoc) — đoạn gốc giữ xuống dòng,
    # câu trong cùng đoạn nối bằng khoảng trắng.
    don_vi: list[tuple[str, bool]] = []
    for doan in re.split(r"\n+", text):
        doan = doan.strip()
        if not doan:
            continue
        if len(doan) <= toi_da:
            don_vi.append((doan, True))
        else:
            for vi_tri, cau in enumerate(_tach_cau(doan)):
                if len(cau) <= toi_da:
                    don_vi.append((cau, vi_tri == 0))
                else:
                    for j, manh in enumerate(_cat_cung(cau, toi_da)):
                        don_vi.append((manh, vi_tri == 0 and j == 0))
    phan_hoan_chinh: list[str] = []
    hien_tai = ""
    for noi_dung, xuong_dong in don_vi:
        if not hien_tai:
            hien_tai = noi_dung
            continue
        dau_noi = "\n" if xuong_dong else " "
        if len(hien_tai) + len(dau_noi) + len(noi_dung) <= toi_da:
            hien_tai = hien_tai + dau_noi + noi_dung
        else:
            phan_hoan_chinh.append(hien_tai)
            hien_tai = noi_dung
    if hien_tai:
        phan_hoan_chinh.append(hien_tai)
    return [p for p in (x.strip() for x in phan_hoan_chinh) if p]
