import { Suspense, lazy, useEffect, useState } from "react";
import DangNhap from "./pages/DangNhap";
import { ToastProvider } from "./components/Toast";
import { DangTai } from "./components/dungChung";

// Code-splitting theo trang (mục 8): mỗi phân hệ là một chunk riêng, chỉ tải khi mở.
const TongQuan = lazy(() => import("./pages/TongQuan"));
const HoiThoai = lazy(() => import("./pages/HoiThoai"));
const KhachHang = lazy(() => import("./pages/KhachHang"));
const BanBeZalo = lazy(() => import("./pages/BanBeZalo"));
const ThongBao = lazy(() => import("./pages/ThongBao"));
const TaiKhoanZalo = lazy(() => import("./pages/TaiKhoanZalo"));
const NhaCungCapAI = lazy(() => import("./pages/NhaCungCapAI"));
const KhoTriThuc = lazy(() => import("./pages/KhoTriThuc"));
const DichVu = lazy(() => import("./pages/DichVu"));
const BoNhoAI = lazy(() => import("./pages/BoNhoAI"));
const QuyTac = lazy(() => import("./pages/QuyTacTuDongHoa"));
const NhatKy = lazy(() => import("./pages/NhatKyHeThong"));
const PhanTich = lazy(() => import("./pages/PhanTich"));
const SaoLuu = lazy(() => import("./pages/SaoLuu"));
const CaiDat = lazy(() => import("./pages/CaiDat"));
const KiemThuAI = lazy(() => import("./pages/KiemThuAI"));
const NguoiDung = lazy(() => import("./pages/NguoiDung"));

// Toàn bộ nhãn phân hệ bằng tiếng Việt + icon Font Awesome nhất quán (mục 2).
const MENU: { ten: string; icon: string; thanhPhan: any }[] = [
  { ten: "Tổng quan", icon: "fa-solid fa-gauge-high", thanhPhan: TongQuan },
  { ten: "Hội thoại", icon: "fa-solid fa-comments", thanhPhan: HoiThoai },
  { ten: "Khách hàng", icon: "fa-solid fa-users", thanhPhan: KhachHang },
  { ten: "Bạn bè Zalo", icon: "fa-solid fa-address-book", thanhPhan: BanBeZalo },
  { ten: "Thông báo", icon: "fa-solid fa-bell", thanhPhan: ThongBao },
  { ten: "Tài khoản Zalo", icon: "fa-solid fa-mobile-screen", thanhPhan: TaiKhoanZalo },
  { ten: "Nhà cung cấp AI", icon: "fa-solid fa-robot", thanhPhan: NhaCungCapAI },
  { ten: "Kho tri thức", icon: "fa-solid fa-book-open", thanhPhan: KhoTriThuc },
  { ten: "Dịch vụ", icon: "fa-solid fa-tags", thanhPhan: DichVu },
  { ten: "Bộ nhớ AI", icon: "fa-solid fa-brain", thanhPhan: BoNhoAI },
  { ten: "Quy tắc tự động hóa", icon: "fa-solid fa-bolt", thanhPhan: QuyTac },
  { ten: "Nhật ký hệ thống", icon: "fa-solid fa-list-ul", thanhPhan: NhatKy },
  { ten: "Phân tích và thống kê", icon: "fa-solid fa-chart-column", thanhPhan: PhanTich },
  { ten: "Sao lưu và khôi phục", icon: "fa-solid fa-database", thanhPhan: SaoLuu },
  { ten: "Người dùng", icon: "fa-solid fa-user-gear", thanhPhan: NguoiDung },
  { ten: "Cài đặt", icon: "fa-solid fa-gear", thanhPhan: CaiDat },
  { ten: "Trung tâm kiểm thử AI", icon: "fa-solid fa-flask", thanhPhan: KiemThuAI },
];

function UngDung() {
  const [daDangNhap, setDaDangNhap] = useState(!!localStorage.getItem("token"));
  const [trangHienTai, setTrangHienTai] = useState(0);
  const [cheDoToi, setCheDoToi] = useState(false);
  const [tuKhoaMenu, setTuKhoaMenu] = useState("");
  const [thuGon, setThuGon] = useState(false);
  const [moMenuMobile, setMoMenuMobile] = useState(false);
  const [sucKhoe, setSucKhoe] = useState<null | boolean>(null);
  const [tenNguoiDung, setTenNguoiDung] = useState("");
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

  // Thông tin người dùng hiện tại + màu chủ đạo giao diện từ Cài đặt hệ thống
  useEffect(() => {
    if (!daDangNhap) return;
    const token = localStorage.getItem("token");
    fetch("/api/auth/me", { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d) setTenNguoiDung(`${d.username || d.email} · ${d.role}`); })
      .catch(() => {});
    fetch("/api/cai-dat", { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d?.mau_chu_dao_giao_dien) {
          document.documentElement.style.setProperty("--mau-chu-dao", d.mau_chu_dao_giao_dien);
        }
      })
      .catch(() => {});
  }, [daDangNhap]);

  if (!daDangNhap) return <DangNhap onOk={() => setDaDangNhap(true)} />;

  const diToi = (ten: string) => {
    const i = MENU.findIndex((m) => m.ten === ten);
    if (i >= 0) {
      setTrangHienTai(i);
      setMoMenuMobile(false);
    }
  };

  const ThanhPhan = MENU[trangHienTai].thanhPhan;
  const menuLoc = MENU
    .map((m, i) => ({ ...m, chiSo: i }))
    .filter((m) => m.ten.toLowerCase().includes(tuKhoaMenu.toLowerCase()));

  const noiDungMenu = (thuGonHienThi: boolean) => (
    <>
      <div className="flex items-center justify-between mb-3 px-1">
        {!thuGonHienThi && (
          <div className="font-bold text-lg text-white flex items-center gap-2">
            <span className="w-8 h-8 rounded-lg flex items-center justify-center text-white" style={{ background: "var(--mau-chu-dao)" }}>
              <i className="fa-solid fa-comments text-sm" />
            </span>
            Zalo AI Hub
          </div>
        )}
        <button
          onClick={() => setThuGon(!thuGon)}
          className="text-slate-400 hover:text-white px-2 py-1.5 rounded-lg hover:bg-slate-800 text-sm hidden lg:block transition-colors duration-160"
          title={thuGon ? "Mở rộng thanh điều hướng" : "Thu gọn thanh điều hướng"}
        >
          <i className={`fa-solid ${thuGon ? "fa-angles-right" : "fa-angles-left"}`} />
        </button>
        <button
          onClick={() => setMoMenuMobile(false)}
          className="text-slate-400 hover:text-white px-2 py-1.5 rounded-lg hover:bg-slate-800 text-sm lg:hidden"
          title="Đóng menu"
        >
          <i className="fa-solid fa-xmark" />
        </button>
      </div>
      {!thuGonHienThi && (
        <div className="relative mb-3">
          <i className="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-xs" />
          <input
            className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-8 pr-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-thuongHieu-500"
            placeholder="Tìm kiếm phân hệ..."
            value={tuKhoaMenu}
            onChange={(e) => setTuKhoaMenu(e.target.value)}
          />
        </div>
      )}
      <nav className="flex-1 space-y-0.5 overflow-y-auto cuon-dep pr-0.5">
        {menuLoc.map((m) => (
          <button
            key={m.ten}
            onClick={() => diToi(m.ten)}
            title={m.ten}
            className={`flex items-center gap-3 w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors duration-160 ${
              trangHienTai === m.chiSo
                ? "text-white font-medium shadow-nhe"
                : "text-slate-300 hover:bg-slate-800 hover:text-white"
            }`}
            style={trangHienTai === m.chiSo ? { background: "var(--mau-chu-dao)" } : undefined}
          >
            <i className={`${m.icon} w-5 text-center flex-none`} />
            {!thuGonHienThi && <span className="truncate">{m.ten}</span>}
            {m.ten === "Thông báo" && soThongBaoChuaDoc > 0 && !thuGonHienThi && (
              <span className="ml-auto bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] px-1 flex items-center justify-center">
                {soThongBaoChuaDoc > 99 ? "99+" : soThongBaoChuaDoc}
              </span>
            )}
          </button>
        ))}
        {menuLoc.length === 0 && !thuGonHienThi && (
          <p className="text-sm text-slate-500 px-2">Không có phân hệ nào khớp.</p>
        )}
      </nav>
      {!thuGonHienThi && tenNguoiDung && (
        <p className="text-xs text-slate-400 border-t border-slate-800 pt-3 mt-3 break-all px-1">
          <i className="fa-solid fa-circle-user mr-1.5" />
          {tenNguoiDung}
        </p>
      )}
      <button
        className="flex items-center gap-3 text-left text-sm text-slate-300 hover:text-white mt-2 px-3 py-2 rounded-lg hover:bg-slate-800 transition-colors duration-160"
        onClick={() => setCheDoToi(!cheDoToi)}
      >
        <i className={`w-5 text-center ${cheDoToi ? "fa-solid fa-sun" : "fa-solid fa-moon"}`} />
        {!thuGonHienThi && (cheDoToi ? "Chuyển giao diện sáng" : "Chuyển giao diện tối")}
      </button>
      <button
        className="flex items-center gap-3 text-left text-sm text-red-400 hover:text-red-300 mt-0.5 px-3 py-2 rounded-lg hover:bg-slate-800 transition-colors duration-160"
        onClick={() => { localStorage.removeItem("token"); setDaDangNhap(false); }}
      >
        <i className="fa-solid fa-right-from-bracket w-5 text-center" />
        {!thuGonHienThi && "Đăng xuất"}
      </button>
    </>
  );

  return (
    <div className={cheDoToi ? "dark" : ""}>
      <div className="flex min-h-screen bg-gray-50 dark:bg-neutral-950 dark:text-white">
        {/* Sidebar desktop: cố định, thu gọn được */}
        <aside className={`${thuGon ? "w-[68px]" : "w-64"} hidden lg:flex shrink-0 bg-slate-900 p-3 flex-col sticky top-0 h-screen transition-all duration-180`}>
          {noiDungMenu(thuGon)}
        </aside>

        {/* Sidebar mobile: trượt từ trái + nền mờ (responsive mục 11.1) */}
        {moMenuMobile && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <div className="absolute inset-0 bg-black/50" onClick={() => setMoMenuMobile(false)} />
            <aside className="absolute left-0 top-0 h-full w-72 max-w-[85vw] bg-slate-900 p-3 flex flex-col shadow-xl trang-hien-tai">
              {noiDungMenu(false)}
            </aside>
          </div>
        )}

        <main className="flex-1 min-w-0">
          <header className="bg-white/90 dark:bg-neutral-900/90 backdrop-blur border-b px-3 sm:px-4 py-2.5 text-sm flex flex-wrap items-center gap-x-4 gap-y-1 sticky top-0 z-10">
            <button
              className="lg:hidden px-2 py-1.5 rounded-lg border text-gray-600"
              onClick={() => setMoMenuMobile(true)}
              title="Mở menu"
            >
              <i className="fa-solid fa-bars" />
            </button>
            <span className="flex items-center gap-2 min-w-0">
              <span className={`inline-block w-2.5 h-2.5 rounded-full flex-none ${
                sucKhoe === null ? "bg-gray-300" : sucKhoe ? "bg-green-500" : "bg-red-500"
              }`} />
              <span className="truncate">
                {sucKhoe === null
                  ? "Đang kiểm tra trạng thái hệ thống..."
                  : sucKhoe
                    ? "Hệ thống đang khỏe"
                    : "Không kết nối được máy chủ — kiểm tra backend"}
              </span>
            </span>
            <span className="text-gray-500 hidden md:inline">
              Phân hệ: <b className="text-gray-800 dark:text-gray-100">{MENU[trangHienTai].ten}</b>
            </span>
            <span className="flex-1" />
            <button
              className="relative text-lg leading-none px-1.5 py-1"
              onClick={() => diToi("Thông báo")}
              title={soThongBaoChuaDoc > 0 ? `${soThongBaoChuaDoc} thông báo chưa đọc` : "Thông báo"}
            >
              <i className="fa-regular fa-bell text-gray-600 dark:text-gray-300" />
              {soThongBaoChuaDoc > 0 && (
                <span className="absolute -top-1.5 -right-1 bg-red-600 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] px-1 flex items-center justify-center">
                  {soThongBaoChuaDoc > 99 ? "99+" : soThongBaoChuaDoc}
                </span>
              )}
            </button>
            <button className="text-thuongHieu-600 hover:underline hidden sm:inline" onClick={() => diToi("Tài khoản Zalo")}>
              Trạng thái Zalo →
            </button>
            <button className="text-thuongHieu-600 hover:underline hidden sm:inline" onClick={() => diToi("Nhà cung cấp AI")}>
              Trạng thái AI →
            </button>
          </header>
          <div key={trangHienTai} className="trang-hien-tai">
            <Suspense fallback={<DangTai text="Đang tải phân hệ..." />}>
              <ThanhPhan diToi={diToi} />
            </Suspense>
          </div>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <UngDung />
    </ToastProvider>
  );
}
