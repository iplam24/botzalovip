import { useCallback, useEffect, useMemo, useState } from "react";
import { api, dinhDangThoiGian } from "../lib/api";
import { ChuaCoDuLieu, DangTai, LoiTai, Nut, PhanTrang, TieuDeTrang, oNhap } from "../components/dungChung";

// Nhật ký hệ thống: lọc + PHÂN TRANG phía máy chủ theo mức độ / phân hệ / từ khóa (Đợt 3 mục 1).
// Không ghi khóa API hay mật khẩu vào nhật ký.
const NHAN_MUC_DO: Record<string, { nhan: string; mau: string }> = {
  info: { nhan: "Thông tin", mau: "bg-blue-100 text-blue-800" },
  warning: { nhan: "Cảnh báo", mau: "bg-amber-100 text-amber-800" },
  error: { nhan: "Lỗi", mau: "bg-red-100 text-red-800" },
};

export default function NhatKyHeThong() {
  const [ds, setDs] = useState<any[]>([]);
  const [dangTai, setDangTai] = useState(true);
  const [loi, setLoi] = useState("");
  const [mucDo, setMucDo] = useState("");
  const [moduleLoc, setModuleLoc] = useState("");
  const [tuKhoa, setTuKhoa] = useState("");
  const [trang, setTrang] = useState(1);
  const [kichThuocTrang, setKichThuocTrang] = useState(20);
  const [tongMuc, setTongMuc] = useState(0);
  const [tongTrang, setTongTrang] = useState(1);

  const tai = useCallback(async () => {
    setDangTai(true);
    setLoi("");
    try {
      const thamSo = new URLSearchParams();
      if (mucDo) thamSo.set("muc_do", mucDo);
      if (moduleLoc) thamSo.set("module", moduleLoc);
      if (tuKhoa.trim()) thamSo.set("tu_khoa", tuKhoa.trim());
      thamSo.set("trang", String(trang));
      thamSo.set("kich_thuoc_trang", String(kichThuocTrang));
      const kq = await api(`/api/nhat-ky?${thamSo.toString()}`);
      setDs(Array.isArray(kq) ? kq : kq.muc || []);
      setTongMuc(Array.isArray(kq) ? kq.length : kq.tong || 0);
      setTongTrang(Array.isArray(kq) ? 1 : kq.tong_trang || 1);
    } catch (e: any) {
      setLoi(e.message);
    } finally {
      setDangTai(false);
    }
  }, [mucDo, moduleLoc, tuKhoa, trang, kichThuocTrang]);

  useEffect(() => {
    const t = setTimeout(tai, tuKhoa ? 400 : 0);
    return () => clearTimeout(t);
  }, [tai, tuKhoa]);

  // Danh sách phân hệ xuất hiện trong dữ liệu hiện tại để đưa vào ô lọc
  const dsModule = useMemo(() => Array.from(new Set(ds.map((l) => l.module).filter(Boolean))), [ds]);

  return (
    <div className="p-4 sm:p-6">
      <TieuDeTrang tieuDe="Nhật ký hệ thống" moTa="Ghi nhận sự kiện quan trọng theo thời gian. Khóa API, mật khẩu và thông tin xác thực không bao giờ được ghi vào nhật ký.">
        <Nut mau="xam" onClick={tai}>Làm mới</Nut>
      </TieuDeTrang>

      <div className="bg-white dark:bg-neutral-900 rounded shadow">
        <div className="p-3 border-b grid md:grid-cols-3 gap-2">
          <select className={oNhap} value={mucDo} onChange={(e) => { setMucDo(e.target.value); setTrang(1); }}>
            <option value="">Tất cả mức độ</option>
            <option value="info">Thông tin</option>
            <option value="warning">Cảnh báo</option>
            <option value="error">Lỗi</option>
          </select>
          <select className={oNhap} value={moduleLoc} onChange={(e) => { setModuleLoc(e.target.value); setTrang(1); }}>
            <option value="">Tất cả phân hệ</option>
            {dsModule.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
          <input className={oNhap} placeholder="Tìm theo từ khóa trong nội dung..."
            value={tuKhoa} onChange={(e) => { setTuKhoa(e.target.value); setTrang(1); }} />
        </div>

        {dangTai ? <DangTai /> : loi ? <LoiTai loi={loi} onThuLai={tai} /> : ds.length === 0 ? (
          <div className="p-4"><ChuaCoDuLieu text="Chưa có dòng nhật ký nào khớp bộ lọc." /></div>
        ) : (
          <div className="overflow-auto">
            <table className="min-w-full text-sm bang-du-lieu">
              <thead>
                <tr className="text-left bg-gray-50 dark:bg-neutral-800">
                  <th className="p-3 border-b">Thời gian</th>
                  <th className="p-3 border-b">Mức độ</th>
                  <th className="p-3 border-b">Phân hệ</th>
                  <th className="p-3 border-b">Nội dung</th>
                  <th className="p-3 border-b">Mã truy vết</th>
                </tr>
              </thead>
              <tbody>
                {ds.map((l) => {
                  const md = NHAN_MUC_DO[l.level] || { nhan: l.level, mau: "bg-gray-100 text-gray-700" };
                  return (
                    <tr key={l.id} className="hover:bg-gray-50 dark:hover:bg-neutral-800 align-top">
                      <td className="p-3 border-b whitespace-nowrap">{dinhDangThoiGian(l.created_at)}</td>
                      <td className="p-3 border-b">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${md.mau}`}>{md.nhan}</span>
                      </td>
                      <td className="p-3 border-b whitespace-nowrap">{l.module || "—"}</td>
                      <td className="p-3 border-b whitespace-pre-wrap">{l.message}</td>
                      <td className="p-3 border-b"><code className="text-xs">{l.trace_id || "—"}</code></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {!dangTai && !loi && ds.length > 0 && (
          <div className="px-3 pb-3">
            <PhanTrang trang={trang} tongTrang={tongTrang} tong={tongMuc} kichThuoc={kichThuocTrang}
              onDoiTrang={setTrang}
              onDoiKichThuoc={(k) => { setKichThuocTrang(k); setTrang(1); }} />
          </div>
        )}
      </div>
      <p className="text-xs text-gray-400 mt-3">Nhật ký được phân trang phía máy chủ — bộ lọc hiện tại được giữ nguyên khi chuyển trang.</p>
    </div>
  );
}
