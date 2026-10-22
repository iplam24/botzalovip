import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, apiTaiFile, dinhDangThoiGian, taiBlobXuong } from "../lib/api";
import {
  ChuaCoDuLieu, DangTai, HopBieuMau, HopXacNhan, LoiTai, Nut, ThongBao, TieuDeTrang, Truong, oNhap,
} from "../components/dungChung";

// Nhãn tiếng Việt cho các trường thông tin thu thập tự động (GĐ mở rộng 1)
const NHAN_TRUONG_THU_THAP: Record<string, string> = {
  ho_ten: "Họ tên",
  so_dien_thoai: "Số điện thoại",
  email: "Email",
  nhu_cau: "Nhu cầu",
  dich_vu_quan_tam: "Dịch vụ quan tâm",
  ngan_sach: "Ngân sách",
  thoi_gian_mong_muon: "Thời gian mong muốn",
  dia_chi: "Địa chỉ",
  ghi_chu: "Ghi chú",
};

// Panel thông tin thu thập của 1 khách: bot tự bóc tách từ hội thoại,
// nhân viên xem/sửa/xác minh/thêm tay/xóa được.
function BangThongTinThuThap({ khach, baoLoi }: { khach: any; baoLoi: (text: string) => void }) {
  const [ds, setDs] = useState<any[]>([]);
  const [dangTai, setDangTai] = useState(true);
  const [truongMoi, setTruongMoi] = useState("nhu_cau");
  const [giaTriMoi, setGiaTriMoi] = useState("");
  const [suaId, setSuaId] = useState<number | null>(null);
  const [giaTriSua, setGiaTriSua] = useState("");

  const tai = useCallback(async () => {
    setDangTai(true);
    try {
      setDs(await api(`/api/khach-hang/${khach.id}/thong-tin-thu-thap`));
    } catch (e: any) {
      baoLoi(e.message);
    } finally {
      setDangTai(false);
    }
  }, [khach.id, baoLoi]);

  useEffect(() => { tai(); }, [tai]);

  const them = async () => {
    if (!giaTriMoi.trim()) return;
    try {
      await api(`/api/khach-hang/${khach.id}/thong-tin-thu-thap`, {
        method: "POST",
        body: JSON.stringify({ field: truongMoi, value: giaTriMoi.trim() }),
      });
      setGiaTriMoi("");
      await tai();
    } catch (e: any) {
      baoLoi(e.message);
    }
  };

  const xacMinh = async (t: any) => {
    try {
      await api(`/api/khach-hang/${khach.id}/thong-tin-thu-thap/${t.id}`, {
        method: "PUT",
        body: JSON.stringify({ verified: true }),
      });
      await tai();
    } catch (e: any) {
      baoLoi(e.message);
    }
  };

  const luuSua = async (t: any) => {
    try {
      await api(`/api/khach-hang/${khach.id}/thong-tin-thu-thap/${t.id}`, {
        method: "PUT",
        body: JSON.stringify({ value: giaTriSua }),
      });
      setSuaId(null);
      await tai();
    } catch (e: any) {
      baoLoi(e.message);
    }
  };

  const xoa = async (t: any) => {
    try {
      await api(`/api/khach-hang/${khach.id}/thong-tin-thu-thap/${t.id}`, { method: "DELETE" });
      await tai();
    } catch (e: any) {
      baoLoi(e.message);
    }
  };

  if (dangTai) return <DangTai text="Đang tải thông tin thu thập..." />;
  return (
    <div>
      {ds.length === 0 ? (
        <p className="text-sm text-gray-500 mb-3">
          Chưa thu thập được thông tin nào. Bot sẽ tự bóc tách số điện thoại, email, nhu cầu... từ các tin nhắn tiếp theo của khách.
        </p>
      ) : (
        <table className="min-w-full text-sm mb-3">
          <thead>
            <tr className="text-left bg-gray-50 dark:bg-neutral-800">
              <th className="p-2 border-b">Trường</th>
              <th className="p-2 border-b">Giá trị</th>
              <th className="p-2 border-b">Độ tin cậy</th>
              <th className="p-2 border-b">Trạng thái</th>
              <th className="p-2 border-b">Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {ds.map((t) => (
              <tr key={t.id} className="hover:bg-gray-50 dark:hover:bg-neutral-800">
                <td className="p-2 border-b font-medium whitespace-nowrap">{NHAN_TRUONG_THU_THAP[t.field] || t.field}</td>
                <td className="p-2 border-b">
                  {suaId === t.id ? (
                    <input className={oNhap} value={giaTriSua} onChange={(e) => setGiaTriSua(e.target.value)} autoFocus />
                  ) : (
                    <>
                      {t.value}
                      <span className="block text-xs text-gray-400">
                        {t.source_message_id ? `Từ tin nhắn #${t.source_message_id}` : "Nhập tay"} · {dinhDangThoiGian(t.created_at)}
                      </span>
                    </>
                  )}
                </td>
                <td className="p-2 border-b whitespace-nowrap">{Math.round((t.confidence ?? 0) * 100)}%</td>
                <td className="p-2 border-b whitespace-nowrap">
                  {t.verified
                    ? <span className="inline-block bg-green-100 text-green-800 px-2 py-0.5 rounded-full text-xs font-medium">Đã xác minh</span>
                    : <span className="inline-block bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full text-xs font-medium">Chưa xác minh</span>}
                </td>
                <td className="p-2 border-b whitespace-nowrap">
                  {suaId === t.id ? (
                    <>
                      <button className="text-blue-600 hover:underline mr-3" onClick={() => luuSua(t)}>Lưu</button>
                      <button className="text-gray-500 hover:underline" onClick={() => setSuaId(null)}>Hủy</button>
                    </>
                  ) : (
                    <>
                      {!t.verified && (
                        <button className="text-green-700 hover:underline mr-3" onClick={() => xacMinh(t)}>Xác minh</button>
                      )}
                      <button className="text-blue-600 hover:underline mr-3" onClick={() => { setSuaId(t.id); setGiaTriSua(t.value); }}>Sửa</button>
                      <button className="text-red-600 hover:underline" onClick={() => xoa(t)}>Xóa</button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="flex gap-2 items-end border-t pt-3">
        <div className="w-44">
          <span className="block text-sm font-medium mb-1">Thêm trường</span>
          <select className={oNhap} value={truongMoi} onChange={(e) => setTruongMoi(e.target.value)}>
            {Object.entries(NHAN_TRUONG_THU_THAP).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>
        <input className={oNhap} placeholder="Giá trị..." value={giaTriMoi}
          onChange={(e) => setGiaTriMoi(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); them(); } }} />
        <Nut onClick={them} disabled={!giaTriMoi.trim()}>Thêm</Nut>
      </div>
    </div>
  );
}

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
  const [dangXuat, setDangXuat] = useState(false);
  const [khachThuThap, setKhachThuThap] = useState<any | null>(null);
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

  const xuatExcel = async () => {
    setDangXuat(true);
    try {
      const thamSo = tuKhoa.trim() ? `?tu_khoa=${encodeURIComponent(tuKhoa.trim())}` : "";
      const { blob, tenFile } = await apiTaiFile(`/api/khach-hang/xuat-excel${thamSo}`);
      taiBlobXuong(blob, tenFile);
      setThongBao({ loai: "thanh_cong", text: "Đã xuất danh sách khách hàng ra Excel (kèm thông tin thu thập chính)." });
    } catch (e: any) {
      setThongBao({ loai: "loi", text: `Xuất Excel thất bại: ${e.message}` });
    } finally {
      setDangXuat(false);
    }
  };

  return (
    <div className="p-6">
      <TieuDeTrang tieuDe="Khách hàng" moTa="Hồ sơ khách hàng thống nhất từ mọi kênh hội thoại. Không tự suy đoán thuộc tính nhạy cảm.">
        <Nut mau="xam" onClick={xuatExcel} disabled={dangXuat}>{dangXuat ? "Đang xuất..." : "Xuất Excel"}</Nut>
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
                      <button className="text-emerald-700 hover:underline mr-3" onClick={() => setKhachThuThap(c)}>Thông tin thu thập</button>
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

      <HopBieuMau
        mo={khachThuThap !== null}
        tieuDe={`Thông tin thu thập — ${khachThuThap?.display_name || (khachThuThap ? `#${khachThuThap.id}` : "")}`}
        onDong={() => setKhachThuThap(null)}
        rong="max-w-3xl"
      >
        {khachThuThap && (
          <BangThongTinThuThap
            khach={khachThuThap}
            baoLoi={(text) => setThongBao({ loai: "loi", text })}
          />
        )}
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
