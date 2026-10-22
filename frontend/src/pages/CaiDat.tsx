import { useCallback, useEffect, useMemo, useState } from "react";
import { api, dinhDangThoiGian } from "../lib/api";
import { DangTai, LoiTai, Nut, NutGat, oNhap } from "../components/dungChung";
import { useToast } from "../components/Toast";

// Trung tâm cấu hình (Đợt nâng cấp 2 mục 3/10/11.2): giao diện TỰ SINH từ
// registry cài đặt của backend (GET /api/cai-dat/dang-ky). Mỗi khóa có kiểu
// riêng (bool -> nút gạt, so/gio -> ô số, select -> danh sách chọn, text,
// textarea, mau -> ô chọn màu). Lưu theo nhóm / khôi phục mặc định theo nhóm;
// thay đổi có hiệu lực ngay ở lần xử lý tiếp theo, không cần khởi động lại.
// Bí mật (khóa API, connector secret) KHÔNG ở đây — nằm ở trang chuyên biệt.

type KhoaCaiDat = {
  khoa: string; nhom: string; nhan: string; mo_ta: string; kieu: string;
  mac_dinh: any; gia_tri: any; lua_chon?: string[];
  nhan_lua_chon?: Record<string, string>; min?: number; max?: number;
  da_luu_luc?: string | null;
};

export default function CaiDat() {
  const toast = useToast();
  const [nhomDs, setNhomDs] = useState<any[]>([]);
  const [khoaDs, setKhoaDs] = useState<KhoaCaiDat[]>([]);
  const [giaTri, setGiaTri] = useState<Record<string, any>>({});
  const [nhomChon, setNhomChon] = useState("hanh_vi_bot");
  const [timKiem, setTimKiem] = useState("");
  const [dangTai, setDangTai] = useState(true);
  const [loi, setLoi] = useState("");
  const [dangLuuNhom, setDangLuuNhom] = useState<string | null>(null);
  const [luuLuc, setLuuLuc] = useState<Record<string, string>>({});
  const [sucKhoe, setSucKhoe] = useState<any>(null);

  const tai = useCallback(async () => {
    setDangTai(true);
    setLoi("");
    try {
      const [dk, sk] = await Promise.all([
        api("/api/cai-dat/dang-ky"),
        fetch("/api/suc-khoe").then((r) => r.json()).catch(() => null),
      ]);
      setNhomDs(dk.nhom || []);
      setKhoaDs(dk.cai_dat || []);
      const gt: Record<string, any> = {};
      (dk.cai_dat || []).forEach((c: KhoaCaiDat) => { gt[c.khoa] = c.gia_tri; });
      setGiaTri(gt);
      setSucKhoe(sk);
    } catch (e: any) {
      setLoi(e.message);
    } finally {
      setDangTai(false);
    }
  }, []);

  useEffect(() => { tai(); }, [tai]);

  const dat = (khoa: string, v: any) => setGiaTri((cu) => ({ ...cu, [khoa]: v }));

  const luuNhom = async (nhomKhoa: string) => {
    const khoaCuaNhom = khoaDs.filter((c) => c.nhom === nhomKhoa);
    const body: Record<string, any> = {};
    khoaCuaNhom.forEach((c) => { body[c.khoa] = giaTri[c.khoa]; });
    setDangLuuNhom(nhomKhoa);
    try {
      const kq = await api("/api/cai-dat", { method: "PUT", body: JSON.stringify(body) });
      setGiaTri((cu) => ({ ...cu, ...kq }));
      setLuuLuc((cu) => ({ ...cu, [nhomKhoa]: new Date().toISOString() }));
      toast.thanhCong(`Đã lưu nhóm “${nhomDs.find((n) => n.khoa_nhom === nhomKhoa)?.ten || nhomKhoa}”. Thay đổi có hiệu lực ngay.`);
    } catch (e: any) {
      toast.loi(`Lưu thất bại: ${e.message} (lưu cài đặt yêu cầu quyền quản trị viên)`);
    } finally {
      setDangLuuNhom(null);
    }
  };

  const khoiPhucNhom = async (nhomKhoa: string) => {
    setDangLuuNhom(nhomKhoa);
    try {
      await api("/api/cai-dat/khoi-phuc-mac-dinh", { method: "POST", body: JSON.stringify({ nhom: nhomKhoa }) });
      await tai();
      toast.thongTin(`Đã khôi phục mặc định cho nhóm “${nhomDs.find((n) => n.khoa_nhom === nhomKhoa)?.ten || nhomKhoa}”.`);
    } catch (e: any) {
      toast.loi(`Khôi phục thất bại: ${e.message}`);
    } finally {
      setDangLuuNhom(null);
    }
  };

  const control = (c: KhoaCaiDat) => {
    const v = giaTri[c.khoa];
    if (c.kieu === "bool") {
      return <NutGat bat={!!v} onDoi={(moi) => dat(c.khoa, moi)} nhan={v ? "Đang bật" : "Đang tắt"} />;
    }
    if (c.kieu === "so" || c.kieu === "gio") {
      return (
        <input className={oNhap} type="number" min={c.min} max={c.max} step={c.khoa === "ai_temperature" ? 0.05 : 1}
          value={v ?? ""} onChange={(e) => dat(c.khoa, e.target.value === "" ? "" : Number(e.target.value))} />
      );
    }
    if (c.kieu === "select") {
      return (
        <select className={oNhap} value={v ?? ""} onChange={(e) => dat(c.khoa, e.target.value)}>
          {(c.lua_chon || []).map((lc) => (
            <option key={lc} value={lc}>{c.nhan_lua_chon?.[lc] || lc}</option>
          ))}
        </select>
      );
    }
    if (c.kieu === "mau") {
      return (
        <div className="flex items-center gap-2">
          <input type="color" value={/^#[0-9a-fA-F]{6}$/.test(v || "") ? v : "#0068ff"}
            onChange={(e) => dat(c.khoa, e.target.value)}
            className="w-11 h-10 rounded border cursor-pointer bg-white flex-none" />
          <input className={oNhap} value={v || ""} onChange={(e) => dat(c.khoa, e.target.value)} placeholder="#0068ff" />
        </div>
      );
    }
    if (c.kieu === "textarea") {
      return (
        <textarea className={oNhap} rows={3} value={v ?? ""} onChange={(e) => dat(c.khoa, e.target.value)} />
      );
    }
    return <input className={oNhap} value={v ?? ""} onChange={(e) => dat(c.khoa, e.target.value)} />;
  };

  const khoaTheoNhom = useMemo(() => {
    const m: Record<string, KhoaCaiDat[]> = {};
    khoaDs.forEach((c) => { (m[c.nhom] = m[c.nhom] || []).push(c); });
    return m;
  }, [khoaDs]);

  const ketQuaTim = useMemo(() => {
    const tk = timKiem.trim().toLowerCase();
    if (!tk) return null;
    return khoaDs.filter((c) =>
      c.nhan.toLowerCase().includes(tk) || (c.mo_ta || "").toLowerCase().includes(tk) || c.khoa.includes(tk));
  }, [timKiem, khoaDs]);

  if (dangTai) return <DangTai />;
  if (loi) return <LoiTai loi={loi} onThuLai={tai} />;

  const nhomHienTai = nhomDs.find((n) => n.khoa_nhom === nhomChon);

  const theKhoa = (c: KhoaCaiDat) => (
    <div key={c.khoa} className="py-3.5 border-b last:border-b-0 grid md:grid-cols-[1fr_320px] gap-2 md:gap-6 items-start">
      <div>
        <p className="text-sm font-medium">{c.nhan}</p>
        {c.mo_ta && <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{c.mo_ta}</p>}
        <p className="text-[11px] text-gray-400 mt-1">
          Khóa: <code>{c.khoa}</code> · Mặc định: <code>{String(c.mac_dinh === "" ? "(trống)" : c.mac_dinh)}</code>
          {c.da_luu_luc && <> · Đã lưu lúc {dinhDangThoiGian(c.da_luu_luc)}</>}
        </p>
      </div>
      <div>{control(c)}</div>
    </div>
  );

  return (
    <div className="p-4 sm:p-6">
      <h1 className="text-2xl font-bold mb-1">Cài đặt hệ thống</h1>
      <p className="text-sm text-gray-500 mb-5 max-w-3xl">
        Trung tâm cấu hình toàn diện: mọi thay đổi lưu vào cơ sở dữ liệu và có hiệu lực ngay ở lần xử lý
        tiếp theo — không cần khởi động lại, không cần sửa mã nguồn. Khóa API và bí mật kết nối không nằm
        ở đây (xem “Nhà cung cấp AI” và “Tài khoản Zalo”).
      </p>

      <div className="relative max-w-md mb-5">
        <i className="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm" />
        <input className={`${oNhap} pl-9`} placeholder="Tìm kiếm cài đặt theo tên, mô tả hoặc khóa..."
          value={timKiem} onChange={(e) => setTimKiem(e.target.value)} />
      </div>

      {ketQuaTim ? (
        <section className="bg-white dark:bg-neutral-900 rounded-xl shadow-the p-5 max-w-4xl">
          <h2 className="font-bold mb-1">Kết quả tìm kiếm ({ketQuaTim.length})</h2>
          <p className="text-xs text-gray-400 mb-2">Lưu ý: nút Lưu nằm ở từng nhóm bên dưới — hãy xóa từ khóa tìm kiếm để về nhóm tương ứng khi lưu.</p>
          {ketQuaTim.length === 0
            ? <p className="text-sm text-gray-500 py-3">Không có cài đặt nào khớp.</p>
            : ketQuaTim.map(theKhoa)}
        </section>
      ) : (
        <div className="grid lg:grid-cols-[260px_1fr] gap-4 items-start max-w-6xl">
          {/* Menu nhóm có icon Font Awesome */}
          <aside className="bg-white dark:bg-neutral-900 rounded-xl shadow-the p-2 lg:sticky lg:top-16">
            <div className="flex lg:flex-col gap-1 overflow-x-auto cuon-dep">
              {nhomDs.map((n) => (
                <button key={n.khoa_nhom} onClick={() => setNhomChon(n.khoa_nhom)}
                  className={`flex items-center gap-2.5 text-left px-3 py-2.5 rounded-lg text-sm whitespace-nowrap transition-colors duration-160 ${
                    nhomChon === n.khoa_nhom
                      ? "bg-thuongHieu-50 text-thuongHieu-700 font-medium dark:bg-neutral-800 dark:text-white"
                      : "hover:bg-gray-50 dark:hover:bg-neutral-800"}`}>
                  <i className={`${n.icon} w-5 text-center flex-none`} />
                  <span>{n.ten}</span>
                  <span className="ml-auto text-[11px] text-gray-400">{(khoaTheoNhom[n.khoa_nhom] || []).length}</span>
                </button>
              ))}
            </div>
          </aside>

          <section className="bg-white dark:bg-neutral-900 rounded-xl shadow-the p-5">
            <div className="flex flex-wrap items-start justify-between gap-3 border-b pb-3 mb-1">
              <div>
                <h2 className="font-bold text-lg flex items-center gap-2">
                  <i className={nhomHienTai?.icon} /> {nhomHienTai?.ten}
                </h2>
                {nhomHienTai?.mo_ta && <p className="text-sm text-gray-500 mt-0.5">{nhomHienTai.mo_ta}</p>}
                {luuLuc[nhomChon] && (
                  <p className="text-xs text-green-600 mt-1">
                    <i className="fa-solid fa-circle-check mr-1" />
                    Đã lưu lúc {dinhDangThoiGian(luuLuc[nhomChon])}
                  </p>
                )}
              </div>
              <div className="flex gap-2">
                <Nut mau="xam" onClick={() => khoiPhucNhom(nhomChon)} disabled={dangLuuNhom === nhomChon}>
                  <i className="fa-solid fa-rotate-left mr-1.5" />Khôi phục mặc định
                </Nut>
                <Nut onClick={() => luuNhom(nhomChon)} disabled={dangLuuNhom === nhomChon}>
                  <i className="fa-solid fa-floppy-disk mr-1.5" />
                  {dangLuuNhom === nhomChon ? "Đang lưu..." : "Lưu nhóm này"}
                </Nut>
              </div>
            </div>
            {(khoaTheoNhom[nhomChon] || []).map(theKhoa)}
            {nhomChon === "he_thong" && (
              <div className="pt-4">
                <h3 className="font-semibold mb-1">Sức khỏe hệ thống</h3>
                <p className="text-sm">
                  Trạng thái qua <code>/api/suc-khoe</code>:{" "}
                  {sucKhoe
                    ? <span className="text-green-700 font-medium">{sucKhoe.trang_thai === "khoe" ? "Đang khỏe" : sucKhoe.trang_thai} — {sucKhoe.dich_vu}</span>
                    : <span className="text-red-600">Không gọi được API sức khỏe</span>}
                </p>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
