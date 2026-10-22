import { FormEvent, useState } from "react";
import { dangNhap } from "../lib/api";
import { oNhap, Truong } from "../components/dungChung";

// Trang đăng nhập quản trị. Tài khoản mặc định local ghi ở README — phải đổi ngay khi triển khai thật.
export default function DangNhap({ onOk }: { onOk: () => void }) {
  const [email, setEmail] = useState("admin@local");
  const [matKhau, setMatKhau] = useState("");
  const [loi, setLoi] = useState("");
  const [dangGui, setDangGui] = useState(false);

  const submit = async (ev: FormEvent) => {
    ev.preventDefault();
    setDangGui(true);
    setLoi("");
    try {
      await dangNhap(email, matKhau);
      onOk();
    } catch {
      setLoi("Email hoặc mật khẩu không đúng, hoặc máy chủ chưa chạy.");
    } finally {
      setDangGui(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <form onSubmit={submit} className="w-full max-w-sm bg-white p-6 rounded shadow">
        <h1 className="text-xl font-bold">Zalo AI Hub</h1>
        <p className="text-sm text-gray-500 mb-4">Đăng nhập quản trị hệ thống</p>
        {loi && <p className="bg-red-50 border border-red-300 text-red-700 text-sm rounded p-2.5 mb-3">{loi}</p>}
        <Truong nhan="Email" batBuoc>
          <input className={oNhap} type="email" value={email} onChange={(x) => setEmail(x.target.value)} required autoComplete="username" />
        </Truong>
        <Truong nhan="Mật khẩu" batBuoc>
          <input className={oNhap} type="password" value={matKhau} onChange={(x) => setMatKhau(x.target.value)} required autoComplete="current-password" />
        </Truong>
        <button className="bg-blue-600 hover:bg-blue-700 text-white w-full py-2 rounded font-medium disabled:opacity-50" disabled={dangGui}>
          {dangGui ? "Đang đăng nhập..." : "Đăng nhập"}
        </button>
        <p className="text-xs text-gray-400 mt-3">
          Tài khoản mặc định khi chạy local được ghi trong README (đọc từ biến môi trường ADMIN_EMAIL/ADMIN_PASSWORD) — hãy đổi ngay khi triển khai thật.
        </p>
      </form>
    </div>
  );
}
