import { useCallback, useEffect, useState } from "react";
import { api, apiTaiFile, dinhDangSo, taiBlobXuong } from "../lib/api";
import { DangTai, LoiTai, Nut, ThongBao, TieuDeTrang } from "../components/dungChung";

// Phân tích và thống kê: mọi con số từ /api/phan-tich (dữ liệu thật trong DB).
// Có chọn khoảng thời gian cho tin nhắn và lượt gọi AI + nút xuất báo cáo CSV.
export default function PhanTich() {
  const [d, setD] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [dangTai, setDangTai] = useState(true);
  const [tuNgay, setTuNgay] = useState("");
  const [denNgay, setDenNgay] = useState("");
  const [dangXuat, setDangXuat] = useState(false);
  const [thongBao, setThongBao] = useState<{ loai: "thanh_cong" | "loi"; text: string } | null>(null);

  const thamSoThoiGian = useCallback(() => {
    const p = new URLSearchParams();
    if (tuNgay) p.set("tu_ngay", `${tuNgay}T00:00:00`);
    if (denNgay) p.set("den_ngay", `${denNgay}T23:59:59`);
    return p.toString();
  }, [tuNgay, denNgay]);

  const tai = useCallback(async () => {
    setDangTai(true);
    setLoi("");
    try {
      setD(await api(`/api/phan-tich?${thamSoThoiGian()}`));
    } catch (e: any) {
      setLoi(e.message);
    } finally {
      setDangTai(false);
    }
  }, [thamSoThoiGian]);

  useEffect(() => { tai(); }, [tai]);

  const xuatCsv = async () => {
    setDangXuat(true);
    setThongBao(null);
    try {
      const { blob, tenFile } = await apiTaiFile(`/api/phan-tich/xuat-csv?${thamSoThoiGian()}`);
      taiBlobXuong(blob, tenFile);
      setThongBao({ loai: "thanh_cong", text: `Đã xuất báo cáo CSV: ${tenFile}` });
    } catch (e: any) {
      setThongBao({ loai: "loi", text: `Xuất CSV thất bại: ${e.message}` });
    } finally {
      setDangXuat(false);
    }
  };

  if (dangTai && !d) return <DangTai />;
  if (loi && !d) return <LoiTai loi={loi} onThuLai={tai} />;

  const nhom: { tieuDe: string; muc: [string, string][] }[] = [
    {
      tieuDe: "Hội thoại và tin nhắn",
      muc: [
        ["Tổng tin nhắn", dinhDangSo(d?.tong_tin_nhan)],
        ["Tin nhắn khách gửi", dinhDangSo(d?.tin_nhan_khach)],
        ["Tin nhắn bot gửi", dinhDangSo(d?.tin_nhan_bot)],
        ["Tin nhắn nhân viên gửi", dinhDangSo(d?.tin_nhan_nhan_vien)],
        ["Tỷ lệ bot trả lời", `${Math.round((d?.ty_le_bot || 0) * 100)}%`],
        ["Tổng hội thoại", dinhDangSo(d?.tong_hoi_thoai)],
        ["Hội thoại chuyển nhân viên", dinhDangSo(d?.hoi_thoai_chuyen_nhan_vien)],
      ],
    },
    {
      tieuDe: "Sử dụng AI",
      muc: [
        ["Số lượt gọi AI", dinhDangSo(d?.luot_goi_ai)],
        ["Lượt gọi AI bị lỗi", dinhDangSo(d?.loi_ai)],
        ["Tổng token đầu vào", dinhDangSo(d?.tong_token_prompt)],
        ["Tổng token đầu ra", dinhDangSo(d?.tong_token_completion)],
        ["Chi phí AI ước tính", dinhDangSo(Math.round(d?.chi_phi_uoc_tinh || 0))],
      ],
    },
    {
      tieuDe: "Dữ liệu hệ thống",
      muc: [
        ["Tổng khách hàng", dinhDangSo(d?.tong_khach_hang)],
        ["Tài liệu tri thức", dinhDangSo(d?.tong_tai_lieu)],
        ["Ký ức đã lưu", dinhDangSo(d?.tong_bo_nho)],
        ["Quy tắc tự động hóa", dinhDangSo(d?.tong_quy_tac)],
        ["Tổng lần chạy quy tắc", dinhDangSo(d?.tong_lan_chay_quy_tac)],
      ],
    },
  ];

  const khongCoDuLieu = (d?.tong_tin_nhan ?? 0) === 0 && (d?.luot_goi_ai ?? 0) === 0;

  return (
    <div className="p-4 sm:p-6">
      <TieuDeTrang tieuDe="Phân tích và thống kê" moTa="Báo cáo tính từ dữ liệu thật đã lưu. Chi phí AI là ước tính theo số token nhà cung cấp trả về, không phải hóa đơn thanh toán.">
        <Nut onClick={xuatCsv} disabled={dangXuat}><i className="fa-solid fa-file-csv mr-2" />{dangXuat ? "Đang xuất..." : "Xuất báo cáo CSV"}</Nut>
        <Nut mau="xam" onClick={tai}>Làm mới</Nut>
      </TieuDeTrang>
      {thongBao && <ThongBao loai={thongBao.loai}>{thongBao.text}</ThongBao>}

      <div className="bg-white dark:bg-neutral-900 rounded shadow p-4 mb-5 flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="block font-medium mb-1">Từ ngày</span>
          <input type="date" className="border rounded px-3 py-2 text-sm dark:bg-neutral-800"
            value={tuNgay} onChange={(e) => setTuNgay(e.target.value)} />
        </label>
        <label className="text-sm">
          <span className="block font-medium mb-1">Đến ngày</span>
          <input type="date" className="border rounded px-3 py-2 text-sm dark:bg-neutral-800"
            value={denNgay} onChange={(e) => setDenNgay(e.target.value)} />
        </label>
        {(tuNgay || denNgay) && (
          <Nut mau="xam" onClick={() => { setTuNgay(""); setDenNgay(""); }}>Xem tất cả thời gian</Nut>
        )}
        <p className="text-xs text-gray-400">
          Khoảng ngày áp dụng cho số tin nhắn và lượt gọi AI; các tổng dữ liệu hệ thống luôn là toàn bộ.
        </p>
      </div>

      {khongCoDuLieu && (
        <div className="bg-amber-50 border border-amber-300 text-amber-800 rounded p-4 text-sm mb-5">
          Hiện chưa có tin nhắn hay lượt gọi AI nào trong khoảng đã chọn — các con số 0 dưới đây là số thật, không phải lỗi.
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-4">
        {nhom.map((n) => (
          <section key={n.tieuDe} className="bg-white dark:bg-neutral-900 rounded shadow p-5">
            <h2 className="font-bold mb-3">{n.tieuDe}</h2>
            <table className="w-full text-sm">
              <tbody>
                {n.muc.map(([k, v]) => (
                  <tr key={k} className="border-b last:border-0">
                    <td className="py-2 text-gray-500">{k}</td>
                    <td className="py-2 text-right font-semibold">{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ))}
      </div>
    </div>
  );
}
