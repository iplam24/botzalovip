import { useCallback, useEffect, useState } from "react";
import { api, dinhDangSo, dinhDangThoiGian } from "../lib/api";
import {
  ChuaCoDuLieu, DangTai, HopXacNhan, HuyHieuTrangThai, LoiTai, Nut, ThongBao, TieuDeTrang,
} from "../components/dungChung";

// Sao lưu và khôi phục: tạo bản ZIP (khóa API đã redact phía backend),
// khôi phục bắt buộc xác nhận, xóa bản sao lưu có xác nhận. Cần quyền quản trị viên.
export default function SaoLuu() {
  const [ds, setDs] = useState<any[]>([]);
  const [dangTai, setDangTai] = useState(true);
  const [loi, setLoi] = useState("");
  const [dangTao, setDangTao] = useState(false);
  const [khoiPhucId, setKhoiPhucId] = useState<number | null>(null);
  const [dangKhoiPhuc, setDangKhoiPhuc] = useState(false);
  const [xoaId, setXoaId] = useState<number | null>(null);
  const [dangXoa, setDangXoa] = useState(false);
  const [thongBao, setThongBao] = useState<{ loai: "thanh_cong" | "loi" | "thong_tin"; text: string } | null>(null);

  const tai = useCallback(async () => {
    setDangTai(true);
    setLoi("");
    try {
      setDs(await api("/api/sao-luu"));
    } catch (e: any) {
      setLoi(e.message);
    } finally {
      setDangTai(false);
    }
  }, []);

  useEffect(() => { tai(); }, [tai]);

  const taoMoi = async () => {
    setDangTao(true);
    try {
      const kq = await api("/api/sao-luu", { method: "POST" });
      setThongBao({ loai: "thanh_cong", text: `Đã tạo bản sao lưu ${kq.filename} (${dinhDangSo(kq.size)} byte).` });
      await tai();
    } catch (e: any) {
      setThongBao({ loai: "loi", text: `Tạo sao lưu thất bại: ${e.message}` });
    } finally {
      setDangTao(false);
    }
  };

  const khoiPhuc = async () => {
    if (khoiPhucId === null) return;
    setDangKhoiPhuc(true);
    try {
      const kq = await api(`/api/sao-luu/${khoiPhucId}/khoi-phuc`, {
        method: "POST",
        body: JSON.stringify({ xac_nhan: true }),
      });
      const chiTiet = kq.chi_tiet
        ? Object.entries(kq.chi_tiet).map(([k, v]) => `${k}: ${v}`).join(", ")
        : "";
      setThongBao({
        loai: "thanh_cong",
        text: `Khôi phục hoàn tất. Bản ghi được bổ sung — ${chiTiet}. Lưu ý: khóa API trong bản sao lưu đã bị redact nên cần cấu hình lại khóa sau khôi phục.`,
      });
      setKhoiPhucId(null);
    } catch (e: any) {
      setThongBao({ loai: "loi", text: `Khôi phục thất bại: ${e.message}` });
      setKhoiPhucId(null);
    } finally {
      setDangKhoiPhuc(false);
    }
  };

  const xoa = async () => {
    if (xoaId === null) return;
    setDangXoa(true);
    try {
      await api(`/api/sao-luu/${xoaId}`, { method: "DELETE" });
      setThongBao({ loai: "thanh_cong", text: "Đã xóa bản sao lưu (cả file trên máy chủ)." });
      setXoaId(null);
      await tai();
    } catch (e: any) {
      setThongBao({ loai: "loi", text: e.message });
      setXoaId(null);
    } finally {
      setDangXoa(false);
    }
  };

  return (
    <div className="p-4 sm:p-6">
      <TieuDeTrang tieuDe="Sao lưu và khôi phục" moTa="Bản sao lưu dạng ZIP chứa dữ liệu JSON. Khóa API được redact trước khi ghi vào file — sau khôi phục phải cấu hình lại khóa API.">
        <Nut onClick={taoMoi} disabled={dangTao}><i className="fa-solid fa-database mr-2" />{dangTao ? "Đang tạo..." : "Tạo sao lưu ngay"}</Nut>
      </TieuDeTrang>
      {thongBao && <ThongBao loai={thongBao.loai}>{thongBao.text}</ThongBao>}

      {dangTai ? <DangTai /> : loi ? <LoiTai loi={loi} onThuLai={tai} /> : ds.length === 0 ? (
        <ChuaCoDuLieu text="Chưa có bản sao lưu nào. Hãy tạo bản sao lưu đầu tiên trước khi thay đổi cấu hình quan trọng." />
      ) : (
        <div className="bg-white dark:bg-neutral-900 rounded shadow overflow-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left bg-gray-50 dark:bg-neutral-800">
                <th className="p-3 border-b">Tên file</th>
                <th className="p-3 border-b">Kích thước</th>
                <th className="p-3 border-b">Trạng thái</th>
                <th className="p-3 border-b">Thời điểm tạo</th>
                <th className="p-3 border-b">Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {ds.map((b) => (
                <tr key={b.id} className="hover:bg-gray-50 dark:hover:bg-neutral-800">
                  <td className="p-3 border-b font-medium"><code>{b.filename}</code></td>
                  <td className="p-3 border-b">{dinhDangSo(b.size)} byte</td>
                  <td className="p-3 border-b"><HuyHieuTrangThai giaTri={b.status} /></td>
                  <td className="p-3 border-b whitespace-nowrap">{dinhDangThoiGian(b.created_at)}</td>
                  <td className="p-3 border-b whitespace-nowrap">
                    <button className="text-blue-600 hover:underline mr-3" onClick={() => setKhoiPhucId(b.id)}>Khôi phục</button>
                    <button className="text-red-600 hover:underline" onClick={() => setXoaId(b.id)}>Xóa</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-xs text-gray-400 mt-3">
        Lịch sao lưu tự động định kỳ đang phát triển — hiện tại hãy tạo sao lưu thủ công tại trang này.
        Thao tác tạo/khôi phục/xóa yêu cầu quyền quản trị viên.
      </p>

      <HopXacNhan
        mo={khoiPhucId !== null}
        tieuDe="Khôi phục từ bản sao lưu?"
        noiDung={"Dữ liệu trong bản sao lưu sẽ được bổ sung vào hệ thống hiện tại (bản ghi đã tồn tại theo mã sẽ không bị ghi đè ở bản MVP).\n\nKhóa API trong bản sao lưu đã bị redact — sau khôi phục, hãy vào Nhà cung cấp AI để nhập lại khóa.\n\nBạn có chắc chắn muốn khôi phục?"}
        nhanNut="Khôi phục ngay"
        dangXuLy={dangKhoiPhuc}
        onDong={() => setKhoiPhucId(null)}
        onXacNhan={khoiPhuc}
      />
      <HopXacNhan
        mo={xoaId !== null}
        tieuDe="Xóa bản sao lưu?"
        noiDung="File sao lưu trên máy chủ và bản ghi của nó sẽ bị xóa vĩnh viễn. Hãy chắc chắn bạn còn bản sao lưu khác nếu cần khôi phục sau này."
        nhanNut="Xóa bản sao lưu"
        dangXuLy={dangXoa}
        onDong={() => setXoaId(null)}
        onXacNhan={xoa}
      />
    </div>
  );
}
