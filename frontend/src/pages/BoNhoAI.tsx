import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, dinhDangThoiGian } from "../lib/api";
import {
  ChuaCoDuLieu, DangTai, HopBieuMau, HopXacNhan, LoiTai, Nut, PhanTrang, ThongBao, TieuDeTrang, Truong, oNhap,
} from "../components/dungChung";

// Bộ nhớ AI dài hạn: lọc theo loại ký ức và khách hàng, thêm/sửa, ghim, đánh dấu đã xác minh, xóa.
// Suy luận của AI không được coi là sự thật đã xác minh — cột “Đã xác minh” do quản trị viên quyết định.
export const NHAN_LOAI_KY_UC: Record<string, string> = {
  hoi_thoai: "Bộ nhớ hội thoại",
  su_kien: "Bộ nhớ sự kiện",
  ngu_nghia: "Bộ nhớ ngữ nghĩa",
  nghiep_vu: "Bộ nhớ nghiệp vụ",
  quy_trinh: "Bộ nhớ quy trình",
  so_thich: "Bộ nhớ sở thích",
};

const FORM_TRONG = { content: "", memory_type: "ngu_nghia", customer_id: "", confidence: 0.9, verified: false, pinned: false, source: "nhap_tay" };

export default function BoNhoAI() {
  const [ds, setDs] = useState<any[]>([]);
  const [khachHang, setKhachHang] = useState<any[]>([]);
  const [dangTai, setDangTai] = useState(true);
  const [loi, setLoi] = useState("");
  const [locLoai, setLocLoai] = useState("");
  const [locKhach, setLocKhach] = useState("");
  const [tuKhoa, setTuKhoa] = useState("");
  const [moForm, setMoForm] = useState(false);
  const [dangSua, setDangSua] = useState<any | null>(null);
  const [form, setForm] = useState<any>({ ...FORM_TRONG });
  const [dangLuu, setDangLuu] = useState(false);
  const [xoaId, setXoaId] = useState<number | null>(null);
  const [dangXoa, setDangXoa] = useState(false);
  const [thongBao, setThongBao] = useState<{ loai: "thanh_cong" | "loi"; text: string } | null>(null);
  // Phân trang phía máy chủ (Đợt 3 mục 1) + trạng thái Vector DB của bộ nhớ (mục 3)
  const [trang, setTrang] = useState(1);
  const [kichThuocTrang, setKichThuocTrang] = useState(20);
  const [tongMuc, setTongMuc] = useState(0);
  const [tongTrang, setTongTrang] = useState(1);
  const [trangThaiVector, setTrangThaiVector] = useState<any>(null);

  const tenKhach = (id: any) => khachHang.find((k) => k.id === id)?.display_name || (id ? `Khách #${id}` : "— (chung)");

  const tai = useCallback(async () => {
    setDangTai(true);
    setLoi("");
    try {
      const thamSo = new URLSearchParams();
      if (locLoai) thamSo.set("memory_type", locLoai);
      if (locKhach) thamSo.set("customer_id", locKhach);
      if (tuKhoa.trim()) thamSo.set("tu_khoa", tuKhoa.trim());
      thamSo.set("trang", String(trang));
      thamSo.set("kich_thuoc_trang", String(kichThuocTrang));
      const [boNho, kh, ttVector] = await Promise.all([
        api(`/api/bo-nho?${thamSo.toString()}`),
        api("/api/khach-hang"),
        api("/api/bo-nho/trang-thai-vector").catch(() => null),
      ]);
      setDs(Array.isArray(boNho) ? boNho : boNho.muc || []);
      setTongMuc(Array.isArray(boNho) ? boNho.length : boNho.tong || 0);
      setTongTrang(Array.isArray(boNho) ? 1 : boNho.tong_trang || 1);
      setKhachHang(kh);
      if (ttVector) setTrangThaiVector(ttVector);
    } catch (e: any) {
      setLoi(e.message);
    } finally {
      setDangTai(false);
    }
  }, [locLoai, locKhach, tuKhoa, trang, kichThuocTrang]);

  useEffect(() => {
    const t = setTimeout(tai, tuKhoa ? 350 : 0);
    return () => clearTimeout(t);
  }, [tai, tuKhoa]);

  const moThem = () => { setDangSua(null); setForm({ ...FORM_TRONG, customer_id: locKhach }); setMoForm(true); };
  const moSua = (m: any) => {
    setDangSua(m);
    setForm({
      content: m.content, memory_type: m.memory_type,
      customer_id: m.customer_id ? String(m.customer_id) : "",
      confidence: m.confidence, verified: m.verified, pinned: m.pinned, source: m.source || "nhap_tay",
    });
    setMoForm(true);
  };

  const luu = async (e: FormEvent) => {
    e.preventDefault();
    setDangLuu(true);
    try {
      if (dangSua) {
        await api(`/api/bo-nho/${dangSua.id}`, {
          method: "PUT",
          body: JSON.stringify({
            content: form.content, memory_type: form.memory_type,
            confidence: Number(form.confidence), verified: form.verified, pinned: form.pinned,
          }),
        });
        setThongBao({ loai: "thanh_cong", text: "Đã cập nhật ký ức." });
      } else {
        await api("/api/bo-nho", {
          method: "POST",
          body: JSON.stringify({
            content: form.content, memory_type: form.memory_type, source: form.source,
            customer_id: form.customer_id ? Number(form.customer_id) : null,
            confidence: Number(form.confidence), verified: form.verified, pinned: form.pinned,
          }),
        });
        setThongBao({ loai: "thanh_cong", text: "Đã lưu ký ức mới." });
      }
      setMoForm(false);
      await tai();
    } catch (err: any) {
      setThongBao({ loai: "loi", text: err.message });
    } finally {
      setDangLuu(false);
    }
  };

  // Gạt nhanh ghim / xác minh ngay trên bảng
  const ghatNhanh = async (m: any, truong: "pinned" | "verified") => {
    try {
      await api(`/api/bo-nho/${m.id}`, { method: "PUT", body: JSON.stringify({ [truong]: !m[truong] }) });
      setDs((cu) => cu.map((x) => (x.id === m.id ? { ...x, [truong]: !x[truong] } : x)));
    } catch (e: any) {
      setThongBao({ loai: "loi", text: e.message });
    }
  };

  const xoa = async () => {
    if (xoaId === null) return;
    setDangXoa(true);
    try {
      await api(`/api/bo-nho/${xoaId}`, { method: "DELETE" });
      setThongBao({ loai: "thanh_cong", text: "Đã xóa ký ức." });
      setXoaId(null);
      await tai();
    } catch (e: any) {
      setThongBao({ loai: "loi", text: e.message });
      setXoaId(null);
    } finally {
      setDangXoa(false);
    }
  };

  const dat = (k: string) => (e: any) =>
    setForm((f: any) => ({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));

  return (
    <div className="p-4 sm:p-6">
      <TieuDeTrang tieuDe="Bộ nhớ AI" moTa="Ký ức dài hạn có nguồn, độ tin cậy và trạng thái xác minh. Chỉ ký ức liên quan mới được đưa vào ngữ cảnh trả lời.">
        <Nut onClick={moThem}><i className="fa-solid fa-plus mr-2" />Thêm ký ức</Nut>
      </TieuDeTrang>
      {thongBao && <ThongBao loai={thongBao.loai}>{thongBao.text}</ThongBao>}
      {trangThaiVector && (
        <p className="text-sm text-gray-500 mb-3">
          <i className="fa-solid fa-vector-square mr-1.5 text-thuongHieu-600" />
          Tìm kiếm ngữ nghĩa (Vector DB): đã nhúng <b>{trangThaiVector.da_nhung}/{trangThaiVector.tong_muc}</b> ký ức — {trangThaiVector.mo_ta}
        </p>
      )}

      <div className="bg-white dark:bg-neutral-900 rounded shadow">
        <div className="p-3 border-b grid md:grid-cols-3 gap-2">
          <select className={oNhap} value={locLoai} onChange={(e) => { setLocLoai(e.target.value); setTrang(1); }}>
            <option value="">Tất cả loại ký ức</option>
            {Object.entries(NHAN_LOAI_KY_UC).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <select className={oNhap} value={locKhach} onChange={(e) => { setLocKhach(e.target.value); setTrang(1); }}>
            <option value="">Tất cả khách hàng</option>
            {khachHang.map((k) => <option key={k.id} value={k.id}>{k.display_name || `Khách #${k.id}`}</option>)}
          </select>
          <input className={oNhap} placeholder="Tìm trong nội dung ký ức..." value={tuKhoa} onChange={(e) => { setTuKhoa(e.target.value); setTrang(1); }} />
        </div>
        {dangTai ? <DangTai /> : loi ? <LoiTai loi={loi} onThuLai={tai} /> : ds.length === 0 ? (
          <div className="p-4"><ChuaCoDuLieu text="Chưa có ký ức nào khớp bộ lọc. Ký ức được tạo tự động từ hội thoại đủ điều kiện, hoặc thêm tay tại đây." /></div>
        ) : (
          <div className="overflow-auto">
            <table className="min-w-full text-sm bang-du-lieu">
              <thead>
                <tr className="text-left bg-gray-50 dark:bg-neutral-800">
                  <th className="p-3 border-b">Nội dung ký ức</th>
                  <th className="p-3 border-b">Loại</th>
                  <th className="p-3 border-b">Khách hàng</th>
                  <th className="p-3 border-b">Nguồn</th>
                  <th className="p-3 border-b">Độ tin cậy</th>
                  <th className="p-3 border-b">Ngày tạo</th>
                  <th className="p-3 border-b">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {ds.map((m) => (
                  <tr key={m.id} className="hover:bg-gray-50 dark:hover:bg-neutral-800 align-top">
                    <td className="p-3 border-b max-w-md">
                      {m.pinned && <span className="mr-1 text-thuongHieu-600" title="Đã ghim"><i className="fa-solid fa-thumbtack" /></span>}
                      <span className="whitespace-pre-wrap">{m.content}</span>
                    </td>
                    <td className="p-3 border-b whitespace-nowrap">{NHAN_LOAI_KY_UC[m.memory_type] || m.memory_type}</td>
                    <td className="p-3 border-b whitespace-nowrap">{tenKhach(m.customer_id)}</td>
                    <td className="p-3 border-b">{m.source || "—"}</td>
                    <td className="p-3 border-b">{Math.round((m.confidence || 0) * 100)}%</td>
                    <td className="p-3 border-b whitespace-nowrap">{dinhDangThoiGian(m.created_at)}</td>
                    <td className="p-3 border-b whitespace-nowrap">
                      <button className="text-blue-600 hover:underline mr-3" onClick={() => ghatNhanh(m, "pinned")}>
                        {m.pinned ? "Bỏ ghim" : "Ghim"}
                      </button>
                      <button className="text-blue-600 hover:underline mr-3" onClick={() => ghatNhanh(m, "verified")}>
                        {m.verified ? "Bỏ xác minh" : "Xác minh"}
                      </button>
                      <button className="text-blue-600 hover:underline mr-3" onClick={() => moSua(m)}>Sửa</button>
                      <button className="text-red-600 hover:underline" onClick={() => setXoaId(m.id)}>Xóa</button>
                      <span className={`block text-xs mt-1 ${m.verified ? "text-green-700" : "text-gray-400"}`}>
                        {m.verified ? "Đã xác minh" : "Chưa xác minh"}
                      </span>
                    </td>
                  </tr>
                ))}
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

      <HopBieuMau mo={moForm} tieuDe={dangSua ? "Sửa ký ức" : "Thêm ký ức"} onDong={() => setMoForm(false)} rong="max-w-xl">
        <form onSubmit={luu}>
          <Truong nhan="Nội dung ký ức" batBuoc>
            <textarea className={oNhap} rows={4} value={form.content} onChange={dat("content")} required
              placeholder="Chỉ ghi sự kiện/dữ kiện có cơ sở — không ghi suy đoán như sự thật" />
          </Truong>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Truong nhan="Loại ký ức">
              <select className={oNhap} value={form.memory_type} onChange={dat("memory_type")}>
                {Object.entries(NHAN_LOAI_KY_UC).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </Truong>
            {!dangSua && (
              <Truong nhan="Khách hàng liên quan">
                <select className={oNhap} value={form.customer_id} onChange={dat("customer_id")}>
                  <option value="">Không gắn khách cụ thể (ký ức chung)</option>
                  {khachHang.map((k) => <option key={k.id} value={k.id}>{k.display_name || `Khách #${k.id}`}</option>)}
                </select>
              </Truong>
            )}
          </div>
          <Truong nhan={`Độ tin cậy: ${Math.round((Number(form.confidence) || 0) * 100)}%`}>
            <input type="range" min={0} max={1} step={0.05} className="w-full" value={form.confidence} onChange={dat("confidence")} />
          </Truong>
          <label className="flex items-center gap-2 text-sm mb-2">
            <input type="checkbox" checked={form.pinned} onChange={dat("pinned")} /> Ghim ký ức (ưu tiên khi truy xuất)
          </label>
          <label className="flex items-center gap-2 text-sm mb-4">
            <input type="checkbox" checked={form.verified} onChange={dat("verified")} /> Đã xác minh bởi quản trị viên
          </label>
          <div className="flex justify-end gap-2">
            <Nut mau="xam" onClick={() => setMoForm(false)}>Hủy bỏ</Nut>
            <Nut type="submit" disabled={dangLuu}>{dangLuu ? "Đang lưu..." : "Lưu ký ức"}</Nut>
          </div>
        </form>
      </HopBieuMau>

      <HopXacNhan
        mo={xoaId !== null}
        tieuDe="Xóa ký ức?"
        noiDung="Ký ức bị xóa khỏi bộ nhớ dài hạn, bot sẽ không còn dùng thông tin này. Lịch sử hội thoại gốc vẫn được giữ. Thao tác yêu cầu quyền quản trị viên."
        nhanNut="Xóa ký ức"
        dangXuLy={dangXoa}
        onDong={() => setXoaId(null)}
        onXacNhan={xoa}
      />
    </div>
  );
}
