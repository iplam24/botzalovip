import { useCallback, useEffect, useState } from "react";
import { api, dinhDangThoiGian } from "../lib/api";
import {
  ChuaCoDuLieu, DangTai, LoiTai, Nut, ThongBao as HopThongBao, TieuDeTrang, oNhap,
} from "../components/dungChung";

// Trung tâm thông báo admin (GĐ mở rộng 1): sự kiện từ bảng thong_bao —
// khách mới, khách để lại SĐT, đủ thông tin, gặp nhân viên, khiếu nại, lỗi.
export const NHAN_LOAI_THONG_BAO: Record<string, string> = {
  khach_moi: "Khách hàng mới",
  co_so_dien_thoai: "Khách để lại số điện thoại",
  du_thong_tin: "Đã thu thập đủ thông tin",
  gap_nhan_vien: "Khách yêu cầu gặp nhân viên",
  khieu_nai: "Khách khiếu nại",
  bot_khong_tra_loi_duoc: "Bot không trả lời được",
  loi_he_thong: "Lỗi hệ thống",
};

const MAU_MUC_DO: Record<string, string> = {
  thong_tin: "bg-blue-100 text-blue-800",
  canh_bao: "bg-amber-100 text-amber-800",
  khan_cap: "bg-red-100 text-red-800",
};
const NHAN_MUC_DO: Record<string, string> = {
  thong_tin: "Thông tin",
  canh_bao: "Cảnh báo",
  khan_cap: "Khẩn cấp",
};

export default function ThongBao() {
  const [ds, setDs] = useState<any[]>([]);
  const [dangTai, setDangTai] = useState(true);
  const [loi, setLoi] = useState("");
  const [chiChuaDoc, setChiChuaDoc] = useState(false);
  const [loai, setLoai] = useState("");
  const [soChuaDoc, setSoChuaDoc] = useState(0);
  const [thongBao, setThongBao] = useState<{ loai: "thanh_cong" | "loi"; text: string } | null>(null);

  const tai = useCallback(async () => {
    setDangTai(true);
    setLoi("");
    try {
      const thamSo = new URLSearchParams();
      if (chiChuaDoc) thamSo.set("chua_doc", "true");
      if (loai) thamSo.set("loai", loai);
      const chuoi = thamSo.toString() ? `?${thamSo.toString()}` : "";
      const [danhSach, dem] = await Promise.all([
        api(`/api/thong-bao${chuoi}`),
        api("/api/thong-bao/dem-chua-doc"),
      ]);
      setDs(danhSach);
      setSoChuaDoc(dem.chua_doc || 0);
    } catch (e: any) {
      setLoi(e.message);
    } finally {
      setDangTai(false);
    }
  }, [chiChuaDoc, loai]);

  useEffect(() => { tai(); }, [tai]);

  const danhDauDaDoc = async (id: number) => {
    try {
      await api(`/api/thong-bao/${id}/da-doc`, { method: "POST" });
      await tai();
    } catch (e: any) {
      setThongBao({ loai: "loi", text: e.message });
    }
  };

  const danhDauTatCa = async () => {
    try {
      const kq = await api("/api/thong-bao/danh-dau-tat-ca-da-doc", { method: "POST" });
      setThongBao({ loai: "thanh_cong", text: `Đã đánh dấu đã đọc ${kq.da_danh_dau} thông báo.` });
      await tai();
    } catch (e: any) {
      setThongBao({ loai: "loi", text: e.message });
    }
  };

  return (
    <div className="p-4 sm:p-6">
      <TieuDeTrang
        tieuDe="Thông báo"
        moTa={`Sự kiện quan trọng hệ thống ghi nhận cho quản trị viên. Hiện có ${soChuaDoc} thông báo chưa đọc.`}
      >
        <Nut mau="xam" onClick={danhDauTatCa} disabled={soChuaDoc === 0}><i className="fa-solid fa-check-double mr-2" />Đánh dấu tất cả đã đọc</Nut>
        <Nut mau="xam" onClick={tai}>Tải lại</Nut>
      </TieuDeTrang>
      {thongBao && <HopThongBao loai={thongBao.loai}>{thongBao.text}</HopThongBao>}

      <div className="bg-white dark:bg-neutral-900 rounded shadow">
        <div className="p-3 border-b flex flex-wrap gap-2 items-center">
          <select className={`${oNhap} max-w-xs`} value={loai} onChange={(e) => setLoai(e.target.value)}>
            <option value="">Tất cả loại thông báo</option>
            {Object.entries(NHAN_LOAI_THONG_BAO).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" checked={chiChuaDoc} onChange={(e) => setChiChuaDoc(e.target.checked)} />
            Chỉ hiện chưa đọc
          </label>
        </div>
        {dangTai ? <DangTai /> : loi ? <LoiTai loi={loi} onThuLai={tai} /> : ds.length === 0 ? (
          <div className="p-4"><ChuaCoDuLieu text="Chưa có thông báo nào khớp bộ lọc. Thông báo tự sinh khi có khách mới, khách để lại số điện thoại, yêu cầu gặp nhân viên, khiếu nại hoặc lỗi hệ thống." /></div>
        ) : (
          <ul className="divide-y">
            {ds.map((n) => (
              <li key={n.id} className={`p-4 flex gap-3 ${n.is_read ? "" : "bg-blue-50/60 dark:bg-neutral-800/60"}`}>
                <span className={`mt-1.5 inline-block w-2.5 h-2.5 rounded-full shrink-0 ${n.is_read ? "bg-gray-300" : "bg-blue-600"}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`font-medium text-sm ${n.is_read ? "" : "font-semibold"}`}>{n.title}</span>
                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${MAU_MUC_DO[n.level] || MAU_MUC_DO.thong_tin}`}>
                      {NHAN_MUC_DO[n.level] || n.level}
                    </span>
                    <span className="inline-block bg-gray-100 dark:bg-neutral-800 px-2 py-0.5 rounded-full text-xs">
                      {NHAN_LOAI_THONG_BAO[n.type] || n.type}
                    </span>
                    {n.sent_via_zalo && (
                      <span className="inline-block bg-green-100 text-green-800 px-2 py-0.5 rounded-full text-xs">Đã gửi Zalo cho admin</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-300 mt-1 whitespace-pre-line">{n.content}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {dinhDangThoiGian(n.created_at)}
                    {n.customer_id ? ` · Khách hàng #${n.customer_id}` : ""}
                    {n.conversation_id ? ` · Hội thoại #${n.conversation_id}` : ""}
                  </p>
                </div>
                {!n.is_read && (
                  <button className="text-blue-600 hover:underline text-sm shrink-0" onClick={() => danhDauDaDoc(n.id)}>
                    Đánh dấu đã đọc
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
