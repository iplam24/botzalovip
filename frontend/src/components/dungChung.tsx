import { ReactNode, useEffect } from "react";

// ---- Các thành phần giao diện dùng chung cho mọi phân hệ (tiếng Việt) ----

export function DangTai({ text = "Đang tải dữ liệu..." }: { text?: string }) {
  return (
    <div className="p-6 flex items-center gap-3 text-gray-600 dark:text-gray-300">
      <span className="inline-block w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
      {text}
    </div>
  );
}

export function LoiTai({ loi, onThuLai }: { loi: string; onThuLai?: () => void }) {
  return (
    <div className="p-6">
      <div className="bg-red-50 border border-red-300 text-red-700 p-4 rounded">
        <p className="font-semibold">Không tải được dữ liệu</p>
        <p className="text-sm mt-1">{loi}</p>
        {onThuLai && (
          <button onClick={onThuLai} className="mt-3 bg-white border border-red-400 text-red-700 px-3 py-1.5 rounded text-sm">
            Thử lại
          </button>
        )}
      </div>
    </div>
  );
}

export function ChuaCoDuLieu({ text, icon, huongDan }: { text: string; icon?: string; huongDan?: string }) {
  return (
    <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-the p-8 text-center text-gray-500">
      <p className="text-4xl mb-2 text-gray-300"><i className={icon || "fa-regular fa-folder-open"} /></p>
      <p>{text}</p>
      {huongDan && <p className="text-sm mt-2 text-gray-400">{huongDan}</p>}
    </div>
  );
}

// Phân trang phía máy chủ dùng chung (Đợt nâng cấp 3, mục 1): nút Trước/Sau,
// số trang rút gọn, chọn số mục mỗi trang (10/20/50/100) và dòng trạng thái
// "Hiển thị x–y / tổng z mục". Tự ẩn khi chỉ có tối đa 1 trang VÀ tổng số mục
// không vượt quá một trang (không có gì để phân trang).
export function PhanTrang({ trang, tongTrang, tong, kichThuoc, onDoiTrang, onDoiKichThuoc }: {
  trang: number; tongTrang: number; tong: number; kichThuoc: number;
  onDoiTrang: (trangMoi: number) => void; onDoiKichThuoc: (k: number) => void;
}) {
  if (tongTrang <= 1 && tong <= kichThuoc) return null;
  const tu = tong === 0 ? 0 : (trang - 1) * kichThuoc + 1;
  const den = Math.min(tong, trang * kichThuoc);
  const cacTrang: (number | "...")[] = [];
  for (let i = 1; i <= tongTrang; i++) {
    if (i === 1 || i === tongTrang || Math.abs(i - trang) <= 1) cacTrang.push(i);
    else if (cacTrang[cacTrang.length - 1] !== "...") cacTrang.push("...");
  }
  const nutTrang = "min-w-8 h-8 px-1.5 rounded text-sm border bg-white dark:bg-neutral-900 hover:bg-gray-50 dark:hover:bg-neutral-800 disabled:opacity-40";
  return (
    <div className="flex flex-wrap items-center gap-3 mt-4 text-sm">
      <span className="text-gray-500">Hiển thị {tu}–{den} / tổng {tong} mục</span>
      <span className="flex items-center gap-1.5 ml-auto">
        <button className={nutTrang} disabled={trang <= 1} onClick={() => onDoiTrang(trang - 1)} aria-label="Trang trước">
          <i className="fa-solid fa-chevron-left text-xs" />
        </button>
        {cacTrang.map((t, i) =>
          t === "..." ? (
            <span key={`c${i}`} className="px-1 text-gray-400">…</span>
          ) : (
            <button key={t} onClick={() => onDoiTrang(t)}
              className={`${nutTrang} ${t === trang ? "!bg-blue-600 !text-white !border-blue-600 font-semibold" : ""}`}>
              {t}
            </button>
          ),
        )}
        <button className={nutTrang} disabled={trang >= tongTrang} onClick={() => onDoiTrang(trang + 1)} aria-label="Trang sau">
          <i className="fa-solid fa-chevron-right text-xs" />
        </button>
      </span>
      <label className="flex items-center gap-1.5 text-gray-500">
        Mỗi trang
        <select value={kichThuoc} onChange={(e) => onDoiKichThuoc(Number(e.target.value))}
          className="border rounded px-2 py-1.5 text-sm bg-white dark:bg-neutral-800 dark:border-neutral-700">
          {[10, 20, 50, 100].map((k) => <option key={k} value={k}>{k} mục</option>)}
        </select>
      </label>
    </div>
  );
}

export function ThongBao({ loai, children }: { loai: "thanh_cong" | "loi" | "thong_tin"; children: ReactNode }) {
  const mau =
    loai === "thanh_cong"
      ? "bg-green-50 border-green-300 text-green-800"
      : loai === "loi"
        ? "bg-red-50 border-red-300 text-red-700"
        : "bg-blue-50 border-blue-300 text-blue-800";
  return <div className={`border p-3 rounded text-sm mb-4 ${mau}`}>{children}</div>;
}

export function TieuDeTrang({ tieuDe, moTa, children }: { tieuDe: string; moTa?: string; children?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 mb-5">
      <div>
        <h1 className="text-2xl font-bold">{tieuDe}</h1>
        {moTa && <p className="text-sm text-gray-500 mt-1">{moTa}</p>}
      </div>
      <div className="flex gap-2">{children}</div>
    </div>
  );
}

export function Nut({ children, onClick, mau = "xanh", disabled, type }: {
  children: ReactNode; onClick?: () => void; mau?: "xanh" | "trang" | "do" | "xam";
  disabled?: boolean; type?: "button" | "submit";
}) {
  const cls =
    mau === "xanh"
      ? "bg-blue-600 text-white hover:bg-blue-700"
      : mau === "do"
        ? "bg-white border border-red-500 text-red-600 hover:bg-red-50"
        : mau === "xam"
          ? "bg-gray-100 border text-gray-700 hover:bg-gray-200 dark:bg-neutral-800 dark:text-gray-200"
          : "bg-white border hover:bg-gray-50 dark:bg-neutral-900";
  return (
    <button type={type || "button"} onClick={onClick} disabled={disabled}
      className={`px-3.5 py-2 rounded text-sm font-medium disabled:opacity-50 ${cls}`}>
      {children}
    </button>
  );
}

export function Truong({ nhan, children, batBuoc }: { nhan: string; children: ReactNode; batBuoc?: boolean }) {
  return (
    <label className="block mb-3">
      <span className="block text-sm font-medium mb-1">
        {nhan} {batBuoc && <span className="text-red-500">*</span>}
      </span>
      {children}
    </label>
  );
}

export const oNhap =
  "w-full border rounded px-3 py-2 text-sm bg-white dark:bg-neutral-800 dark:border-neutral-700 focus:outline-none focus:ring-2 focus:ring-blue-400";

// Hộp thoại xác nhận dùng chung (xóa / khôi phục / thao tác nguy hiểm)
export function HopXacNhan({ mo, tieuDe, noiDung, nhanNut, dangXuLy, onDong, onXacNhan }: {
  mo: boolean; tieuDe: string; noiDung: string; nhanNut: string; dangXuLy?: boolean;
  onDong: () => void; onXacNhan: () => void;
}) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") onDong(); };
    if (mo) window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [mo, onDong]);
  if (!mo) return null;
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onDong}>
      <div className="bg-white dark:bg-neutral-900 rounded shadow-xl max-w-md w-full p-5" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-bold text-lg mb-2">{tieuDe}</h3>
        <p className="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-line">{noiDung}</p>
        <div className="flex justify-end gap-2 mt-5">
          <Nut mau="xam" onClick={onDong}>Hủy bỏ</Nut>
          <button onClick={onXacNhan} disabled={dangXuLy}
            className="px-3.5 py-2 rounded text-sm font-medium bg-red-600 text-white hover:bg-red-700 disabled:opacity-50">
            {dangXuLy ? "Đang xử lý..." : nhanNut}
          </button>
        </div>
      </div>
    </div>
  );
}

// Khung biểu mẫu dạng cửa sổ nổi (thêm/sửa)
export function HopBieuMau({ mo, tieuDe, onDong, children, rong = "max-w-lg" }: {
  mo: boolean; tieuDe: string; onDong: () => void; children: ReactNode; rong?: string;
}) {
  if (!mo) return null;
  // Cấu trúc: tiêu đề CỐ ĐỊNH trên cùng, thân cuộn được; hàng nút cuối của
  // form (Lưu/Hủy) được CSS .than-modal ghim dính ở đáy vùng cuộn — form dài
  // đến đâu nút Lưu vẫn luôn nhìn thấy (yêu cầu nút Lưu nổi bật, khó quên).
  return (
    <div className="fixed inset-0 bg-black/40 flex items-start justify-center z-50 p-4 overflow-y-auto" onClick={onDong}>
      <div className={`bg-white dark:bg-neutral-900 rounded shadow-xl w-full ${rong} my-8 max-h-[92vh] flex flex-col overflow-hidden`} onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-4 border-b flex-none">
          <h3 className="font-bold text-lg">{tieuDe}</h3>
          <button onClick={onDong} className="text-gray-500 hover:text-gray-800 text-xl leading-none" aria-label="Đóng">×</button>
        </div>
        <div className="px-5 pt-4 pb-5 overflow-y-auto than-modal">
          {children}
        </div>
      </div>
    </div>
  );
}

// Nút gạt bật/tắt dùng chung (toggle switch thuần CSS trong index.css)
export function NutGat({ bat, onDoi, disabled, nhan }: {
  bat: boolean; onDoi: (batMoi: boolean) => void; disabled?: boolean; nhan?: string;
}) {
  return (
    <span className="inline-flex items-center gap-2">
      <label className="nut-gat" title={nhan}>
        <input type="checkbox" checked={bat} disabled={disabled}
          onChange={(e) => onDoi(e.target.checked)} aria-label={nhan || "Bật/tắt"} />
        <span className="duong-ray" />
      </label>
      {nhan && <span className="text-sm">{nhan}</span>}
    </span>
  );
}

// Khung xương (skeleton) khi đang tải dữ liệu — thay spinner ở danh sách
export function SkeletonDanhSach({ soDong = 4 }: { soDong?: number }) {
  return (
    <div className="p-4 space-y-3" aria-label="Đang tải dữ liệu">
      {Array.from({ length: soDong }).map((_, i) => (
        <div key={i} className="flex items-center gap-3">
          <div className="skeleton w-10 h-10 !rounded-full" />
          <div className="flex-1 space-y-2">
            <div className="skeleton h-3.5 w-2/5" />
            <div className="skeleton h-3 w-4/5" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function HuyHieuTrangThai({ giaTri, bangMau }: { giaTri: string; bangMau?: Record<string, string> }) {
  const macDinh: Record<string, string> = {
    da_ket_noi: "bg-green-100 text-green-800", thanh_cong: "bg-green-100 text-green-800",
    da_giai_quyet: "bg-green-100 text-green-800", dang_xu_ly: "bg-blue-100 text-blue-800",
    cho_phan_hoi: "bg-amber-100 text-amber-800", loi: "bg-red-100 text-red-800",
    mat_ket_noi: "bg-red-100 text-red-800", chua_ho_tro: "bg-gray-200 text-gray-700",
    chua_cau_hinh: "bg-amber-100 text-amber-800", chua_kiem_tra: "bg-gray-200 text-gray-700",
    chua_ket_noi: "bg-gray-200 text-gray-700",
  };
  const nhan: Record<string, string> = {
    da_ket_noi: "Đã kết nối", thanh_cong: "Thành công", da_giai_quyet: "Đã giải quyết",
    dang_xu_ly: "Đang xử lý", cho_phan_hoi: "Chờ phản hồi", loi: "Lỗi",
    mat_ket_noi: "Mất kết nối", chua_ho_tro: "Chưa hỗ trợ", chua_cau_hinh: "Chưa cấu hình",
    chua_kiem_tra: "Chưa kiểm tra", chua_ket_noi: "Chưa kết nối",
  };
  const cls = (bangMau && bangMau[giaTri]) || macDinh[giaTri] || "bg-gray-100 text-gray-700";
  return <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>{nhan[giaTri] || giaTri}</span>;
}
