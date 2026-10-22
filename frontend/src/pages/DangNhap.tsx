import { FormEvent, useState } from "react";
import { dangNhap } from "../lib/api";
import { oNhap, Truong } from "../components/dungChung";

// Trang đăng nhập quản trị — Đợt nâng cấp 2: đăng nhập nội bộ CHỈ bằng tên
// đăng nhập (username), không dùng mật khẩu theo lựa chọn của chủ hệ thống.
export default function DangNhap({ onOk }: { onOk: () => void }) {
  const [username, setUsername] = useState("admin");
  const [loi, setLoi] = useState("");
  const [dangGui, setDangGui] = useState(false);

  const submit = async (ev: FormEvent) => {
    ev.preventDefault();
    setDangGui(true);
    setLoi("");
    try {
      await dangNhap(username.trim());
      onOk();
    } catch (e: any) {
      setLoi(e.message || "Đăng nhập thất bại, hoặc máy chủ chưa chạy.");
    } finally {
      setDangGui(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-thuongHieu-50 to-gray-100 flex items-center justify-center p-4">
      <form onSubmit={submit} className="w-full max-w-sm bg-white p-6 rounded-2xl shadow-the trang-hien-tai">
        <div className="flex items-center gap-3 mb-1">
          <span className="w-11 h-11 rounded-xl bg-thuongHieu-600 text-white flex items-center justify-center text-xl">
            <i className="fa-solid fa-comments" />
          </span>
          <div>
            <h1 className="text-xl font-bold leading-tight">Zalo AI Hub</h1>
            <p className="text-sm text-gray-500">Đăng nhập quản trị hệ thống</p>
          </div>
        </div>
        <div className="mt-4 mb-4">
          {loi && <p className="bg-red-50 border border-red-300 text-red-700 text-sm rounded-lg p-2.5">{loi}</p>}
        </div>
        <Truong nhan="Tên đăng nhập" batBuoc>
          <input
            className={oNhap}
            value={username}
            onChange={(x) => setUsername(x.target.value)}
            required
            autoComplete="username"
            autoFocus
            placeholder="Ví dụ: admin"
          />
        </Truong>
        <button
          className="bg-thuongHieu-600 hover:bg-thuongHieu-700 text-white w-full py-2.5 rounded-lg font-medium disabled:opacity-50 transition-colors duration-160"
          disabled={dangGui}
        >
          {dangGui ? "Đang đăng nhập..." : (<><i className="fa-solid fa-right-to-bracket mr-2" />Đăng nhập</>)}
        </button>
        <p className="text-xs text-gray-400 mt-4 leading-relaxed">
          <i className="fa-solid fa-circle-info mr-1" />
          Đây là đăng nhập nội bộ đơn giản chỉ bằng tên đăng nhập (không mật khẩu) — theo lựa chọn
          của chủ hệ thống cho môi trường vận hành nội bộ. Đừng để lộ địa chỉ quản trị ra ngoài
          nếu chưa có lớp bảo vệ bổ sung (VPN / danh sách IP cho phép).
        </p>
      </form>
    </div>
  );
}
