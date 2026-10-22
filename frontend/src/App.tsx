import { useEffect, useState } from "react";
import TongQuan from "./pages/TongQuan";
import HoiThoai from "./pages/HoiThoai";
import KhachHang from "./pages/KhachHang";
import TaiKhoanZalo from "./pages/TaiKhoanZalo";
import NhaCungCapAI from "./pages/NhaCungCapAI";
import KhoTriThuc from "./pages/KhoTriThuc";
import DichVu from "./pages/DichVu";
import BoNhoAI from "./pages/BoNhoAI";
import QuyTac from "./pages/QuyTacTuDongHoa";
import NhatKy from "./pages/NhatKyHeThong";
import PhanTich from "./pages/PhanTich";
import SaoLuu from "./pages/SaoLuu";
import CaiDat from "./pages/CaiDat";
import KiemThuAI from "./pages/KiemThuAI";
import ThongBao from "./pages/ThongBao";
import DangNhap from "./pages/DangNhap";

// Toàn bộ nhãn phân hệ bằng tiếng Việt. `diToi` cho phép Tổng quan nhảy sang phân hệ khác.
const MENU: { ten: string; bieuTuong: string; thanhPhan: any }[] = [
  { ten: "Tổng quan", bieuTuong: "🏠", thanhPhan: TongQuan },
  { ten: "Hội thoại", bieuTuong: "💬", thanhPhan: HoiThoai },
  { ten: "Khách hàng", bieuTuong: "👥", thanhPhan: KhachHang },
  { ten: "Thông báo", bieuTuong: "🔔", thanhPhan: ThongBao },
  { ten: "Tài khoản Zalo", bieuTuong: "📱", thanhPhan: TaiKhoanZalo },
  { ten: "Nhà cung cấp AI", bieuTuong: "🤖", thanhPhan: NhaCungCapAI },
  { ten: "Kho tri thức", bieuTuong: "📚", thanhPhan: KhoTriThuc },
  { ten: "Dịch vụ", bieuTuong: "🧾", thanhPhan: DichVu },
  { ten: "Bộ nhớ AI", bieuTuong: "🧠", thanhPhan: BoNhoAI },
  { ten: "Quy tắc tự động hóa", bieuTuong: "⚙️", thanhPhan: QuyTac },
  { ten: "Nhật ký hệ thống", bieuTuong: "📋", thanhPhan: NhatKy },
  { ten: "Phân tích và thống kê", bieuTuong: "📊", thanhPhan: PhanTich },
  { ten: "Sao lưu và khôi phục", bieuTuong: "💾", thanhPhan: SaoLuu },
  { ten: "Cài đặt", bieuTuong: "🔧", thanhPhan: CaiDat },
  { ten: "Trung tâm kiểm thử AI", bieuTuong: "🧪", thanhPhan: KiemThuAI },
];

export default function App() {
  const [daDangNhap, setDaDangNhap] = useState(!!localStorage.getItem("token"));
  const [trangHienTai, setTrangHienTai] = useState(0);
  const [cheDoToi, setCheDoToi] = useState(false);
  const [tuKhoaMenu, setTuKhoaMenu] = useState("");
  const [thuGon, setThuGon] = useState(false);
  const [sucKhoe, setSucKhoe] = useState<null | boolean>(null);
  const [emailNguoiDung, setEmailNguoiDung] = useState("");
  const [soThongBaoChuaDoc, setSoThongBaoChuaDoc] = useState(0);

  // Header: kiểm tra sức khỏe thật qua /api/suc-khoe mỗi 30 giây
  useEffect(() => {
    if (!daDangNhap) return;
    let dung = false;
    const kiemTra = async () => {
      try {
        const r = await fetch("/api/suc-khoe");
        const d = await r.json();
        if (!dung) setSucKhoe(r.ok && d.trang_thai === "khoe");
      } catch {
        if (!dung) setSucKhoe(false);
      }
    };
    kiemTra();
    const t = setInterval(kiemTra, 30000);
    return () => { dung = true; clearInterval(t); };
  }, [daDangNhap]);

  // Chuông thông báo: đếm số thông báo admin chưa đọc thật, kiểm tra mỗi 30 giây
  useEffect(() => {
    if (!daDangNhap) return;
    let dung = false;
    const kiemTra = async () => {
      try {
        const token = localStorage.getItem("token");
        const r = await fetch("/api/thong-bao/dem-chua-doc", { headers: { Authorization: `Bearer ${token}` } });
        if (!r.ok) return;
        const d = await r.json();
        if (!dung) setSoThongBaoChuaDoc(d.chua_doc || 0);
      } catch { /* bỏ qua, chuông chỉ là chỉ báo phụ */ }
    };
    kiemTra();
    const t = setInterval(kiemTra, 30000);
    return () => { dung = true; clearInterval(t); };
  }, [daDangNhap, trangHienTai]);

  // Lấy email người dùng đang đăng nhập để hiện ở thanh bên
  useEffect(() => {
    if (!daDangNhap) return;
    const token = localStorage.getItem("token");
    fetch("/api/auth/me", { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d) setEmailNguoiDung(`${d.email} · ${d.role}`); })
      .catch(() => {});
  }, [daDangNhap]);

  if (!daDangNhap) return <DangNhap onOk={() => setDaDangNhap(true)} />;

  const diToi = (ten: string) => {
    const i = MENU.findIndex((m) => m.ten === ten);
    if (i >= 0) setTrangHienTai(i);
  };

  const ThanhPhan = MENU[trangHienTai].thanhPhan;
  const menuLoc = MENU
    .map((m, i) => ({ ...m, chiSo: i }))
    .filter((m) => m.ten.toLowerCase().includes(tuKhoaMenu.toLowerCase()));

  return (
    <div className={cheDoToi ? "dark" : ""}>
      <div className="flex min-h-screen bg-gray-50 dark:bg-neutral-950 dark:text-white">
        <aside className={`${thuGon ? "w-16" : "w-64"} shrink-0 bg-white dark:bg-neutral-900 border-r p-3 flex flex-col transition-all`}>
          <div className="flex items-center justify-between mb-3">
            {!thuGon && <div className="font-bold text-lg">Zalo AI Hub</div>}
            <button
              onClick={() => setThuGon(!thuGon)}
              className="text-gray-500 hover:text-gray-800 px-2 py-1 rounded border text-sm"
              title={thuGon ? "Mở rộng thanh điều hướng" : "Thu gọn thanh điều hướng"}
            >
              {thuGon ? "»" : "«"}
            </button>
          </div>
          {!thuGon && (
            <input
              className="border w-full p-2 rounded mb-3 text-sm dark:bg-neutral-800"
              placeholder="Tìm kiếm phân hệ..."
              value={tuKhoaMenu}
              onChange={(e) => setTuKhoaMenu(e.target.value)}
            />
          )}
          <nav className="flex-1 space-y-0.5 overflow-y-auto">
            {menuLoc.map((m) => (
              <button
                key={m.ten}
                onClick={() => setTrangHienTai(m.chiSo)}
                title={m.ten}
                className={`block w-full text-left px-3 py-2 rounded text-sm ${
                  trangHienTai === m.chiSo ? "bg-blue-100 dark:bg-neutral-800 font-medium" : "hover:bg-gray-50 dark:hover:bg-neutral-800"
                }`}
              >
                <span className="mr-2">{m.bieuTuong}</span>
                {!thuGon && m.ten}
              </button>
            ))}
            {menuLoc.length === 0 && !thuGon && (
              <p className="text-sm text-gray-400 px-2">Không có phân hệ nào khớp.</p>
            )}
          </nav>
          {!thuGon && emailNguoiDung && (
            <p className="text-xs text-gray-400 border-t pt-3 mt-3 break-all">{emailNguoiDung}</p>
          )}
          <button className="text-left text-sm mt-2 px-1" onClick={() => setCheDoToi(!cheDoToi)}>
            {thuGon ? (cheDoToi ? "☀️" : "🌙") : cheDoToi ? "☀️ Chuyển giao diện sáng" : "🌙 Chuyển giao diện tối"}
          </button>
          <button
            className="text-left text-sm text-red-600 mt-1 px-1"
            onClick={() => { localStorage.removeItem("token"); setDaDangNhap(false); }}
          >
            {thuGon ? "🚪" : "Đăng xuất"}
          </button>
        </aside>

        <main className="flex-1 min-w-0">
          <header className="bg-white dark:bg-neutral-900 border-b px-4 py-2.5 text-sm flex flex-wrap items-center gap-x-5 gap-y-1 sticky top-0 z-10">
            <span className="flex items-center gap-2">
              <span className={`inline-block w-2.5 h-2.5 rounded-full ${
                sucKhoe === null ? "bg-gray-300" : sucKhoe ? "bg-green-500" : "bg-red-500"
              }`} />
              {sucKhoe === null
                ? "Đang kiểm tra trạng thái hệ thống..."
                : sucKhoe
                  ? "Hệ thống đang khỏe (qua /api/suc-khoe)"
                  : "Không kết nối được máy chủ — kiểm tra backend"}
            </span>
            <span className="text-gray-500">Phân hệ: <b className="text-gray-800 dark:text-gray-100">{MENU[trangHienTai].ten}</b></span>
            <button
              className="relative text-lg leading-none"
              onClick={() => diToi("Thông báo")}
              title={soThongBaoChuaDoc > 0 ? `${soThongBaoChuaDoc} thông báo chưa đọc` : "Thông báo"}
            >
              🔔
              {soThongBaoChuaDoc > 0 && (
                <span className="absolute -top-2 -right-2.5 bg-red-600 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] px-1 flex items-center justify-center">
                  {soThongBaoChuaDoc > 99 ? "99+" : soThongBaoChuaDoc}
                </span>
              )}
            </button>
            <button className="text-blue-600 hover:underline" onClick={() => diToi("Tài khoản Zalo")}>
              Trạng thái Zalo →
            </button>
            <button className="text-blue-600 hover:underline" onClick={() => diToi("Nhà cung cấp AI")}>
              Trạng thái AI →
            </button>
          </header>
          <ThanhPhan diToi={diToi} />
        </main>
      </div>
    </div>
  );
}
