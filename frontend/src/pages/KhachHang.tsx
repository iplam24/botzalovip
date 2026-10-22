import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, dinhDangThoiGian } from "../lib/api";
import {
  ChuaCoDuLieu, DangTai, HopBieuMau, HopXacNhan, LoiTai, Nut, ThongBao, TieuDeTrang, Truong, oNhap,
} from "../components/dungChung";

// Quản lý khách hàng: bảng + tìm kiếm + form thêm/sửa đầy đủ + xóa có xác nhận (chỉ quản trị viên xóa được ở backend).
const FORM_TRONG = { display_name: "", phone: "", labels: "", group_name: "", notes: "", assignee: "", external_id: "" };

export default function KhachHang() {
  const [ds, setDs] = useState<any[]>([]);
  const [dangTai, setDangTai] = useState(true);
  const [loi, setLoi] = useState("");
  const [tuKhoa, setTuKhoa] = useState("");
  const [moForm, setMoForm] = useState(false);
  const [dangSua, setDangSua] = useState<any | null>(null);
  const [form, setForm] = useState({ ...FORM_TRONG });
  const [dangLuu, setDangLuu] = useState(false);
  const [xoaId, setXoaId] = useState<number | null>(null);
  const [dangXoa, setDangXoa] = useState(false);
  const [thongBao, setThongBao] = useState<{ loai: "thanh_cong" | "loi"; text: string } | null>(null);

  const tai = useCallback(async () => {
    setDangTai(true);
    setLoi("");
    try {
      const thamSo = tuKhoa.trim() ? `?tu_khoa=${encodeURIComponent(tuKhoa.trim())}` : "";
      setDs(await api(`/api/khach-hang${thamSo}`));
    } catch (e: any) {
      setLoi(e.message);
    } finally {
      setDangTai(false);
    }
  }, [tuKhoa]);

  useEffect(() => {
    const t = setTimeout(tai, tuKhoa ? 350 : 0);
    return () => clearTimeout(t);
  }, [tai, tuKhoa]);

  const moThem = () => { setDangSua(null); setForm({ ...FORM_TRONG }); setMoForm(true); };
  const moSua = (c: any) => {
    setDangSua(c);
    setForm({
      display_name: c.display_name || "", phone: c.phone || "", labels: c.labels || "",
      group_name: c.group_name || "", notes: c.notes || "", assignee: c.assignee || "",
      external_id: c.external_id || "",
    });
    setMoForm(true);
  };

  const luu = async (e: FormEvent) => {
    e.preventDefault();
    setDangLuu(true);
    try {
      if (dangSua) {
        await api(`/api/khach-hang/${dangSua.id}`, { method: "PUT", body: JSON.stringify(form) });
        setThongBao({ loai: "thanh_cong", text: `Đã cập nhật khách hàng “${form.display_name}”.` });
      } else {
        await api("/api/khach-hang", {
          method: "POST",
          body: JSON.stringify({ ...form, external_id: form.external_id || null }),
        });
        setThongBao({ loai: "thanh_cong", text: `Đã thêm khách hàng “${form.display_name}”.` });
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
      await api(`/api/khach-hang/${xoaId}`, { method: "DELETE" });
      setThongBao({ loai: "thanh_cong", text: "Đã xóa khách hàng." });
      setXoaId(null);
      await tai();
    } catch (e: any) {
      setThongBao({ loai: "loi", text: e.message });
      setXoaId(null);
    } finally {
      setDangXoa(false);
    }
  };

  const dat = (k: string) => (e: any) => setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <div className="p-6">
      <TieuDeTrang tieuDe="Khách hàng" moTa="Hồ sơ khách hàng thống nhất từ mọi kênh hội thoại. Không tự suy đoán thuộc tính nhạy cảm.">
        <Nut onClick={moThem}>+ Thêm khách hàng</Nut>
      </TieuDeTrang>
      {thongBao && <ThongBao loai={thongBao.loai}>{thongBao.text}</ThongBao>}

      <div className="bg-white dark:bg-neutral-900 rounded shadow">
        <div className="p-3 border-b flex gap-2">
          <input className={oNhap} placeholder="Tìm theo tên, số điện thoại hoặc ghi chú..."
            value={tuKhoa} onChange={(e) => setTuKhoa(e.target.value)} />
          <Nut mau="xam" onClick={tai}>Tìm kiếm</Nut>
        </div>
        {dangTai ? <DangTai /> : loi ? <LoiTai loi={loi} onThuLai={tai} /> : ds.length === 0 ? (
          <div className="p-4"><ChuaCoDuLieu text="Chưa có khách hàng nào. Khách hàng tự được tạo khi có tin nhắn đến, hoặc bấm “Thêm khách hàng” để nhập tay." /></div>
        ) : (
          <div className="overflow-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left bg-gray-50 dark:bg-neutral-800">
                  <th className="p-3 border-b">Tên hiển thị</th>
                  <th className="p-3 border-b">Số điện thoại</th>
                  <th className="p-3 border-b">Nhãn</th>
                  <th className="p-3 border-b">Nhóm</th>
                  <th className="p-3 border-b">Người phụ trách</th>
                  <th className="p-3 border-b">Tương tác gần nhất</th>
                  <th className="p-3 border-b">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {ds.map((c) => (
                  <tr key={c.id} className="hover:bg-gray-50 dark:hover:bg-neutral-800">
                    <td className="p-3 border-b font-medium">{c.display_name || `(chưa có tên) #${c.id}`}</td>
                    <td className="p-3 border-b">{c.phone || "—"}</td>
                    <td className="p-3 border-b">
                      {(c.labels || "").split(",").map((s: string) => s.trim()).filter(Boolean).map((nhan: string) => (
                        <span key={nhan} className="inline-block bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full text-xs mr-1">{nhan}</span>
                      ))}
                      {!c.labels && "—"}
                    </td>
                    <td className="p-3 border-b">{c.group_name || "—"}</td>
                    <td className="p-3 border-b">{c.assignee || "—"}</td>
                    <td className="p-3 border-b whitespace-nowrap">{dinhDangThoiGian(c.last_interaction_at)}</td>
                    <td className="p-3 border-b whitespace-nowrap">
                      <button className="text-blue-600 hover:underline mr-3" onClick={() => moSua(c)}>Sửa</button>
                      <button className="text-red-600 hover:underline" onClick={() => setXoaId(c.id)}>Xóa</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <HopBieuMau mo={moForm} tieuDe={dangSua ? "Sửa khách hàng" : "Thêm khách hàng"} onDong={() => setMoForm(false)} rong="max-w-xl">
        <form onSubmit={luu}>
          <Truong nhan="Tên hiển thị" batBuoc>
            <input className={oNhap} value={form.display_name} onChange={dat("display_name")} required placeholder="Ví dụ: Nguyễn Văn A" />
          </Truong>
          <div className="grid grid-cols-2 gap-3">
            <Truong nhan="Số điện thoại">
              <input className={oNhap} value={form.phone} onChange={dat("phone")} placeholder="09xx xxx xxx" />
            </Truong>
            <Truong nhan="Định danh từ Zalo (nếu có)">
              <input className={oNhap} value={form.external_id} onChange={dat("external_id")} placeholder="Mã người dùng Zalo" />
            </Truong>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Truong nhan="Nhãn (phân cách bằng dấu phẩy)">
              <input className={oNhap} value={form.labels} onChange={dat("labels")} placeholder="Khách mới, Đang tư vấn" />
            </Truong>
            <Truong nhan="Nhóm khách hàng">
              <input className={oNhap} value={form.group_name} onChange={dat("group_name")} placeholder="Ví dụ: Khách lẻ" />
            </Truong>
          </div>
          <Truong nhan="Người phụ trách">
            <input className={oNhap} value={form.assignee} onChange={dat("assignee")} placeholder="Tên nhân viên" />
          </Truong>
          <Truong nhan="Ghi chú nội bộ">
            <textarea className={oNhap} rows={3} value={form.notes} onChange={dat("notes")} placeholder="Chỉ ghi thông tin cần cho nghiệp vụ chăm sóc" />
          </Truong>
          <div className="flex justify-end gap-2 mt-4">
            <Nut mau="xam" onClick={() => setMoForm(false)}>Hủy bỏ</Nut>
            <Nut type="submit" disabled={dangLuu}>{dangLuu ? "Đang lưu..." : "Lưu khách hàng"}</Nut>
          </div>
        </form>
      </HopBieuMau>

      <HopXacNhan
        mo={xoaId !== null}
        tieuDe="Xóa khách hàng?"
        noiDung="Hành động này xóa hồ sơ khách hàng khỏi cơ sở dữ liệu và không khôi phục được từ giao diện. Thao tác xóa yêu cầu quyền quản trị viên."
        nhanNut="Xóa khách hàng"
        dangXuLy={dangXoa}
        onDong={() => setXoaId(null)}
        onXacNhan={xoa}
      />
    </div>
  );
}
