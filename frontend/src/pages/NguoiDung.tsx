import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, dinhDangThoiGian } from "../lib/api";
import {
  ChuaCoDuLieu, DangTai, HopBieuMau, LoiTai, Nut, NutGat, ThongBao, TieuDeTrang, Truong, oNhap,
} from "../components/dungChung";
import { useToast } from "../components/Toast";

// Quản lý người dùng nội bộ (mục 1 + 9.3): đăng nhập bằng username + mật khẩu.
// Trang này quản lý username, mật khẩu (đặt khi tạo, đổi khi sửa), họ tên,
// email, vai trò, khóa/mở tài khoản, và hiển thị lần đăng nhập cuối +
// số khách / số bạn bè Zalo được phân bổ.
const CAC_VAI_TRO = ["QuanTriVienCaoNhat", "QuanTriVien", "QuanLy", "NhanVien", "ChiXem"];
const NHAN_VAI_TRO: Record<string, string> = {
  QuanTriVienCaoNhat: "Quản trị viên cao nhất",
  QuanTriVien: "Quản trị viên",
  QuanLy: "Quản lý",
  NhanVien: "Nhân viên",
  ChiXem: "Chỉ xem",
};

export default function NguoiDung() {
  const toast = useToast();
  const [ds, setDs] = useState<any[]>([]);
  const [dangTai, setDangTai] = useState(true);
  const [loi, setLoi] = useState("");
  const [moForm, setMoForm] = useState(false);
  const [form, setForm] = useState({ username: "", full_name: "", email: "", role: "NhanVien", password: "" });
  const [suaUser, setSuaUser] = useState<any | null>(null);
  const [formSua, setFormSua] = useState({ username: "", full_name: "", email: "", role: "NhanVien", password: "" });
  const [dangLuu, setDangLuu] = useState(false);
  const [thongBao, setThongBao] = useState<{ loai: "thanh_cong" | "loi"; text: string } | null>(null);

  const tai = useCallback(async () => {
    setDangTai(true);
    setLoi("");
    try {
      setDs(await api("/api/auth/nguoi-dung"));
    } catch (e: any) {
      setLoi(e.message);
    } finally {
      setDangTai(false);
    }
  }, []);

  useEffect(() => { tai(); }, [tai]);

  const them = async (e: FormEvent) => {
    e.preventDefault();
    setDangLuu(true);
    try {
      await api("/api/auth/nguoi-dung", { method: "POST", body: JSON.stringify(form) });
      toast.thanhCong(`Đã tạo người dùng “${form.username}”. Người này đăng nhập bằng tên đăng nhập + mật khẩu vừa đặt.`);
      setMoForm(false);
      setForm({ username: "", full_name: "", email: "", role: "NhanVien", password: "" });
      await tai();
    } catch (err: any) {
      setThongBao({ loai: "loi", text: err.message });
    } finally {
      setDangLuu(false);
    }
  };

  const moSua = (u: any) => {
    setSuaUser(u);
    setFormSua({ username: u.username || "", full_name: u.full_name || "", email: u.email || "", role: u.role, password: "" });
    setThongBao(null);
  };

  const luuSua = async (e: FormEvent) => {
    e.preventDefault();
    if (!suaUser) return;
    setDangLuu(true);
    try {
      const body: any = { username: formSua.username, full_name: formSua.full_name, email: formSua.email, role: formSua.role };
      if (formSua.password) body.password = formSua.password; // chỉ gửi khi admin thật sự đặt mật khẩu mới
      await api(`/api/auth/nguoi-dung/${suaUser.id}`, { method: "PUT", body: JSON.stringify(body) });
      toast.thanhCong(`Đã cập nhật người dùng “${formSua.username}”${formSua.password ? " và đổi mật khẩu" : ""}.`);
      setSuaUser(null);
      await tai();
    } catch (err: any) {
      setThongBao({ loai: "loi", text: err.message });
    } finally {
      setDangLuu(false);
    }
  };

  const doiTrangThai = async (u: any, bat: boolean) => {
    try {
      await api(`/api/auth/nguoi-dung/${u.id}`, { method: "PUT", body: JSON.stringify({ is_active: bat }) });
      toast.thongTin(bat ? `Đã mở khóa tài khoản “${u.username}”.` : `Đã khóa tài khoản “${u.username}” — người này sẽ không đăng nhập được.`);
      await tai();
    } catch (e: any) {
      toast.loi(e.message);
    }
  };

  const doiVaiTro = async (u: any, role: string) => {
    try {
      await api(`/api/auth/nguoi-dung/${u.id}`, { method: "PUT", body: JSON.stringify({ role }) });
      toast.thanhCong(`Đã đổi vai trò của “${u.username}” thành ${NHAN_VAI_TRO[role] || role}.`);
      await tai();
    } catch (e: any) {
      toast.loi(e.message);
    }
  };

  const dat = (k: string) => (e: any) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const datSua = (k: string) => (e: any) => setFormSua((f) => ({ ...f, [k]: e.target.value }));

  return (
    <div className="p-4 sm:p-6">
      <TieuDeTrang
        tieuDe="Người dùng"
        moTa="Tài khoản nội bộ đăng nhập bằng tên đăng nhập + mật khẩu. Khóa tài khoản để chặn đăng nhập ngay lập tức."
      >
        <Nut onClick={() => setMoForm(true)}>
          <i className="fa-solid fa-user-plus mr-2" />Thêm người dùng
        </Nut>
      </TieuDeTrang>
      {thongBao && <ThongBao loai={thongBao.loai}>{thongBao.text}</ThongBao>}

      {dangTai ? <DangTai /> : loi ? <LoiTai loi={loi} onThuLai={tai} /> : ds.length === 0 ? (
        <ChuaCoDuLieu text="Chưa có người dùng nào." />
      ) : (
        <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-the overflow-x-auto cuon-dep">
          <table className="min-w-[880px] w-full text-sm">
            <thead>
              <tr className="text-left bg-gray-50 dark:bg-neutral-800">
                <th className="p-3 border-b">Tên đăng nhập</th>
                <th className="p-3 border-b">Họ tên</th>
                <th className="p-3 border-b">Email</th>
                <th className="p-3 border-b">Vai trò</th>
                <th className="p-3 border-b">Trạng thái</th>
                <th className="p-3 border-b">Đăng nhập cuối</th>
                <th className="p-3 border-b">Khách phụ trách</th>
                <th className="p-3 border-b">Bạn bè phụ trách</th>
                <th className="p-3 border-b">Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {ds.map((u) => (
                <tr key={u.id} className={`hover:bg-gray-50 dark:hover:bg-neutral-800 ${!u.is_active ? "opacity-60" : ""}`}>
                  <td className="p-3 border-b font-medium">
                    <i className="fa-regular fa-circle-user mr-2 text-gray-400" />
                    {u.username || <span className="text-gray-400">(chưa có)</span>}
                  </td>
                  <td className="p-3 border-b">{u.full_name || "—"}</td>
                  <td className="p-3 border-b">{u.email}</td>
                  <td className="p-3 border-b">
                    <select className="border rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-neutral-800"
                      value={u.role} onChange={(e) => doiVaiTro(u, e.target.value)}>
                      {CAC_VAI_TRO.map((r) => <option key={r} value={r}>{NHAN_VAI_TRO[r]}</option>)}
                    </select>
                  </td>
                  <td className="p-3 border-b whitespace-nowrap">
                    <NutGat bat={!!u.is_active} onDoi={(bat) => doiTrangThai(u, bat)}
                      nhan={u.is_active ? "Đang hoạt động" : "Đã khóa"} />
                  </td>
                  <td className="p-3 border-b whitespace-nowrap">{u.last_login_at ? dinhDangThoiGian(u.last_login_at) : "Chưa đăng nhập"}</td>
                  <td className="p-3 border-b text-center">{u.so_khach_phu_trach}</td>
                  <td className="p-3 border-b text-center">{u.so_ban_be_phu_trach}</td>
                  <td className="p-3 border-b whitespace-nowrap">
                    <Nut mau="xam" onClick={() => moSua(u)}>
                      <i className="fa-solid fa-pen mr-1.5" />Sửa
                    </Nut>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <HopBieuMau mo={moForm} tieuDe="Thêm người dùng" onDong={() => setMoForm(false)}>
        <form onSubmit={them}>
          <Truong nhan="Tên đăng nhập (username)" batBuoc>
            <input className={oNhap} value={form.username} onChange={dat("username")} required placeholder="Ví dụ: nhanvien1" />
          </Truong>
          <Truong nhan="Họ tên">
            <input className={oNhap} value={form.full_name} onChange={dat("full_name")} placeholder="Ví dụ: Nguyễn Thị B" />
          </Truong>
          <Truong nhan="Email">
            <input className={oNhap} type="email" value={form.email} onChange={dat("email")} placeholder="Không bắt buộc — tự sinh nếu trống" />
          </Truong>
          <Truong nhan="Mật khẩu" batBuoc>
            <input className={oNhap} type="password" value={form.password} onChange={dat("password")} required
              autoComplete="new-password" placeholder="Đặt mật khẩu đăng nhập cho người dùng này" />
          </Truong>
          <Truong nhan="Vai trò">
            <select className={oNhap} value={form.role} onChange={dat("role")}>
              {CAC_VAI_TRO.map((r) => <option key={r} value={r}>{NHAN_VAI_TRO[r]}</option>)}
            </select>
          </Truong>
          <div className="flex justify-end gap-2">
            <Nut mau="xam" onClick={() => setMoForm(false)}>Hủy bỏ</Nut>
            <Nut type="submit" disabled={dangLuu}>{dangLuu ? "Đang tạo..." : "Tạo người dùng"}</Nut>
          </div>
        </form>
      </HopBieuMau>

      <HopBieuMau mo={!!suaUser} tieuDe={`Sửa người dùng${suaUser ? ` — ${suaUser.username}` : ""}`} onDong={() => setSuaUser(null)}>
        <form onSubmit={luuSua}>
          <Truong nhan="Tên đăng nhập (username)" batBuoc>
            <input className={oNhap} value={formSua.username} onChange={datSua("username")} required />
          </Truong>
          <Truong nhan="Họ tên">
            <input className={oNhap} value={formSua.full_name} onChange={datSua("full_name")} />
          </Truong>
          <Truong nhan="Email">
            <input className={oNhap} type="email" value={formSua.email} onChange={datSua("email")} />
          </Truong>
          <Truong nhan="Mật khẩu mới (để trống = giữ nguyên)">
            <input className={oNhap} type="password" value={formSua.password} onChange={datSua("password")}
              autoComplete="new-password" placeholder="Chỉ nhập khi muốn đổi mật khẩu" />
          </Truong>
          <Truong nhan="Vai trò">
            <select className={oNhap} value={formSua.role} onChange={datSua("role")}>
              {CAC_VAI_TRO.map((r) => <option key={r} value={r}>{NHAN_VAI_TRO[r]}</option>)}
            </select>
          </Truong>
          <div className="flex justify-end gap-2">
            <Nut mau="xam" onClick={() => setSuaUser(null)}>Hủy bỏ</Nut>
            <Nut type="submit" disabled={dangLuu}>{dangLuu ? "Đang lưu..." : "Lưu thay đổi"}</Nut>
          </div>
        </form>
      </HopBieuMau>
    </div>
  );
}
