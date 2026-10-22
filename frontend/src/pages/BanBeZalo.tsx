import { useCallback, useEffect, useMemo, useState } from "react";
import { api, dinhDangThoiGian } from "../lib/api";
import { ChuaCoDuLieu, DangTai, LoiTai, Nut, TieuDeTrang, oNhap } from "../components/dungChung";
import { useToast } from "../components/Toast";

// Bạn bè Zalo + phân bổ admin phụ trách (mục 9.5).
// Danh sách bạn bè chỉ đến từ đồng bộ THẬT qua sidecar zca-js (getAllFriends).
// Nếu sidecar chưa chạy/chưa đăng nhập, trang hiển thị đúng trạng thái lỗi đó
// kèm hướng dẫn — hệ thống không bao giờ chế dữ liệu bạn bè.
export default function BanBeZalo() {
  const toast = useToast();
  const [ds, setDs] = useState<any[]>([]);
  const [thongKe, setThongKe] = useState<any>(null);
  const [nguoiDung, setNguoiDung] = useState<any[]>([]);
  const [dangTai, setDangTai] = useState(true);
  const [loi, setLoi] = useState("");
  const [loiDongBo, setLoiDongBo] = useState("");
  const [dangDongBo, setDangDongBo] = useState(false);
  const [tuKhoa, setTuKhoa] = useState("");
  const [locAdmin, setLocAdmin] = useState("");
  const [chon, setChon] = useState<Record<number, boolean>>({});
  const [adminHangLoat, setAdminHangLoat] = useState<string>("");

  const tai = useCallback(async () => {
    setDangTai(true);
    setLoi("");
    try {
      const thamSo = new URLSearchParams();
      if (tuKhoa.trim()) thamSo.set("tu_khoa", tuKhoa.trim());
      if (locAdmin) thamSo.set("admin_id", locAdmin);
      const [bb, tk] = await Promise.all([
        api(`/api/ban-be-zalo?${thamSo.toString()}`),
        api("/api/ban-be-zalo/thong-ke"),
      ]);
      setDs(bb);
      setThongKe(tk);
    } catch (e: any) {
      setLoi(e.message);
    } finally {
      setDangTai(false);
    }
  }, [tuKhoa, locAdmin]);

  useEffect(() => {
    const t = setTimeout(tai, tuKhoa ? 350 : 0);
    return () => clearTimeout(t);
  }, [tai, tuKhoa]);

  // Danh sách nhân viên cho dropdown phân bổ (chỉ quản trị viên xem được;
  // nếu không có quyền thì bỏ qua, vẫn hiển thị tên admin đã gán).
  useEffect(() => {
    api("/api/auth/nguoi-dung").then(setNguoiDung).catch(() => setNguoiDung([]));
  }, []);

  const dongBo = async () => {
    setDangDongBo(true);
    setLoiDongBo("");
    try {
      const kq = await api("/api/ban-be-zalo/dong-bo", { method: "POST" });
      toast.thanhCong(`Đã đồng bộ từ Zalo: ${kq.tong_tu_zalo} bạn bè (${kq.moi} mới, ${kq.cap_nhat} cập nhật). Phân bổ admin cũ được giữ nguyên.`);
      await tai();
    } catch (e: any) {
      setLoiDongBo(e.message);
    } finally {
      setDangDongBo(false);
    }
  };

  const phanBo = async (b: any, adminId: string) => {
    try {
      await api(`/api/ban-be-zalo/${b.id}/phan-bo`, {
        method: "PUT",
        body: JSON.stringify({ admin_user_id: adminId === "" ? null : Number(adminId) }),
      });
      toast.thanhCong(adminId === "" ? `Đã bỏ phân bổ của “${b.ten_hien_thi}”.` : `Đã phân bổ “${b.ten_hien_thi}” cho nhân viên phụ trách.`);
      await tai();
    } catch (e: any) {
      toast.loi(e.message);
    }
  };

  const idDaChon = useMemo(() => Object.keys(chon).filter((k) => chon[Number(k)]).map(Number), [chon]);

  const phanBoHangLoat = async () => {
    if (idDaChon.length === 0) return;
    try {
      const kq = await api("/api/ban-be-zalo/phan-bo-hang-loat", {
        method: "PUT",
        body: JSON.stringify({ ids: idDaChon, admin_user_id: adminHangLoat === "" ? null : Number(adminHangLoat) }),
      });
      toast.thanhCong(`Đã cập nhật phân bổ cho ${kq.da_cap_nhat} bạn bè.`);
      setChon({});
      await tai();
    } catch (e: any) {
      toast.loi(e.message);
    }
  };

  return (
    <div className="p-4 sm:p-6">
      <TieuDeTrang
        tieuDe="Bạn bè Zalo"
        moTa="Danh sách bạn bè của tài khoản Zalo cá nhân đang liên kết, đồng bộ thật qua dịch vụ phụ. Phân bổ admin phụ trách: khi bạn bè nhắn tin, khách và hội thoại tự gắn người phụ trách đó (nếu chưa có)."
      >
        <Nut onClick={dongBo} disabled={dangDongBo}>
          <i className="fa-solid fa-rotate mr-2" />
          {dangDongBo ? "Đang đồng bộ..." : "Đồng bộ từ Zalo"}
        </Nut>
      </TieuDeTrang>

      {loiDongBo && (
        <div className="bg-amber-50 border border-amber-300 text-amber-800 text-sm rounded-lg p-3.5 mb-4">
          <p className="font-semibold"><i className="fa-solid fa-triangle-exclamation mr-2" />Chưa đồng bộ được danh sách bạn bè</p>
          <p className="mt-1">{loiDongBo}</p>
          <p className="mt-1 text-xs">
            Hãy chắc chắn dịch vụ phụ Zalo cá nhân đang chạy và tài khoản đã đăng nhập (xem trang “Tài khoản Zalo”).
            Hệ thống không hiển thị dữ liệu bạn bè giả — danh sách dưới đây là dữ liệu đã đồng bộ trước đó (nếu có).
          </p>
        </div>
      )}

      {thongKe && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-the p-4">
            <p className="text-xs text-gray-500">Tổng bạn bè</p>
            <p className="text-2xl font-bold mt-0.5">{thongKe.tong_ban}</p>
          </div>
          <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-the p-4">
            <p className="text-xs text-gray-500">Đã phân bổ</p>
            <p className="text-2xl font-bold mt-0.5 text-green-600">{thongKe.da_phan_bo}</p>
          </div>
          <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-the p-4">
            <p className="text-xs text-gray-500">Chưa phân bổ</p>
            <p className="text-2xl font-bold mt-0.5 text-amber-600">{thongKe.chua_phan_bo}</p>
          </div>
          <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-the p-4">
            <p className="text-xs text-gray-500 mb-1">Theo nhân viên</p>
            <div className="space-y-0.5 max-h-16 overflow-y-auto cuon-dep">
              {(thongKe.theo_admin || []).map((t: any) => (
                <p key={t.admin_user_id} className="text-sm flex justify-between gap-2">
                  <span className="truncate">{t.full_name || t.username}</span>
                  <b>{t.so_ban}</b>
                </p>
              ))}
              {(thongKe.theo_admin || []).length === 0 && <p className="text-sm text-gray-400">Chưa có nhân viên</p>}
            </div>
          </div>
        </div>
      )}

      <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-the">
        <div className="p-3 border-b flex flex-col md:flex-row gap-2">
          <div className="relative flex-1">
            <i className="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm" />
            <input className={`${oNhap} pl-9`} placeholder="Tìm bạn bè theo tên hoặc ID Zalo..."
              value={tuKhoa} onChange={(e) => setTuKhoa(e.target.value)} />
          </div>
          <select className={`${oNhap} md:w-60`} value={locAdmin} onChange={(e) => setLocAdmin(e.target.value)}>
            <option value="">Tất cả (đã + chưa phân bổ)</option>
            <option value="chua_phan_bo">Chưa phân bổ</option>
            {nguoiDung.map((u) => (
              <option key={u.id} value={u.id}>Đã phân bổ: {u.full_name || u.username}</option>
            ))}
          </select>
        </div>

        {idDaChon.length > 0 && (
          <div className="p-3 border-b bg-thuongHieu-50 dark:bg-neutral-800 flex flex-wrap items-center gap-2 text-sm">
            <span>Đã chọn <b>{idDaChon.length}</b> bạn bè →</span>
            <select className="border rounded-lg px-2 py-1.5 bg-white dark:bg-neutral-900" value={adminHangLoat}
              onChange={(e) => setAdminHangLoat(e.target.value)}>
              <option value="">(Bỏ phân bổ)</option>
              {nguoiDung.map((u) => (
                <option key={u.id} value={u.id}>{u.full_name || u.username}</option>
              ))}
            </select>
            <Nut onClick={phanBoHangLoat}>Áp dụng hàng loạt</Nut>
            <Nut mau="xam" onClick={() => setChon({})}>Bỏ chọn</Nut>
          </div>
        )}

        {dangTai ? <DangTai /> : loi ? <LoiTai loi={loi} onThuLai={tai} /> : ds.length === 0 ? (
          <div className="p-4">
            <ChuaCoDuLieu text="Chưa có bạn bè nào trong hệ thống. Bấm “Đồng bộ từ Zalo” để lấy danh sách bạn bè thật của tài khoản đang liên kết." />
          </div>
        ) : (
          <div className="overflow-x-auto cuon-dep">
            <table className="min-w-[760px] w-full text-sm">
              <thead>
                <tr className="text-left bg-gray-50 dark:bg-neutral-800">
                  <th className="p-3 border-b w-10">
                    <input type="checkbox" aria-label="Chọn tất cả"
                      checked={ds.length > 0 && ds.every((b) => chon[b.id])}
                      onChange={(e) => {
                        const moi: Record<number, boolean> = {};
                        if (e.target.checked) ds.forEach((b) => { moi[b.id] = true; });
                        setChon(moi);
                      }} />
                  </th>
                  <th className="p-3 border-b">Bạn bè</th>
                  <th className="p-3 border-b">ID Zalo</th>
                  <th className="p-3 border-b">Admin phụ trách</th>
                  <th className="p-3 border-b">Cập nhật</th>
                </tr>
              </thead>
              <tbody>
                {ds.map((b) => (
                  <tr key={b.id} className="hover:bg-gray-50 dark:hover:bg-neutral-800">
                    <td className="p-3 border-b">
                      <input type="checkbox" checked={!!chon[b.id]} aria-label={`Chọn ${b.ten_hien_thi}`}
                        onChange={(e) => setChon((cu) => ({ ...cu, [b.id]: e.target.checked }))} />
                    </td>
                    <td className="p-3 border-b">
                      <span className="flex items-center gap-2.5">
                        {b.avatar_url ? (
                          <img src={b.avatar_url} alt="" className="w-9 h-9 rounded-full object-cover flex-none" />
                        ) : (
                          <span className="w-9 h-9 rounded-full bg-gray-200 dark:bg-neutral-700 flex items-center justify-center text-gray-500 flex-none">
                            <i className="fa-solid fa-user" />
                          </span>
                        )}
                        <span className="font-medium">{b.ten_hien_thi || "(chưa có tên)"}</span>
                      </span>
                    </td>
                    <td className="p-3 border-b text-gray-500">{b.zalo_friend_id}</td>
                    <td className="p-3 border-b">
                      {nguoiDung.length > 0 ? (
                        <select className="border rounded-lg px-2 py-1.5 bg-white dark:bg-neutral-800 max-w-[220px]"
                          value={b.admin_user_id ?? ""} onChange={(e) => phanBo(b, e.target.value)}>
                          <option value="">— Chưa phân bổ —</option>
                          {nguoiDung.map((u) => (
                            <option key={u.id} value={u.id}>{u.full_name || u.username} ({u.username})</option>
                          ))}
                        </select>
                      ) : (
                        <span>{b.admin_full_name || b.admin_username || <span className="text-gray-400">Chưa phân bổ</span>}</span>
                      )}
                    </td>
                    <td className="p-3 border-b whitespace-nowrap text-gray-500">{dinhDangThoiGian(b.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
