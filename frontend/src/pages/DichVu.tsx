import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, dinhDangSo } from "../lib/api";
import {
  ChuaCoDuLieu, DangTai, HopBieuMau, HopXacNhan, LoiTai, Nut, ThongBao, TieuDeTrang, Truong, oNhap,
} from "../components/dungChung";

// Danh mục dịch vụ động: toàn bộ tên/giá/chính sách quản lý từ giao diện + DB,
// không hard-code trong mã nguồn. Mỗi lần sửa, phiên bản tự tăng.
const FORM_TRONG = {
  code: "", name: "", description: "", category: "", price: 0, price_text: "",
  policy: "", faq: "", keywords: "", is_active: true,
};

export default function DichVu() {
  const [ds, setDs] = useState<any[]>([]);
  const [dangTai, setDangTai] = useState(true);
  const [loi, setLoi] = useState("");
  const [tuKhoa, setTuKhoa] = useState("");
  const [moForm, setMoForm] = useState(false);
  const [dangSua, setDangSua] = useState<any | null>(null);
  const [form, setForm] = useState<any>({ ...FORM_TRONG });
  const [dangLuu, setDangLuu] = useState(false);
  const [xoaId, setXoaId] = useState<number | null>(null);
  const [dangXoa, setDangXoa] = useState(false);
  const [thongBao, setThongBao] = useState<{ loai: "thanh_cong" | "loi"; text: string } | null>(null);

  const tai = useCallback(async () => {
    setDangTai(true);
    setLoi("");
    try {
      setDs(await api("/api/dich-vu"));
    } catch (e: any) {
      setLoi(e.message);
    } finally {
      setDangTai(false);
    }
  }, []);

  useEffect(() => { tai(); }, [tai]);

  const dsLoc = ds.filter((s) => {
    if (!tuKhoa.trim()) return true;
    const tk = tuKhoa.toLowerCase();
    return `${s.name} ${s.code} ${s.category} ${s.description}`.toLowerCase().includes(tk);
  });

  const moThem = () => { setDangSua(null); setForm({ ...FORM_TRONG }); setMoForm(true); };
  const moSua = (s: any) => {
    setDangSua(s);
    setForm({
      code: s.code || "", name: s.name, description: s.description || "", category: s.category || "",
      price: s.price || 0, price_text: s.price_text || "", policy: s.policy || "", faq: s.faq || "",
      keywords: s.keywords || "", is_active: s.is_active,
    });
    setMoForm(true);
  };

  const luu = async (e: FormEvent) => {
    e.preventDefault();
    setDangLuu(true);
    try {
      const body = { ...form, price: Number(form.price) || 0, code: form.code || null };
      if (dangSua) {
        const kq = await api(`/api/dich-vu/${dangSua.id}`, { method: "PUT", body: JSON.stringify(body) });
        setThongBao({ loai: "thanh_cong", text: `Đã cập nhật dịch vụ “${form.name}” (phiên bản v${kq.version}).` });
      } else {
        await api("/api/dich-vu", { method: "POST", body: JSON.stringify(body) });
        setThongBao({ loai: "thanh_cong", text: `Đã thêm dịch vụ “${form.name}”.` });
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
      await api(`/api/dich-vu/${xoaId}`, { method: "DELETE" });
      setThongBao({ loai: "thanh_cong", text: "Đã xóa dịch vụ." });
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
      <TieuDeTrang tieuDe="Dịch vụ" moTa="Danh mục dịch vụ động — bot tư vấn theo dữ liệu tại đây, thêm dịch vụ mới không cần sửa code.">
        <Nut onClick={moThem}><i className="fa-solid fa-plus mr-2" />Thêm dịch vụ</Nut>
      </TieuDeTrang>
      {thongBao && <ThongBao loai={thongBao.loai}>{thongBao.text}</ThongBao>}

      <div className="bg-white dark:bg-neutral-900 rounded shadow">
        <div className="p-3 border-b">
          <input className={oNhap} placeholder="Tìm theo tên, mã, danh mục hoặc mô tả dịch vụ..."
            value={tuKhoa} onChange={(e) => setTuKhoa(e.target.value)} />
        </div>
        {dangTai ? <DangTai /> : loi ? <LoiTai loi={loi} onThuLai={tai} /> : dsLoc.length === 0 ? (
          <div className="p-4"><ChuaCoDuLieu text={ds.length === 0 ? "Chưa có dịch vụ nào. Thêm dịch vụ đầu tiên để bot có cơ sở tư vấn." : "Không có dịch vụ nào khớp từ khóa tìm kiếm."} /></div>
        ) : (
          <div className="overflow-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left bg-gray-50 dark:bg-neutral-800">
                  <th className="p-3 border-b">Tên dịch vụ</th>
                  <th className="p-3 border-b">Mã</th>
                  <th className="p-3 border-b">Danh mục</th>
                  <th className="p-3 border-b">Giá</th>
                  <th className="p-3 border-b">Phiên bản</th>
                  <th className="p-3 border-b">Trạng thái</th>
                  <th className="p-3 border-b">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {dsLoc.map((s) => (
                  <tr key={s.id} className="hover:bg-gray-50 dark:hover:bg-neutral-800">
                    <td className="p-3 border-b">
                      <span className="font-medium">{s.name}</span>
                      {s.description && <span className="block text-xs text-gray-500 mt-0.5 max-w-md truncate">{s.description}</span>}
                    </td>
                    <td className="p-3 border-b"><code>{s.code}</code></td>
                    <td className="p-3 border-b">{s.category || "—"}</td>
                    <td className="p-3 border-b whitespace-nowrap">
                      {s.price_text || (s.price ? `${dinhDangSo(s.price)} VND` : "Liên hệ")}
                    </td>
                    <td className="p-3 border-b">v{s.version}</td>
                    <td className="p-3 border-b">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${s.is_active ? "bg-green-100 text-green-800" : "bg-gray-200 text-gray-700"}`}>
                        {s.is_active ? "Đang hoạt động" : "Đã tắt"}
                      </span>
                    </td>
                    <td className="p-3 border-b whitespace-nowrap">
                      <button className="text-blue-600 hover:underline mr-3" onClick={() => moSua(s)}>Sửa</button>
                      <button className="text-red-600 hover:underline" onClick={() => setXoaId(s.id)}>Xóa</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <HopBieuMau mo={moForm} tieuDe={dangSua ? `Sửa dịch vụ (đang là v${dangSua.version} — lưu sẽ tăng phiên bản)` : "Thêm dịch vụ"} onDong={() => setMoForm(false)} rong="max-w-2xl">
        <form onSubmit={luu}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Truong nhan="Tên dịch vụ" batBuoc>
              <input className={oNhap} value={form.name} onChange={dat("name")} required placeholder="Ví dụ: Dịch vụ chăm sóc khách hàng" />
            </Truong>
            <Truong nhan="Mã dịch vụ (để trống = tự sinh)">
              <input className={oNhap} value={form.code} onChange={dat("code")} placeholder="Ví dụ: CSKH-01" />
            </Truong>
          </div>
          <Truong nhan="Mô tả">
            <textarea className={oNhap} rows={3} value={form.description} onChange={dat("description")} placeholder="Mô tả ngắn gọn dịch vụ, đối tượng khách hàng phù hợp" />
          </Truong>
          <div className="grid grid-cols-3 gap-3">
            <Truong nhan="Danh mục">
              <input className={oNhap} value={form.category} onChange={dat("category")} placeholder="Ví dụ: Hỗ trợ" />
            </Truong>
            <Truong nhan="Giá (số, VND)">
              <input className={oNhap} type="number" min={0} value={form.price} onChange={dat("price")} />
            </Truong>
            <Truong nhan="Giá hiển thị (văn bản)">
              <input className={oNhap} value={form.price_text} onChange={dat("price_text")} placeholder="Ví dụ: 500.000 VND/tháng" />
            </Truong>
          </div>
          <Truong nhan="Chính sách (bảo hành, hậu mãi, điều kiện áp dụng)">
            <textarea className={oNhap} rows={3} value={form.policy} onChange={dat("policy")} placeholder="Chính sách áp dụng cho dịch vụ này" />
          </Truong>
          <Truong nhan="Câu hỏi thường gặp">
            <textarea className={oNhap} rows={3} value={form.faq} onChange={dat("faq")} placeholder="Hỏi — đáp phổ biến về dịch vụ" />
          </Truong>
          <Truong nhan="Từ khóa (phân cách bằng dấu phẩy)">
            <input className={oNhap} value={form.keywords} onChange={dat("keywords")} placeholder="giúp bot nhận diện khi khách hỏi đến dịch vụ" />
          </Truong>
          <label className="flex items-center gap-2 text-sm mb-4">
            <input type="checkbox" checked={form.is_active} onChange={dat("is_active")} /> Đang hoạt động (bot được tư vấn dịch vụ này)
          </label>
          <div className="flex justify-end gap-2">
            <Nut mau="xam" onClick={() => setMoForm(false)}>Hủy bỏ</Nut>
            <Nut type="submit" disabled={dangLuu}>{dangLuu ? "Đang lưu..." : "Lưu dịch vụ"}</Nut>
          </div>
        </form>
      </HopBieuMau>

      <HopXacNhan
        mo={xoaId !== null}
        tieuDe="Xóa dịch vụ?"
        noiDung="Dịch vụ bị xóa khỏi danh mục, bot sẽ ngừng tư vấn về dịch vụ này. Tài liệu tri thức đã gắn với dịch vụ vẫn còn nhưng mất liên kết. Thao tác yêu cầu quyền quản trị viên."
        nhanNut="Xóa dịch vụ"
        dangXuLy={dangXoa}
        onDong={() => setXoaId(null)}
        onXacNhan={xoa}
      />
    </div>
  );
}
