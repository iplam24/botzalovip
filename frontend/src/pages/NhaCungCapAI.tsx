import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import {
  ChuaCoDuLieu, DangTai, HopBieuMau, HopXacNhan, HuyHieuTrangThai, LoiTai, Nut, ThongBao, TieuDeTrang, Truong, oNhap,
} from "../components/dungChung";

// Nhà cung cấp AI: cấu hình mô hình qua giao diện (không sửa code),
// khóa API chỉ hiển thị dạng che (masked) — backend không bao giờ trả khóa đầy đủ.
const FORM_TRONG = {
  name: "", provider: "openai_compatible", base_url: "", api_key: "",
  model: "", embedding_model: "", max_tokens: 2000, timeout: 30,
  is_active: true, is_default: false,
};

const NHAN_NHA_CUNG_CAP: Record<string, string> = {
  mock: "Mô phỏng (Mock — chỉ để kiểm thử)",
  openai_compatible: "Tương thích OpenAI API",
};

export default function NhaCungCapAI() {
  const [ds, setDs] = useState<any[]>([]);
  const [dangTai, setDangTai] = useState(true);
  const [loi, setLoi] = useState("");
  const [moForm, setMoForm] = useState(false);
  const [dangSua, setDangSua] = useState<any | null>(null);
  const [form, setForm] = useState<any>({ ...FORM_TRONG });
  const [dangLuu, setDangLuu] = useState(false);
  const [xoaId, setXoaId] = useState<number | null>(null);
  const [dangXoa, setDangXoa] = useState(false);
  const [ketQuaKiemTra, setKetQuaKiemTra] = useState<Record<number, any>>({});
  const [dangKiemTraId, setDangKiemTraId] = useState<number | null>(null);
  const [thongBao, setThongBao] = useState<{ loai: "thanh_cong" | "loi"; text: string } | null>(null);

  const tai = useCallback(async () => {
    setDangTai(true);
    setLoi("");
    try {
      setDs(await api("/api/ai-providers"));
    } catch (e: any) {
      setLoi(e.message);
    } finally {
      setDangTai(false);
    }
  }, []);

  useEffect(() => { tai(); }, [tai]);

  const moThem = () => { setDangSua(null); setForm({ ...FORM_TRONG }); setMoForm(true); };
  const moSua = (p: any) => {
    setDangSua(p);
    setForm({
      name: p.name, provider: p.provider, base_url: p.base_url || "", api_key: "",
      model: p.model, embedding_model: p.embedding_model || "",
      max_tokens: p.max_tokens, timeout: p.timeout,
      is_active: p.is_active, is_default: p.is_default,
    });
    setMoForm(true);
  };

  const luu = async (e: FormEvent) => {
    e.preventDefault();
    setDangLuu(true);
    try {
      const body: any = { ...form, max_tokens: Number(form.max_tokens), timeout: Number(form.timeout) };
      if (dangSua && !body.api_key) delete body.api_key; // để trống = giữ khóa cũ
      if (dangSua) {
        await api(`/api/ai-providers/${dangSua.id}`, { method: "PUT", body: JSON.stringify(body) });
        setThongBao({ loai: "thanh_cong", text: `Đã cập nhật cấu hình “${form.name}”.` });
      } else {
        await api("/api/ai-providers", { method: "POST", body: JSON.stringify(body) });
        setThongBao({ loai: "thanh_cong", text: `Đã thêm cấu hình “${form.name}”. Hãy bấm Kiểm tra kết nối để xác thực.` });
      }
      setMoForm(false);
      await tai();
    } catch (err: any) {
      setThongBao({ loai: "loi", text: err.message });
    } finally {
      setDangLuu(false);
    }
  };

  const kiemTra = async (p: any) => {
    setDangKiemTraId(p.id);
    try {
      const kq = await api(`/api/ai-providers/${p.id}/kiem-tra`, { method: "POST" });
      setKetQuaKiemTra((cu) => ({ ...cu, [p.id]: { thanhCong: true, ...kq } }));
      await tai();
    } catch (e: any) {
      setKetQuaKiemTra((cu) => ({ ...cu, [p.id]: { thanhCong: false, loi: e.message } }));
    } finally {
      setDangKiemTraId(null);
    }
  };

  const voHieuHoa = async (p: any) => {
    try {
      await api(`/api/ai-providers/${p.id}`, { method: "PUT", body: JSON.stringify({ is_active: !p.is_active }) });
      setThongBao({ loai: "thanh_cong", text: p.is_active ? `Đã vô hiệu hóa “${p.name}”.` : `Đã bật lại “${p.name}”.` });
      await tai();
    } catch (e: any) {
      setThongBao({ loai: "loi", text: e.message });
    }
  };

  const xoa = async () => {
    if (xoaId === null) return;
    setDangXoa(true);
    try {
      await api(`/api/ai-providers/${xoaId}`, { method: "DELETE" });
      setThongBao({ loai: "thanh_cong", text: "Đã xóa cấu hình nhà cung cấp." });
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
    <div className="p-6">
      <TieuDeTrang tieuDe="Nhà cung cấp AI" moTa="Thêm, kiểm tra và đổi mô hình bằng giao diện — không cần sửa mã nguồn. Khóa API được mã hóa khi lưu và chỉ hiển thị dạng che.">
        <Nut onClick={moThem}>+ Thêm cấu hình</Nut>
      </TieuDeTrang>
      {thongBao && <ThongBao loai={thongBao.loai}>{thongBao.text}</ThongBao>}

      {dangTai ? <DangTai /> : loi ? <LoiTai loi={loi} onThuLai={tai} /> : ds.length === 0 ? (
        <ChuaCoDuLieu text="Chưa có cấu hình AI nào. Bấm “Thêm cấu hình” để nhập khóa API của bạn." />
      ) : (
        <div className="space-y-4">
          {ds.map((p) => {
            const kq = ketQuaKiemTra[p.id];
            return (
              <section key={p.id} className={`bg-white dark:bg-neutral-900 rounded shadow p-5 ${!p.is_active ? "opacity-60" : ""}`}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-bold text-lg flex items-center gap-2">
                      {p.name}
                      {p.is_default && <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">Mặc định</span>}
                      {!p.is_active && <span className="text-xs bg-gray-200 text-gray-700 px-2 py-0.5 rounded-full">Đã vô hiệu hóa</span>}
                    </p>
                    <p className="text-sm text-gray-500 mt-1">
                      {NHAN_NHA_CUNG_CAP[p.provider] || p.provider}
                      {p.base_url && <> · {p.base_url}</>}
                    </p>
                  </div>
                  <HuyHieuTrangThai giaTri={p.status} />
                </div>

                <div className="grid md:grid-cols-4 gap-3 text-sm mt-4">
                  <div><span className="text-gray-500 block">Mô hình hội thoại</span><code className="bg-gray-100 dark:bg-neutral-800 px-1.5 py-0.5 rounded">{p.model}</code></div>
                  <div><span className="text-gray-500 block">Mô hình embedding</span>{p.embedding_model || "—"}</div>
                  <div><span className="text-gray-500 block">Khóa API</span><code>{p.api_key_masked || "(chưa nhập)"}</code></div>
                  <div><span className="text-gray-500 block">Giới hạn token / Thời gian chờ</span>{p.max_tokens} token · {p.timeout} giây</div>
                </div>

                {p.last_error && <p className="text-sm text-red-600 mt-3">Lỗi gần nhất: {p.last_error}</p>}
                {kq && (
                  <div className={`mt-3 text-sm border rounded p-3 ${kq.thanhCong && kq.trang_thai !== "loi" ? "bg-green-50 border-green-300 text-green-800" : "bg-red-50 border-red-300 text-red-700"}`}>
                    {kq.thanhCong ? (
                      <>Kết quả kiểm tra thật: trạng thái <b>{kq.trang_thai}</b>
                        {kq.model && <> · mô hình <b>{kq.model}</b></>}
                        {kq.thong_bao && <> · {kq.thong_bao}</>}
                        {kq.loi && <> · {kq.loi}</>}</>
                    ) : (
                      <>Kiểm tra thất bại: {kq.loi}</>
                    )}
                  </div>
                )}

                <div className="flex flex-wrap gap-2 mt-4">
                  <Nut onClick={() => kiemTra(p)} disabled={dangKiemTraId === p.id}>
                    {dangKiemTraId === p.id ? "Đang kiểm tra..." : "Kiểm tra kết nối"}
                  </Nut>
                  <Nut mau="xam" onClick={() => moSua(p)}>Sửa cấu hình</Nut>
                  <Nut mau="xam" onClick={() => voHieuHoa(p)}>{p.is_active ? "Vô hiệu hóa" : "Bật lại"}</Nut>
                  <Nut mau="do" onClick={() => setXoaId(p.id)}>Xóa</Nut>
                </div>
              </section>
            );
          })}
        </div>
      )}

      <HopBieuMau mo={moForm} tieuDe={dangSua ? "Sửa cấu hình AI" : "Thêm cấu hình AI"} onDong={() => setMoForm(false)} rong="max-w-xl">
        <form onSubmit={luu}>
          <Truong nhan="Tên cấu hình" batBuoc>
            <input className={oNhap} value={form.name} onChange={dat("name")} required placeholder="Ví dụ: LAM Token - code" />
          </Truong>
          <Truong nhan="Nhà cung cấp">
            <select className={oNhap} value={form.provider} onChange={dat("provider")}>
              <option value="openai_compatible">Tương thích OpenAI API</option>
              <option value="mock">Mô phỏng (Mock — chỉ để kiểm thử)</option>
            </select>
          </Truong>
          <Truong nhan="Địa chỉ API (base URL)">
            <input className={oNhap} value={form.base_url} onChange={dat("base_url")} placeholder="https://.../v1 — để trống nếu dùng mặc định của nhà cung cấp" />
          </Truong>
          <Truong nhan={dangSua ? "Khóa API (để trống nếu giữ khóa cũ)" : "Khóa API"} batBuoc={!dangSua}>
            <input className={oNhap} type="password" value={form.api_key} onChange={dat("api_key")}
              placeholder={dangSua ? "•••••••• (không đổi)" : "Nhập khóa API — sẽ được mã hóa khi lưu"} autoComplete="new-password" />
          </Truong>
          <div className="grid grid-cols-2 gap-3">
            <Truong nhan="Mô hình hội thoại" batBuoc>
              <input className={oNhap} value={form.model} onChange={dat("model")} required placeholder="Ví dụ: code" />
            </Truong>
            <Truong nhan="Mô hình embedding">
              <input className={oNhap} value={form.embedding_model} onChange={dat("embedding_model")} placeholder="Có thể để trống" />
            </Truong>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Truong nhan="Giới hạn token mỗi lần gọi">
              <input className={oNhap} type="number" min={1} value={form.max_tokens} onChange={dat("max_tokens")} />
            </Truong>
            <Truong nhan="Thời gian chờ (giây)">
              <input className={oNhap} type="number" min={1} value={form.timeout} onChange={dat("timeout")} />
            </Truong>
          </div>
          <label className="flex items-center gap-2 text-sm mb-2">
            <input type="checkbox" checked={form.is_active} onChange={dat("is_active")} /> Đang kích hoạt
          </label>
          <label className="flex items-center gap-2 text-sm mb-4">
            <input type="checkbox" checked={form.is_default} onChange={dat("is_default")} /> Đặt làm mô hình mặc định của hệ thống
          </label>
          <div className="flex justify-end gap-2">
            <Nut mau="xam" onClick={() => setMoForm(false)}>Hủy bỏ</Nut>
            <Nut type="submit" disabled={dangLuu}>{dangLuu ? "Đang lưu..." : "Lưu cấu hình"}</Nut>
          </div>
        </form>
      </HopBieuMau>

      <HopXacNhan
        mo={xoaId !== null}
        tieuDe="Xóa cấu hình nhà cung cấp?"
        noiDung="Khóa API đã mã hóa của cấu hình này cũng bị xóa. Nếu đây là cấu hình mặc định, hãy đặt cấu hình khác làm mặc định trước. Thao tác yêu cầu quyền quản trị viên."
        nhanNut="Xóa cấu hình"
        dangXuLy={dangXoa}
        onDong={() => setXoaId(null)}
        onXacNhan={xoa}
      />
    </div>
  );
}
