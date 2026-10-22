import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, dinhDangThoiGian } from "../lib/api";
import {
  ChuaCoDuLieu, DangTai, HopBieuMau, HopXacNhan, LoiTai, Nut, ThongBao, TieuDeTrang, Truong, oNhap,
} from "../components/dungChung";

// Quy tắc tự động hóa: điều kiện (từ khóa / ý định / nhãn) -> hành động
// (trả lời sẵn / gọi AI / gắn nhãn / chuyển nhân viên / tạm dừng bot).
// Mỗi quy tắc hiện số lần đã chạy và lần chạy gần nhất từ backend.
export const NHAN_DIEU_KIEN: Record<string, string> = {
  chua_tu_khoa: "Tin nhắn chứa từ khóa",
  intent: "Ý định của khách",
  nhan: "Khách có nhãn",
};

export const NHAN_HANH_DONG: Record<string, string> = {
  tra_loi: "Trả lời bằng nội dung cấu hình",
  goi_ai: "Gọi AI trả lời",
  gan_nhan: "Gắn nhãn khách hàng",
  chuyen_nhan_vien: "Chuyển cho nhân viên",
  tam_dung_bot: "Tạm dừng bot",
};

const FORM_TRONG = {
  name: "", description: "", condition_type: "chua_tu_khoa", condition_value: "",
  action_type: "tra_loi", action_value: "", priority: 10, is_active: true,
};

export default function QuyTacTuDongHoa() {
  const [ds, setDs] = useState<any[]>([]);
  const [dangTai, setDangTai] = useState(true);
  const [loi, setLoi] = useState("");
  const [moForm, setMoForm] = useState(false);
  const [dangSua, setDangSua] = useState<any | null>(null);
  const [form, setForm] = useState<any>({ ...FORM_TRONG });
  const [dangLuu, setDangLuu] = useState(false);
  const [xoaId, setXoaId] = useState<number | null>(null);
  const [dangXoa, setDangXoa] = useState(false);
  const [thongBao, setThongBao] = useState<{ loai: "thanh_cong" | "loi"; text: string } | null>(null);
  const [lanChayMo, setLanChayMo] = useState<number | null>(null);
  const [dsLanChay, setDsLanChay] = useState<any[]>([]);
  const [dangTaiLanChay, setDangTaiLanChay] = useState(false);

  const tai = useCallback(async () => {
    setDangTai(true);
    setLoi("");
    try {
      setDs(await api("/api/quy-tac"));
    } catch (e: any) {
      setLoi(e.message);
    } finally {
      setDangTai(false);
    }
  }, []);

  useEffect(() => { tai(); }, [tai]);

  const xemLanChay = async (r: any) => {
    if (lanChayMo === r.id) { setLanChayMo(null); return; }
    setLanChayMo(r.id);
    setDangTaiLanChay(true);
    try {
      setDsLanChay(await api(`/api/quy-tac/${r.id}/lan-chay`));
    } catch {
      setDsLanChay([]);
    } finally {
      setDangTaiLanChay(false);
    }
  };

  const moThem = () => { setDangSua(null); setForm({ ...FORM_TRONG }); setMoForm(true); };
  const moSua = (r: any) => {
    setDangSua(r);
    setForm({
      name: r.name, description: r.description || "", condition_type: r.condition_type,
      condition_value: r.condition_value || "", action_type: r.action_type,
      action_value: r.action_value || "", priority: r.priority, is_active: r.is_active,
    });
    setMoForm(true);
  };

  const luu = async (e: FormEvent) => {
    e.preventDefault();
    setDangLuu(true);
    try {
      const body = { ...form, priority: Number(form.priority) || 10 };
      if (dangSua) {
        await api(`/api/quy-tac/${dangSua.id}`, { method: "PUT", body: JSON.stringify(body) });
        setThongBao({ loai: "thanh_cong", text: `Đã cập nhật quy tắc “${form.name}”.` });
      } else {
        await api("/api/quy-tac", { method: "POST", body: JSON.stringify(body) });
        setThongBao({ loai: "thanh_cong", text: `Đã tạo quy tắc “${form.name}”.` });
      }
      setMoForm(false);
      await tai();
    } catch (err: any) {
      setThongBao({ loai: "loi", text: err.message });
    } finally {
      setDangLuu(false);
    }
  };

  const doiTrangThai = async (r: any) => {
    try {
      await api(`/api/quy-tac/${r.id}`, {
        method: "PUT",
        body: JSON.stringify({
          name: r.name, description: r.description || "", condition_type: r.condition_type,
          condition_value: r.condition_value || "", action_type: r.action_type,
          action_value: r.action_value || "", priority: r.priority, is_active: !r.is_active,
        }),
      });
      setDs((cu) => cu.map((x) => (x.id === r.id ? { ...x, is_active: !x.is_active } : x)));
    } catch (e: any) {
      setThongBao({ loai: "loi", text: e.message });
    }
  };

  const xoa = async () => {
    if (xoaId === null) return;
    setDangXoa(true);
    try {
      await api(`/api/quy-tac/${xoaId}`, { method: "DELETE" });
      setThongBao({ loai: "thanh_cong", text: "Đã xóa quy tắc." });
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

  const goiYGiaTriHanhDong: Record<string, string> = {
    tra_loi: "Nội dung trả lời gửi cho khách, ví dụ: Chào anh/chị, em hỗ trợ gì ạ?",
    goi_ai: "Để trống — AI tự sinh câu trả lời theo kho tri thức",
    gan_nhan: "Tên nhãn sẽ gắn, ví dụ: Đang tư vấn",
    chuyen_nhan_vien: "Lý do/ghi chú chuyển (có thể để trống)",
    tam_dung_bot: "Để trống",
  };

  return (
    <div className="p-4 sm:p-6">
      <TieuDeTrang tieuDe="Quy tắc tự động hóa" moTa="Quy tắc được xét theo thứ tự ưu tiên tăng dần khi có tin nhắn đến. Mọi lần chạy đều ghi lại để kiểm tra.">
        <Nut onClick={moThem}><i className="fa-solid fa-plus mr-2" />Tạo quy tắc</Nut>
      </TieuDeTrang>
      {thongBao && <ThongBao loai={thongBao.loai}>{thongBao.text}</ThongBao>}

      {dangTai ? <DangTai /> : loi ? <LoiTai loi={loi} onThuLai={tai} /> : ds.length === 0 ? (
        <ChuaCoDuLieu text="Chưa có quy tắc nào. Nếu không có quy tắc khớp, hệ thống mặc định gọi AI theo kho tri thức và bộ nhớ." />
      ) : (
        <div className="space-y-3">
          {ds.map((r) => (
            <section key={r.id} className={`bg-white dark:bg-neutral-900 rounded shadow p-4 ${!r.is_active ? "opacity-60" : ""}`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-bold flex flex-wrap items-center gap-2">
                    {r.name}
                    <span className="text-xs bg-gray-100 dark:bg-neutral-800 px-2 py-0.5 rounded-full">Ưu tiên {r.priority}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${r.is_active ? "bg-green-100 text-green-800" : "bg-gray-200 text-gray-700"}`}>
                      {r.is_active ? "Đang bật" : "Đã tắt"}
                    </span>
                  </p>
                  {r.description && <p className="text-sm text-gray-500 mt-0.5">{r.description}</p>}
                  <p className="text-sm mt-2">
                    Khi <b>{NHAN_DIEU_KIEN[r.condition_type] || r.condition_type}</b>
                    {r.condition_value && <>: <code className="bg-gray-100 dark:bg-neutral-800 px-1.5 py-0.5 rounded">{r.condition_value}</code></>}
                    {" → "}<b>{NHAN_HANH_DONG[r.action_type] || r.action_type}</b>
                    {r.action_value && <>: <span className="text-gray-600 dark:text-gray-300">{r.action_value}</span></>}
                  </p>
                  <p className="text-xs text-gray-400 mt-1.5">
                    Đã chạy {r.so_lan_chay ?? 0} lần
                    {r.lan_chay_gan_nhat
                      ? <> · Lần gần nhất: {dinhDangThoiGian(r.lan_chay_gan_nhat.created_at)} — {r.lan_chay_gan_nhat.result}</>
                      : " · Chưa từng chạy"}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 shrink-0">
                  <Nut mau="xam" onClick={() => xemLanChay(r)}>{lanChayMo === r.id ? "Đóng lịch sử" : "Lịch sử chạy"}</Nut>
                  <Nut mau="xam" onClick={() => doiTrangThai(r)}>{r.is_active ? "Tắt quy tắc" : "Bật quy tắc"}</Nut>
                  <Nut mau="xam" onClick={() => moSua(r)}>Sửa</Nut>
                  <Nut mau="do" onClick={() => setXoaId(r.id)}>Xóa</Nut>
                </div>
              </div>
              {lanChayMo === r.id && (
                <div className="mt-3 border-t pt-3">
                  {dangTaiLanChay ? <p className="text-sm text-gray-500">Đang tải lịch sử chạy...</p>
                    : dsLanChay.length === 0 ? <p className="text-sm text-gray-500">Quy tắc này chưa từng chạy.</p>
                    : (
                      <ul className="text-sm space-y-1.5">
                        {dsLanChay.map((x) => (
                          <li key={x.id} className="flex flex-wrap gap-2">
                            <span className="text-gray-400">{dinhDangThoiGian(x.created_at)}</span>
                            <span>Kết quả: {x.result || "—"}</span>
                            {x.conversation_id && <span className="text-gray-400">· Hội thoại #{x.conversation_id}</span>}
                          </li>
                        ))}
                      </ul>
                    )}
                </div>
              )}
            </section>
          ))}
        </div>
      )}

      <HopBieuMau mo={moForm} tieuDe={dangSua ? "Sửa quy tắc" : "Tạo quy tắc tự động hóa"} onDong={() => setMoForm(false)} rong="max-w-xl">
        <form onSubmit={luu}>
          <Truong nhan="Tên quy tắc" batBuoc>
            <input className={oNhap} value={form.name} onChange={dat("name")} required placeholder="Ví dụ: Khách muốn gặp nhân viên thì chuyển người" />
          </Truong>
          <Truong nhan="Mô tả">
            <input className={oNhap} value={form.description} onChange={dat("description")} placeholder="Mục đích của quy tắc (không bắt buộc)" />
          </Truong>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Truong nhan="Loại điều kiện">
              <select className={oNhap} value={form.condition_type} onChange={dat("condition_type")}>
                {Object.entries(NHAN_DIEU_KIEN).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </Truong>
            <Truong nhan="Giá trị điều kiện" batBuoc>
              <input className={oNhap} value={form.condition_value} onChange={dat("condition_value")} required
                placeholder={form.condition_type === "intent" ? "Ví dụ: gap_nhan_vien" : form.condition_type === "nhan" ? "Ví dụ: Khách ưu tiên" : "Ví dụ: xin chào"} />
            </Truong>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Truong nhan="Hành động">
              <select className={oNhap} value={form.action_type} onChange={dat("action_type")}>
                {Object.entries(NHAN_HANH_DONG).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </Truong>
            <Truong nhan="Mức ưu tiên (số nhỏ chạy trước)">
              <input className={oNhap} type="number" value={form.priority} onChange={dat("priority")} />
            </Truong>
          </div>
          <Truong nhan="Giá trị hành động">
            <textarea className={oNhap} rows={2} value={form.action_value} onChange={dat("action_value")}
              placeholder={goiYGiaTriHanhDong[form.action_type] || ""} />
          </Truong>
          <label className="flex items-center gap-2 text-sm mb-4">
            <input type="checkbox" checked={form.is_active} onChange={dat("is_active")} /> Bật quy tắc ngay sau khi lưu
          </label>
          <div className="flex justify-end gap-2">
            <Nut mau="xam" onClick={() => setMoForm(false)}>Hủy bỏ</Nut>
            <Nut type="submit" disabled={dangLuu}>{dangLuu ? "Đang lưu..." : "Lưu quy tắc"}</Nut>
          </div>
        </form>
      </HopBieuMau>

      <HopXacNhan
        mo={xoaId !== null}
        tieuDe="Xóa quy tắc?"
        noiDung="Quy tắc bị xóa sẽ không còn được áp dụng cho tin nhắn mới. Lịch sử lần chạy đã ghi vẫn được giữ để truy vết. Thao tác yêu cầu quyền quản trị viên."
        nhanNut="Xóa quy tắc"
        dangXuLy={dangXoa}
        onDong={() => setXoaId(null)}
        onXacNhan={xoa}
      />
    </div>
  );
}
