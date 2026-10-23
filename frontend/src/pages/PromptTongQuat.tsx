import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import { DangTai, LoiTai, Nut, ThongBao, TieuDeTrang, oNhap } from "../components/dungChung";
import { useToast } from "../components/Toast";

// Trang PROMPT TỔNG QUÁT:
// - Cột trái: sửa toàn văn khóa cài đặt `prompt_tong_quat`. Khi có nội dung,
//   đoạn này THAY phần lõi mặc định (danh tính + phong cách) trong prompt hệ
//   thống; các phần dữ liệu động (doanh nghiệp, dịch vụ, hồ sơ khách, tri
//   thức/bộ nhớ, hướng dẫn bổ sung) vẫn tự chắp phía sau như cũ.
// - Cột phải: xem trước TOÀN VĂN prompt đã ghép bằng GET
//   /api/cai-dat/xem-prompt-tong-quat (dữ liệu mẫu ghi rõ [DỮ LIỆU MẪU]).
// Lưu qua PUT /api/cai-dat hiện có — hiệu lực ngay, không cần khởi động lại.

type PhanPrompt = { ten: string; noi_dung: string; nguon: "co_dinh" | "cai_dat" | "du_lieu_dong" };

const NHAN_NGUON: Record<string, { nhan: string; lop: string }> = {
  co_dinh: { nhan: "Cố định trong hệ thống", lop: "bg-gray-200 text-gray-700 dark:bg-neutral-700 dark:text-gray-200" },
  cai_dat: { nhan: "Từ Cài đặt", lop: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200" },
  du_lieu_dong: { nhan: "Dữ liệu động", lop: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200" },
};

export default function PromptTongQuat() {
  const toast = useToast();
  const [noiDung, setNoiDung] = useState("");
  const [banDaLuu, setBanDaLuu] = useState("");
  const [cacPhan, setCacPhan] = useState<PhanPrompt[]>([]);
  const [toanVan, setToanVan] = useState("");
  const [dangTai, setDangTai] = useState(true);
  const [loi, setLoi] = useState("");
  const [dangLuu, setDangLuu] = useState(false);
  const [dangTaiLaiGhep, setDangTaiLaiGhep] = useState(false);
  const [thongBao, setThongBao] = useState<{ loai: "thanh_cong" | "loi"; text: string } | null>(null);

  const taiBanGhep = useCallback(async () => {
    const kq = await api("/api/cai-dat/xem-prompt-tong-quat");
    setCacPhan(kq.cac_phan || []);
    setToanVan(kq.toan_van || "");
  }, []);

  const taiDuLieu = useCallback(async () => {
    setDangTai(true);
    setLoi("");
    try {
      const [cd] = await Promise.all([api("/api/cai-dat"), taiBanGhep()]);
      const gt = String(cd?.prompt_tong_quat || "");
      setNoiDung(gt);
      setBanDaLuu(gt);
    } catch (e: any) {
      setLoi(e.message);
    } finally {
      setDangTai(false);
    }
  }, [taiBanGhep]);

  useEffect(() => { taiDuLieu(); }, [taiDuLieu]);

  const luu = async (giaTri: string, thongDiep: string) => {
    setDangLuu(true);
    setThongBao(null);
    try {
      await api("/api/cai-dat", { method: "PUT", body: JSON.stringify({ prompt_tong_quat: giaTri }) });
      setNoiDung(giaTri);
      setBanDaLuu(giaTri);
      await taiBanGhep();
      toast.thanhCong(thongDiep);
      setThongBao({ loai: "thanh_cong", text: thongDiep });
    } catch (e: any) {
      toast.loi(e.message);
      setThongBao({ loai: "loi", text: `Lưu thất bại: ${e.message}` });
    } finally {
      setDangLuu(false);
    }
  };

  const taiLaiBanGhep = async () => {
    setDangTaiLaiGhep(true);
    try {
      await taiBanGhep();
      toast.thanhCong("Đã tải lại bản ghép prompt theo cài đặt hiện tại.");
    } catch (e: any) {
      toast.loi(e.message);
    } finally {
      setDangTaiLaiGhep(false);
    }
  };

  const saoChep = async () => {
    try {
      await navigator.clipboard.writeText(toanVan);
      toast.thanhCong("Đã sao chép toàn văn prompt đã ghép.");
    } catch {
      toast.loi("Trình duyệt không cho sao chép tự động — hãy bôi đen khung bên phải và sao chép thủ công.");
    }
  };

  const chuaLuu = noiDung !== banDaLuu;
  const dangDungMacDinh = !banDaLuu.trim();

  return (
    <div className="p-4 sm:p-6">
      <TieuDeTrang
        tieuDe="Prompt tổng quát"
        moTa="Toàn văn phần lõi của prompt hệ thống mà bot dùng khi trả lời khách — xem, sửa và kiểm tra bản ghép tại một chỗ.">
        <Nut mau="xam" onClick={taiDuLieu}><i className="fa-solid fa-rotate mr-2" />Làm mới</Nut>
      </TieuDeTrang>
      {thongBao && <ThongBao loai={thongBao.loai}>{thongBao.text}</ThongBao>}
      {dangTai ? (
        <DangTai text="Đang tải prompt..." />
      ) : loi ? (
        <LoiTai loi={loi} onThuLai={taiDuLieu} />
      ) : (
        <div className="grid lg:grid-cols-2 gap-4 items-start">
          {/* Cột trái — ô sửa prompt_tong_quat toàn văn */}
          <section className="bg-white dark:bg-neutral-900 rounded shadow p-4 space-y-3">
            <h3 className="font-bold flex items-center gap-2">
              <i className="fa-solid fa-pen-to-square text-thuongHieu-600" />
              Prompt tổng quát (phần lõi — do bạn đặt)
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              <b>Cơ chế:</b> khi ô này <b>có nội dung</b>, đoạn đó <b>THAY</b> phần lõi mặc định của bot
              (danh tính + xưng hô + giọng điệu + luật chống một motip + khóa danh tính). Các phần dữ liệu
              động vẫn tự chắp phía sau như cũ: thông tin doanh nghiệp, danh sách dịch vụ PR, hồ sơ khách,
              ngữ cảnh tri thức/bộ nhớ và Hướng dẫn bổ sung. Khi <b>để trống</b>: bot dùng phần lõi mặc
              định của hệ thống như trước.
            </p>
            <textarea
              className={`${oNhap} w-full font-mono text-[13px] leading-relaxed resize-y`}
              rows={18}
              placeholder={"Để trống = dùng phần lõi mặc định của hệ thống.\n\nVí dụ khi muốn tự đặt lõi:\nBạn là Mai — nhân viên tư vấn của shop Hải sản Bà Thi...\nXưng 'em', gọi khách là 'anh/chị'...\nLuôn tư vấn ngắn gọn, ưu tiên giới thiệu hải sản tươi..."}
              value={noiDung}
              onChange={(e) => setNoiDung(e.target.value)}
            />
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => luu(noiDung, "Đã lưu Prompt tổng quát — hiệu lực ngay cho các lượt trả lời tiếp theo.")}
                disabled={dangLuu || !chuaLuu}
                className="bg-thuongHieu-600 hover:bg-thuongHieu-700 text-white font-semibold px-5 py-2.5 rounded-lg shadow disabled:opacity-50 disabled:cursor-not-allowed">
                <i className="fa-solid fa-floppy-disk mr-2" />
                {dangLuu ? "Đang lưu..." : "Lưu Prompt tổng quát"}
              </button>
              <Nut mau="xam" disabled={dangLuu || dangDungMacDinh}
                onClick={() => luu("", "Đã xóa Prompt tổng quát — bot quay về phần lõi mặc định của hệ thống.")}>
                <i className="fa-solid fa-eraser mr-2" />Xóa để về mặc định
              </Nut>
              {chuaLuu && <span className="text-sm text-amber-600 font-medium">Có thay đổi chưa lưu</span>}
              {!chuaLuu && (
                <span className="text-sm text-gray-500">
                  Trạng thái hiện tại: {dangDungMacDinh
                    ? "đang dùng phần lõi MẶC ĐỊNH của hệ thống"
                    : "đang dùng prompt lõi TỰ ĐẶT"}
                </span>
              )}
            </div>
            <p className="text-xs text-gray-500">
              Lưu qua Cài đặt hệ thống (khóa <code>prompt_tong_quat</code>) — hiệu lực ngay ở lượt trả lời
              tiếp theo, không cần khởi động lại. Persona của Chế độ trò chuyện tự do là một ô riêng trong
              Cài đặt, không bị ảnh hưởng bởi ô này.
            </p>
          </section>

          {/* Cột phải — bản xem trước toàn văn prompt đã ghép */}
          <section className="bg-white dark:bg-neutral-900 rounded shadow p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-bold flex items-center gap-2">
                <i className="fa-solid fa-file-lines text-thuongHieu-600" />
                Bản ghép toàn văn (xem trước)
              </h3>
              <div className="flex gap-2">
                <Nut mau="xam" onClick={taiLaiBanGhep} disabled={dangTaiLaiGhep}>
                  <i className="fa-solid fa-rotate mr-2" />{dangTaiLaiGhep ? "Đang tải..." : "Tải lại bản ghép"}
                </Nut>
                <Nut mau="xam" onClick={saoChep} disabled={!toanVan}>
                  <i className="fa-solid fa-copy mr-2" />Sao chép
                </Nut>
              </div>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              Đây là prompt hệ thống bot thật sự gửi cho AI, ghép từ cài đặt hiện tại. Các phần phụ thuộc
              từng khách/từng câu hỏi dùng dữ liệu mẫu ghi rõ <b>[DỮ LIỆU MẪU]</b>; danh sách dịch vụ dùng
              dịch vụ thật đang mở bán (nếu có).
            </p>
            <div className="space-y-1.5">
              {cacPhan.map((p, i) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <span className="text-gray-400 font-mono text-xs">{i + 1}.</span>
                  <span className="flex-1 truncate">{p.ten}</span>
                  <span className={`text-[11px] px-2 py-0.5 rounded-full ${NHAN_NGUON[p.nguon]?.lop || ""}`}>
                    {NHAN_NGUON[p.nguon]?.nhan || p.nguon}
                  </span>
                </div>
              ))}
            </div>
            <pre className="w-full max-h-[520px] overflow-auto whitespace-pre-wrap break-words bg-gray-50 dark:bg-neutral-950 border dark:border-neutral-800 rounded-lg p-3 text-[13px] leading-relaxed">
              {toanVan || "(chưa có nội dung)"}
            </pre>
          </section>
        </div>
      )}
    </div>
  );
}
