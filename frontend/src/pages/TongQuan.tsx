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

  // Thẻ thống kê có icon Font Awesome trong ô bo góc màu (design pass đợt 3)
  const the = (nhan: string, giaTri: any, ghiChu: string | undefined, icon: string, mauIcon: string) => (
    <div className="bg-white dark:bg-neutral-900 p-4 rounded-xl shadow-the flex items-start gap-3">
      <span className={`the-thong-ke-icon ${mauIcon}`}><i className={icon} /></span>
      <div className="min-w-0">
        <div className="text-sm text-gray-500">{nhan}</div>
        <div className="text-2xl font-bold mt-0.5">{giaTri}</div>
        {ghiChu && <div className="text-xs text-gray-400 mt-1">{ghiChu}</div>}
      </div>
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
        {the("Tổng khách hàng", dinhDangSo(tongQuan?.tong_khach_hang), undefined, "fa-solid fa-users", "bg-blue-100 text-blue-600 dark:bg-blue-950")}
        {the("Tổng hội thoại", dinhDangSo(tongQuan?.tong_hoi_thoai),
          `${dinhDangSo(tongQuan?.hoi_thoai_dang_xu_ly)} đang xử lý`, "fa-solid fa-comments", "bg-violet-100 text-violet-600 dark:bg-violet-950")}
        {the("Hội thoại nhân viên tiếp quản", dinhDangSo(tongQuan?.hoi_thoai_chuyen_nhan_vien), undefined, "fa-solid fa-headset", "bg-purple-100 text-purple-600 dark:bg-purple-950")}
        {the("Tổng tin nhắn", dinhDangSo(tongQuan?.tong_tin_nhan),
          phanTich ? `Bot: ${dinhDangSo(phanTich.tin_nhan_bot)} · Khách: ${dinhDangSo(phanTich.tin_nhan_khach)}` : undefined, "fa-solid fa-message", "bg-sky-100 text-sky-600 dark:bg-sky-950")}
        {the("Tài liệu tri thức", dinhDangSo(tongQuan?.tong_tai_lieu), undefined, "fa-solid fa-book-open", "bg-amber-100 text-amber-600 dark:bg-amber-950")}
        {the("Ký ức đã lưu (Bộ nhớ AI)", dinhDangSo(tongQuan?.tong_bo_nho), undefined, "fa-solid fa-brain", "bg-pink-100 text-pink-600 dark:bg-pink-950")}
        {the("Dịch vụ đang quản lý", dinhDangSo(tongQuan?.tong_dich_vu), undefined, "fa-solid fa-tags", "bg-green-100 text-green-600 dark:bg-green-950")}
        {the("Lượt gọi AI", dinhDangSo(tongQuan?.tong_luot_goi_ai),
          `${dinhDangSo(tongQuan?.loi_goi_ai)} lượt lỗi · Chi phí ước tính: ${dinhDangSo(Math.round(tongQuan?.chi_phi_ai_uoc_tinh || 0))}`, "fa-solid fa-robot", "bg-indigo-100 text-indigo-600 dark:bg-indigo-950")}
      </div>

      {/* Mini bar chart hoạt động 7 ngày (design pass đợt 3) — dữ liệu thật từ /api/tong-quan */}
      {Array.isArray(tongQuan?.hoat_dong_7_ngay) && (
        <section className="bg-white dark:bg-neutral-900 p-5 rounded-xl shadow-the mt-6">
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <h2 className="font-bold flex items-center gap-2">
              <i className="fa-solid fa-chart-column text-thuongHieu-600" /> Hoạt động 7 ngày gần nhất
            </h2>
            <span className="flex-1" />
            <span className="text-xs text-gray-500 flex items-center gap-3">
              <span><span className="inline-block w-2.5 h-2.5 rounded-sm bg-sky-400 mr-1" />Khách</span>
              <span><span className="inline-block w-2.5 h-2.5 rounded-sm bg-blue-600 mr-1" />Bot</span>
              <span><span className="inline-block w-2.5 h-2.5 rounded-sm bg-green-500 mr-1" />Nhân viên</span>
            </span>
          </div>
          {(() => {
            const dsNgay = tongQuan.hoat_dong_7_ngay as any[];
            const lonNhat = Math.max(1, ...dsNgay.map((d) => d.tong || 0));
            const TEN_THU = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];
            return (
              <div className="flex items-end gap-2 sm:gap-4 h-36">
                {dsNgay.map((d) => {
                  const thu = TEN_THU[new Date(`${d.ngay}T00:00:00`).getDay()];
                  const phanTram = (v: number) => `${Math.round(((v || 0) / lonNhat) * 100)}%`;
                  return (
                    <div key={d.ngay} className="flex-1 flex flex-col items-center gap-1.5 min-w-0"
                      title={`${d.ngay}: ${d.tong} tin (Khách ${d.tin_khach} · Bot ${d.tin_bot} · Nhân viên ${d.tin_nhan_vien})`}>
                      <span className="text-xs font-semibold">{d.tong || ""}</span>
                      <div className="w-full max-w-12 h-24 flex flex-col-reverse rounded-t-md overflow-hidden bg-gray-100 dark:bg-neutral-800">
                        <div className="bg-sky-400 w-full" style={{ height: phanTram(d.tin_khach) }} />
                        <div className="bg-blue-600 w-full" style={{ height: phanTram(d.tin_bot) }} />
                        <div className="bg-green-500 w-full" style={{ height: phanTram(d.tin_nhan_vien) }} />
                      </div>
                      <span className="text-xs text-gray-500">{thu}</span>
                      <span className="text-[10px] text-gray-400 -mt-1">{String(d.ngay).slice(5).split("-").reverse().join("/")}</span>
                    </div>
                  );
                })}
              </div>
            );
          })()}
        </section>
      )}

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
