import { useCallback, useEffect, useState } from "react";
import { api, dinhDangSo } from "../lib/api";
import { DangTai, HuyHieuTrangThai, LoiTai, Nut, NutGat, TieuDeTrang } from "../components/dungChung";

// Trang Tổng quan: số liệu thật từ /api/tong-quan và /api/phan-tich,
// trạng thái nhà cung cấp AI mặc định + các tài khoản Zalo đã cấu hình.
export default function TongQuan({ diToi }: { diToi?: (tenTrang: string) => void }) {
  const [tongQuan, setTongQuan] = useState<any>(null);
  const [phanTich, setPhanTich] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [dangTai, setDangTai] = useState(true);
  const [tuDo, setTuDo] = useState(false);
  const [dangDoiTuDo, setDangDoiTuDo] = useState(false);

  const tai = useCallback(async () => {
    setDangTai(true);
    setLoi("");
    try {
      const [tq, pt] = await Promise.all([api("/api/tong-quan"), api("/api/phan-tich")]);
      setTongQuan(tq);
      setPhanTich(pt);
    } catch (e: any) {
      setLoi(e.message || "Không gọi được máy chủ");
    } finally {
      setDangTai(false);
    }
  }, []);

  // Công tắc nhanh chế độ trò chuyện tự do (đồng bộ với Cài đặt hệ thống)
  useEffect(() => {
    api("/api/cai-dat")
      .then((cd) => setTuDo(!!cd.che_do_tro_chuyen_tu_do))
      .catch(() => {});
  }, []);

  const doiTuDo = async (bat: boolean) => {
    setDangDoiTuDo(true);
    try {
      await api("/api/cai-dat", { method: "PUT", body: JSON.stringify({ che_do_tro_chuyen_tu_do: bat }) });
      setTuDo(bat);
    } catch {
      /* lỗi quyền/kết nối: giữ nguyên trạng thái cũ */
    } finally {
      setDangDoiTuDo(false);
    }
  };

  useEffect(() => { tai(); }, [tai]);

  if (dangTai && !tongQuan) return <DangTai />;
  if (loi && !tongQuan) return <LoiTai loi={loi} onThuLai={tai} />;

  const the = (nhan: string, giaTri: any, ghiChu?: string) => (
    <div className="bg-white dark:bg-neutral-900 p-4 rounded shadow">
      <div className="text-sm text-gray-500">{nhan}</div>
      <div className="text-2xl font-bold mt-1">{giaTri}</div>
      {ghiChu && <div className="text-xs text-gray-400 mt-1">{ghiChu}</div>}
    </div>
  );

  const provider = tongQuan?.nha_cung_cap_mac_dinh;

  return (
    <div className="p-4 sm:p-6">
      <TieuDeTrang tieuDe="Tổng quan" moTa="Số liệu thật từ cơ sở dữ liệu hệ thống, không dùng số liệu mẫu.">
        <Nut mau="xam" onClick={tai} disabled={dangTai}>{dangTai ? "Đang tải..." : "Làm mới"}</Nut>
      </TieuDeTrang>
      {loi && <p className="text-sm text-red-600 mb-3">Lỗi làm mới: {loi}</p>}

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
        {the("Tổng khách hàng", dinhDangSo(tongQuan?.tong_khach_hang))}
        {the("Tổng hội thoại", dinhDangSo(tongQuan?.tong_hoi_thoai),
          `${dinhDangSo(tongQuan?.hoi_thoai_dang_xu_ly)} đang xử lý`)}
        {the("Hội thoại nhân viên tiếp quản", dinhDangSo(tongQuan?.hoi_thoai_chuyen_nhan_vien))}
        {the("Tổng tin nhắn", dinhDangSo(tongQuan?.tong_tin_nhan),
          phanTich ? `Bot: ${dinhDangSo(phanTich.tin_nhan_bot)} · Khách: ${dinhDangSo(phanTich.tin_nhan_khach)}` : undefined)}
        {the("Tài liệu tri thức", dinhDangSo(tongQuan?.tong_tai_lieu))}
        {the("Ký ức đã lưu (Bộ nhớ AI)", dinhDangSo(tongQuan?.tong_bo_nho))}
        {the("Dịch vụ đang quản lý", dinhDangSo(tongQuan?.tong_dich_vu))}
        {the("Lượt gọi AI", dinhDangSo(tongQuan?.tong_luot_goi_ai),
          `${dinhDangSo(tongQuan?.loi_goi_ai)} lượt lỗi · Chi phí ước tính: ${dinhDangSo(Math.round(tongQuan?.chi_phi_ai_uoc_tinh || 0))}`)}
      </div>

      <section className={`mt-6 p-5 rounded shadow border-2 ${tuDo ? "bg-amber-50 border-amber-300 dark:bg-neutral-900" : "bg-white dark:bg-neutral-900 border-transparent"}`}>
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="font-bold flex items-center gap-2">
            <i className="fa-solid fa-face-laugh-wink text-amber-500" />
            Chế độ trò chuyện tự do
          </h2>
          <span className="flex-1" />
          <NutGat bat={tuDo} onDoi={doiTuDo} disabled={dangDoiTuDo} nhan={tuDo ? "Đang BẬT — bot đang chat bạn bè" : "Đang tắt — bot tư vấn bán hàng"} />
        </div>
        <p className="text-sm text-gray-500 mt-2 max-w-3xl">
          Bật lên là bot <b>nghỉ bán hàng</b>, chuyển sang nói chuyện như bạn bè bình thường: ai nhắn gì rep nấy,
          giải trí, cà khịa. Khi đang bật, bot không chèn tri thức/dịch vụ, không hỏi số điện thoại và không báo lead cho admin.
          Chỉnh tính cách chi tiết tại Cài đặt → nhóm “Chế độ trò chuyện tự do”.
        </p>
      </section>

      <div className="grid md:grid-cols-2 gap-4 mt-6">
        <section className="bg-white dark:bg-neutral-900 p-5 rounded shadow">
          <h2 className="font-bold mb-3">Trạng thái AI</h2>
          {provider ? (
            <div className="text-sm space-y-2">
              <p>Nhà cung cấp mặc định: <b>{provider.name}</b></p>
              <p>Mô hình: <code className="bg-gray-100 dark:bg-neutral-800 px-1.5 py-0.5 rounded">{provider.model}</code></p>
              <p className="flex items-center gap-2">Trạng thái: <HuyHieuTrangThai giaTri={provider.status} /></p>
              {diToi && <Nut mau="xam" onClick={() => diToi("Nhà cung cấp AI")}>Mở Nhà cung cấp AI</Nut>}
            </div>
          ) : (
            <p className="text-sm text-gray-500">
              Chưa có nhà cung cấp AI mặc định. Hãy thêm cấu hình tại phân hệ “Nhà cung cấp AI”.
            </p>
          )}
          {phanTich && (
            <p className="text-sm text-gray-500 mt-3">
              Tỷ lệ bot trả lời: <b>{Math.round((phanTich.ty_le_bot || 0) * 100)}%</b> trên tổng số tin nhắn đã lưu.
            </p>
          )}
        </section>

        <section className="bg-white dark:bg-neutral-900 p-5 rounded shadow">
          <h2 className="font-bold mb-3">Trạng thái Zalo</h2>
          {(tongQuan?.tai_khoan_zalo || []).length === 0 ? (
            <p className="text-sm text-gray-500">Chưa cấu hình tài khoản Zalo nào.</p>
          ) : (
            <ul className="text-sm space-y-2">
              {tongQuan.tai_khoan_zalo.map((a: any) => (
                <li key={a.id} className="flex items-center justify-between gap-2 border-b pb-2 last:border-0">
                  <span>
                    {a.name}
                    <span className="text-gray-400"> · {a.account_type === "mock" ? "Mô phỏng" : a.account_type === "oa" ? "Zalo OA" : "Cá nhân (zca-js)"}</span>
                  </span>
                  <HuyHieuTrangThai giaTri={a.status} />
                </li>
              ))}
            </ul>
          )}
          <p className="text-xs text-gray-400 mt-3">
            Trạng thái thật theo cấu hình đã lưu. Kết nối Zalo cá nhân chạy qua dịch vụ phụ zca-js — xem chi tiết tại “Tài khoản Zalo”.
          </p>
          {diToi && <Nut mau="xam" onClick={() => diToi("Tài khoản Zalo")}>Mở Tài khoản Zalo</Nut>}
        </section>
      </div>
    </div>
  );
}
