"""Phân trang phía máy chủ cho các danh sách dài (Đợt nâng cấp 3, mục 1).

Chuẩn chung cho mọi endpoint danh sách:
- Tham số: `trang` (bắt đầu từ 1) + `kich_thuoc_trang` (10/20/50/100, mặc định 20).
- Khi CÓ truyền `trang` (>= 1): trả về dict
  {"muc": [...], "tong": n, "trang": t, "tong_trang": tt, "kich_thuoc_trang": k}.
- Khi KHÔNG truyền `trang`: giữ nguyên hành vi cũ (trả list thuần) để không phá
  vỡ các nơi đang dùng (frontend cũ, kiểm thử cũ, tích hợp ngoài).

Trang vượt quá tổng số trang được kẹp về trang cuối (tối thiểu 1) để giao diện
không bao giờ rơi vào trang trống khó hiểu khi dữ liệu vừa bị xóa/lọc bớt.
"""

KICH_THUOC_CHO_PHEP = (10, 20, 50, 100)
KICH_THUOC_MAC_DINH = 20


def chuan_hoa_kich_thuoc(kich_thuoc_trang) -> int:
    try:
        k = int(kich_thuoc_trang)
    except (TypeError, ValueError):
        return KICH_THUOC_MAC_DINH
    return k if k in KICH_THUOC_CHO_PHEP else KICH_THUOC_MAC_DINH


def trang_hoa(danh_sach: list, trang, kich_thuoc_trang=KICH_THUOC_MAC_DINH) -> dict:
    """Cắt một danh sách ĐÃ lọc + sắp xếp thành một trang theo chuẩn trên."""
    k = chuan_hoa_kich_thuoc(kich_thuoc_trang)
    tong = len(danh_sach)
    tong_trang = max(1, (tong + k - 1) // k)
    try:
        t = int(trang)
    except (TypeError, ValueError):
        t = 1
    t = min(max(1, t), tong_trang)
    bat_dau = (t - 1) * k
    return {
        "muc": danh_sach[bat_dau:bat_dau + k],
        "tong": tong,
        "trang": t,
        "tong_trang": tong_trang,
        "kich_thuoc_trang": k,
    }


def co_phan_trang(trang) -> bool:
    """Endpoint chỉ chuyển sang dạng phân trang khi client truyền trang >= 1."""
    try:
        return int(trang) >= 1
    except (TypeError, ValueError):
        return False
