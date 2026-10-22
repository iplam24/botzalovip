import { FormEvent, Fragment, useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import {
  ChuaCoDuLieu, DangTai, HopBieuMau, HopXacNhan, LoiTai, Nut, ThongBao, TieuDeTrang, Truong, oNhap,
} from "../components/dungChung";

// Kho tri thức: danh sách tài liệu + nhập văn bản trực tiếp + kiểm tra truy xuất
// (nhập câu hỏi -> hiện đoạn tri thức, tài liệu nguồn và điểm liên quan từ backend).
export default function KhoTriThuc() {
  const [ds, setDs] = useState<any[]>([]);
  const [dichVu, setDichVu] = useState<any[]>([]);
  const [dangTai, setDangTai] = useState(true);
  const [loi, setLoi] = useState("");
  const [moForm, setMoForm] = useState(false);
  const [dangSua, setDangSua] = useState<any | null>(null);
  const [form, setForm] = useState({ title: "", content: "", service_id: "" });
  const [dangLuu, setDangLuu] = useState(false);
  const [xoaId, setXoaId] = useState<number | null>(null);
  const [dangXoa, setDangXoa] = useState(false);
  const [thongBao, setThongBao] = useState<{ loai: "thanh_cong" | "loi"; text: string } | null>(null);
  const [chiTietId, setChiTietId] = useState<number | null>(null);

  // Kiểm tra truy xuất
  const [cauHoi, setCauHoi] = useState("");
  const [ketQua, setKetQua] = useState<any[] | null>(null);
  const [dangTruyXuat, setDangTruyXuat] = useState(false);
  const [loiTruyXuat, setLoiTruyXuat] = useState("");

  const tai = useCallback(async () => {
    setDangTai(true);
    setLoi("");
    try {
      const [tl, dv] = await Promise.all([api("/api/tri-thuc/tai-lieu"), api("/api/dich-vu")]);
      setDs(tl);
      setDichVu(dv);
    } catch (e: any) {
      setLoi(e.message);
    } finally {
      setDangTai(false);
    }
  }, []);

  useEffect(() => { tai(); }, [tai]);

  const tenDichVu = (id: any) => dichVu.find((d) => d.id === id)?.name || (id ? `#${id}` : "—");

  const moThem = () => { setDangSua(null); setForm({ title: "", content: "", service_id: "" }); setMoForm(true); };
  const moSua = (d: any) => {
    setDangSua(d);
    setForm({ title: d.title, content: d.content || "", service_id: d.service_id ? String(d.service_id) : "" });
    setMoForm(true);
  };

  const luu = async (e: FormEvent) => {
    e.preventDefault();
    setDangLuu(true);
    try {
      const body = { title: form.title, content: form.content, service_id: form.service_id ? Number(form.service_id) : null };
      if (dangSua) {
        await api(`/api/tri-thuc/tai-lieu/${dangSua.id}`, { method: "PUT", body: JSON.stringify(body) });
        setThongBao({ loai: "thanh_cong", text: `Đã cập nhật tài liệu “${form.title}” (tăng phiên bản, chia đoạn lại).` });
      } else {
        await api("/api/tri-thuc/tai-lieu", { method: "POST", body: JSON.stringify(body) });
        setThongBao({ loai: "thanh_cong", text: `Đã nhập tài liệu “${form.title}” vào kho tri thức.` });
      }
      setMoForm(false);
      await tai();
    } catch (err: any) {
      setThongBao({ loai: "loi", text: err.message });
    } finally {
      setDangLuu(false);
    }
  };

  const xoa = async () => {
    if (xoaId === null) return;
    setDangXoa(true);
    try {
      await api(`/api/tri-thuc/tai-lieu/${xoaId}`, { method: "DELETE" });
      setThongBao({ loai: "thanh_cong", text: "Đã xóa tài liệu và các đoạn tri thức của nó." });
      setXoaId(null);
      await tai();
    } catch (e: any) {
      setThongBao({ loai: "loi", text: e.message });
      setXoaId(null);
    } finally {
      setDangXoa(false);
    }
  };

  const truyXuat = async () => {
    if (!cauHoi.trim()) return;
    setDangTruyXuat(true);
    setLoiTruyXuat("");
    setKetQua(null);
    try {
      const kq = await api("/api/tri-thuc/truy-xuat", {
        method: "POST",
        body: JSON.stringify({ query: cauHoi.trim(), limit: 5 }),
      });
      setKetQua(kq.ket_qua || []);
    } catch (e: any) {
      setLoiTruyXuat(e.message);
    } finally {
      setDangTruyXuat(false);
    }
  };

  return (
    <div className="p-6">
      <TieuDeTrang tieuDe="Kho tri thức" moTa="Bot chỉ trả lời dựa trên dữ liệu đã nhập tại đây — không hard-code giá hay chính sách trong mã nguồn.">
        <Nut onClick={moThem}>+ Nhập tài liệu văn bản</Nut>
      </TieuDeTrang>
      {thongBao && <ThongBao loai={thongBao.loai}>{thongBao.text}</ThongBao>}

      <section className="bg-white dark:bg-neutral-900 rounded shadow p-5 mb-5">
        <h2 className="font-bold mb-2">Kiểm tra truy xuất tri thức</h2>
        <p className="text-sm text-gray-500 mb-3">Nhập câu hỏi như khách hàng sẽ hỏi để xem hệ thống tìm được đoạn nào, từ tài liệu nào, điểm liên quan bao nhiêu.</p>
        <div className="flex gap-2">
          <input className={oNhap} placeholder="Ví dụ: Giá dịch vụ chăm sóc khách hàng là bao nhiêu?"
            value={cauHoi} onChange={(e) => setCauHoi(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") truyXuat(); }} />
          <Nut onClick={truyXuat} disabled={dangTruyXuat || !cauHoi.trim()}>
            {dangTruyXuat ? "Đang tìm..." : "Truy xuất"}
          </Nut>
        </div>
        {loiTruyXuat && <p className="text-sm text-red-600 mt-3">Lỗi truy xuất: {loiTruyXuat}</p>}
        {ketQua !== null && (
          <div className="mt-4 space-y-3">
            {ketQua.length === 0 ? (
              <p className="text-sm text-amber-700 bg-amber-50 border border-amber-300 rounded p-3">
                Không tìm thấy đoạn tri thức nào khớp. Với câu hỏi này, bot sẽ hỏi lại khách hoặc chuyển nhân viên thay vì bịa thông tin.
              </p>
            ) : (
              ketQua.map((k) => (
                <div key={k.chunk_id} className="border rounded p-3">
                  <div className="flex flex-wrap justify-between gap-2 text-sm">
                    <span className="font-medium">📄 {k.title}</span>
                    <span className="text-gray-500">Điểm liên quan: <b>{k.score}</b> · Đoạn #{k.chunk_id}</span>
                  </div>
                  <p className="text-sm text-gray-700 dark:text-gray-200 mt-1.5 whitespace-pre-wrap">{k.content}</p>
                </div>
              ))
            )}
          </div>
        )}
      </section>

      {dangTai ? <DangTai /> : loi ? <LoiTai loi={loi} onThuLai={tai} /> : ds.length === 0 ? (
        <ChuaCoDuLieu text="Kho tri thức đang trống. Hãy nhập tài liệu đầu tiên (bảng giá, chính sách, câu hỏi thường gặp...) để bot có dữ liệu trả lời." />
      ) : (
        <div className="bg-white dark:bg-neutral-900 rounded shadow overflow-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left bg-gray-50 dark:bg-neutral-800">
                <th className="p-3 border-b">Tiêu đề</th>
                <th className="p-3 border-b">Loại nguồn</th>
                <th className="p-3 border-b">Dịch vụ liên quan</th>
                <th className="p-3 border-b">Phiên bản</th>
                <th className="p-3 border-b">Trạng thái</th>
                <th className="p-3 border-b">Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {ds.map((d) => (
                <Fragment key={d.id}>
                  <tr className="hover:bg-gray-50 dark:hover:bg-neutral-800">
                    <td className="p-3 border-b font-medium">{d.title}</td>
                    <td className="p-3 border-b">{d.source_type === "van_ban" ? "Văn bản nhập tay" : d.source_type}</td>
                    <td className="p-3 border-b">{tenDichVu(d.service_id)}</td>
                    <td className="p-3 border-b">v{d.version}</td>
                    <td className="p-3 border-b">{d.is_active ? "Đang dùng" : "Đã tắt"}</td>
                    <td className="p-3 border-b whitespace-nowrap">
                      <button className="text-blue-600 hover:underline mr-3" onClick={() => setChiTietId(chiTietId === d.id ? null : d.id)}>
                        {chiTietId === d.id ? "Ẩn nội dung" : "Xem nội dung"}
                      </button>
                      <button className="text-blue-600 hover:underline mr-3" onClick={() => moSua(d)}>Sửa</button>
                      <button className="text-red-600 hover:underline" onClick={() => setXoaId(d.id)}>Xóa</button>
                    </td>
                  </tr>
                  {chiTietId === d.id && (
                    <tr>
                      <td colSpan={6} className="p-3 border-b bg-gray-50 dark:bg-neutral-800">
                        <p className="whitespace-pre-wrap text-sm">{d.content || "(Tài liệu không có nội dung)"}</p>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <HopBieuMau mo={moForm} tieuDe={dangSua ? "Sửa tài liệu tri thức" : "Nhập tài liệu văn bản"} onDong={() => setMoForm(false)} rong="max-w-2xl">
        <form onSubmit={luu}>
          <Truong nhan="Tiêu đề tài liệu" batBuoc>
            <input className={oNhap} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
              required placeholder="Ví dụ: Bảng giá dịch vụ 2026" />
          </Truong>
          <Truong nhan="Dịch vụ liên quan">
            <select className={oNhap} value={form.service_id} onChange={(e) => setForm({ ...form, service_id: e.target.value })}>
              <option value="">Không gắn dịch vụ cụ thể (dùng chung)</option>
              {dichVu.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </Truong>
          <Truong nhan="Nội dung" batBuoc>
            <textarea className={oNhap} rows={10} value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })}
              required placeholder="Dán nội dung bảng giá / chính sách / hướng dẫn... Hệ thống tự chia đoạn và lập chỉ mục từ khóa khi lưu." />
          </Truong>
          <p className="text-xs text-gray-400 mb-3">Lưu ý: hiện tại nhập liệu hỗ trợ văn bản trực tiếp. Nhập từ PDF/DOCX/XLSX đang phát triển — xem Báo cáo nghiệm thu.</p>
          <div className="flex justify-end gap-2">
            <Nut mau="xam" onClick={() => setMoForm(false)}>Hủy bỏ</Nut>
            <Nut type="submit" disabled={dangLuu}>{dangLuu ? "Đang lưu..." : "Lưu tài liệu"}</Nut>
          </div>
        </form>
      </HopBieuMau>

      <HopXacNhan
        mo={xoaId !== null}
        tieuDe="Xóa tài liệu tri thức?"
        noiDung="Toàn bộ đoạn tri thức của tài liệu này bị xóa, bot sẽ không còn dùng dữ liệu này để trả lời. Thao tác yêu cầu quyền quản trị viên."
        nhanNut="Xóa tài liệu"
        dangXuLy={dangXoa}
        onDong={() => setXoaId(null)}
        onXacNhan={xoa}
      />
    </div>
  );
}
