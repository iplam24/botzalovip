import { useCallback, useEffect, useRef, useState } from "react";
import { api, dinhDangThoiGian } from "../lib/api";
import { DangTai, HuyHieuTrangThai, Nut, ThongBao, TieuDeTrang, oNhap } from "../components/dungChung";

// Tài khoản Zalo — 3 khu vực trung thực về khả năng tích hợp:
// 1) Zalo cá nhân (sidecar zca-js): đăng nhập QR, polling trạng thái mỗi 3 giây.
// 2) Kênh mô phỏng (Mock): nhận tin giả lập để kiểm thử toàn bộ pipeline, ghi rõ là mô phỏng.
// 3) Zalo OA (stub): CHƯA hỗ trợ gọi API thật — cần token OA + app phê duyệt, không fake kết nối.

const NHAN_TRANG_THAI_CA_NHAN: Record<string, string> = {
  cho_quet: "Chờ quét mã QR",
  da_quet_cho_xac_nhan: "Đã quét — chờ xác nhận trên điện thoại",
  da_ket_noi: "Đã kết nối",
  qr_het_han: "Mã QR đã hết hạn",
  mat_ket_noi: "Mất kết nối / Chưa chạy dịch vụ Zalo cá nhân",
  chua_dang_nhap: "Chưa đăng nhập",
  chua_cai_thu_vien: "Chưa cài thư viện zca-js trong dịch vụ phụ",
  loi: "Có lỗi xảy ra",
};

const NHAN_LOAI_TK: Record<string, string> = {
  mock: "Mô phỏng",
  oa: "Zalo OA",
  ca_nhan: "Cá nhân (zca-js)",
};

export default function TaiKhoanZalo() {
  // --- Cá nhân QR ---
  const [tt, setTt] = useState<any>(null);
  const [loiCaNhan, setLoiCaNhan] = useState("");
  const [dangTaoQr, setDangTaoQr] = useState(false);
  const timer = useRef<any>(null);

  const taiTrangThaiCaNhan = useCallback(async () => {
    try {
      setTt(await api("/api/zalo/ca-nhan/trang-thai"));
      setLoiCaNhan("");
    } catch (e: any) {
      setLoiCaNhan(e.message || "Không gọi được backend");
    }
  }, []);

  // Polling mỗi 3 giây: cập nhật QR mới / trạng thái quét / kết nối
  useEffect(() => {
    taiTrangThaiCaNhan();
    timer.current = setInterval(taiTrangThaiCaNhan, 3000);
    return () => clearInterval(timer.current);
  }, [taiTrangThaiCaNhan]);

  const taoQr = async () => {
    setDangTaoQr(true);
    try {
      setTt(await api("/api/zalo/ca-nhan/dang-nhap-qr", { method: "POST" }));
      setTimeout(taiTrangThaiCaNhan, 1200);
    } catch (e: any) {
      setLoiCaNhan(e.message);
    } finally {
      setDangTaoQr(false);
    }
  };

  const ngatCaNhan = async () => {
    try {
      setTt(await api("/api/zalo/ca-nhan/ngat-ket-noi", { method: "POST" }));
    } catch (e: any) {
      setLoiCaNhan(e.message);
    }
  };

  // --- Danh sách tài khoản + kiểm tra connector ---
  const [taiKhoan, setTaiKhoan] = useState<any[]>([]);
  const [kiemTra, setKiemTra] = useState<any>(null);
  const [dangKiemTra, setDangKiemTra] = useState(false);

  const taiTaiKhoan = useCallback(async () => {
    try { setTaiKhoan(await api("/api/zalo/tai-khoan")); } catch { /* giữ danh sách cũ */ }
  }, []);
  useEffect(() => { taiTaiKhoan(); }, [taiTaiKhoan]);

  const chayKiemTra = async () => {
    setDangKiemTra(true);
    try {
      setKiemTra(await api("/api/zalo/kiem-tra-connector", { method: "POST" }));
      await taiTaiKhoan();
    } catch (e: any) {
      setKiemTra({ loi: e.message });
    } finally {
      setDangKiemTra(false);
    }
  };

  // --- Gửi tin mô phỏng để kiểm thử ---
  const [tenKhachMoPhong, setTenKhachMoPhong] = useState("Khách kiểm thử");
  const [tinMoPhong, setTinMoPhong] = useState("");
  const [ketQuaMoPhong, setKetQuaMoPhong] = useState<any>(null);
  const [dangGuiMoPhong, setDangGuiMoPhong] = useState(false);

  const guiMoPhong = async () => {
    if (!tinMoPhong.trim()) return;
    setDangGuiMoPhong(true);
    try {
      const kq = await api("/api/zalo/mock/nhan-tin-nhan", {
        method: "POST",
        body: JSON.stringify({
          external_id: `mo-phong-${Date.now()}`,
          customer_external_id: "khach-kiem-thu-giao-dien",
          customer_name: tenKhachMoPhong || "Khách kiểm thử",
          content: tinMoPhong.trim(),
        }),
      });
      setKetQuaMoPhong(kq);
    } catch (e: any) {
      setKetQuaMoPhong({ loi: e.message });
    } finally {
      setDangGuiMoPhong(false);
    }
  };

  const trangThaiCaNhan = tt?.trang_thai || "mat_ket_noi";
  const nhanCaNhan = NHAN_TRANG_THAI_CA_NHAN[trangThaiCaNhan] || trangThaiCaNhan;
  const qr = tt?.qr_base64 || "";

  return (
    <div className="p-6 space-y-5">
      <TieuDeTrang tieuDe="Tài khoản Zalo" moTa="Quản lý các kênh kết nối Zalo. Mỗi kênh ghi rõ trạng thái thật và giới hạn của nó.">
        <Nut mau="xam" onClick={chayKiemTra} disabled={dangKiemTra}>
          {dangKiemTra ? "Đang kiểm tra..." : "Kiểm tra tất cả connector"}
        </Nut>
      </TieuDeTrang>

      {kiemTra && (
        kiemTra.loi
          ? <ThongBao loai="loi">Kiểm tra connector thất bại: {kiemTra.loi}</ThongBao>
          : <ThongBao loai="thong_tin">
              Kết quả kiểm tra thật — Mô phỏng: <b>{kiemTra.mock?.trang_thai}</b> · Zalo OA: <b>{kiemTra.oa_stub?.trang_thai}</b> ·
              Cá nhân: <b>{NHAN_TRANG_THAI_CA_NHAN[kiemTra.ca_nhan?.trang_thai] || kiemTra.ca_nhan?.trang_thai}</b>.
              {kiemTra.gioi_han && <span className="block mt-1">{kiemTra.gioi_han}</span>}
            </ThongBao>
      )}

      {/* Khu 1: Zalo cá nhân QR */}
      <div className="bg-yellow-50 border border-yellow-300 text-yellow-900 p-4 rounded">
        <p className="font-semibold">⚠️ Cảnh báo về Zalo cá nhân (thư viện zca-js — không chính thức)</p>
        <p className="text-sm mt-1">
          Kết nối tài khoản cá nhân dùng thư viện <b>không chính thức</b>, không phải API do Zalo cung cấp.
          Việc sử dụng có <b>rủi ro bị Zalo hạn chế hoặc khóa tài khoản</b>. Hệ thống <b>không</b> vượt CAPTCHA/OTP,
          không lưu mật khẩu — đăng nhập do chính bạn quét QR và xác nhận trên điện thoại.
          Hãy cân nhắc dùng tài khoản phụ cho mục đích thử nghiệm.
        </p>
      </div>

      <section className="bg-white dark:bg-neutral-900 p-5 rounded shadow">
        <h2 className="font-bold text-lg mb-2">1. Zalo cá nhân — Đăng nhập bằng mã QR</h2>
        <p className="text-sm mb-1">
          Trạng thái: <b>{nhanCaNhan}</b>
          {tt?.qr_updated_at && trangThaiCaNhan === "cho_quet" && (
            <span className="text-gray-500"> · QR tạo lúc {dinhDangThoiGian(tt.qr_updated_at)} (QR hết hạn nhanh — nếu quét không được, hãy tạo QR mới)</span>
          )}
        </p>
        {tt?.thong_bao && <p className="text-sm text-gray-500 mb-3">{tt.thong_bao}</p>}
        {loiCaNhan && (
          <p className="text-sm text-red-600 mb-3">
            Lỗi: {loiCaNhan}. Nếu trạng thái là mất kết nối, hãy khởi động dịch vụ phụ:{" "}
            <code>cd connectors/zalo-personal &amp;&amp; npm install &amp;&amp; npm start</code>
          </p>
        )}

        {!tt ? (
          <DangTai text="Đang kiểm tra trạng thái dịch vụ Zalo cá nhân..." />
        ) : qr && trangThaiCaNhan !== "da_ket_noi" ? (
          <div className="my-3">
            <img src={qr} alt="Mã QR đăng nhập Zalo" className="w-56 h-56 border rounded bg-white" />
            <p className="text-sm text-gray-500 mt-2">Mở ứng dụng Zalo trên điện thoại → Quét mã QR → Xác nhận đăng nhập. Trang này tự cập nhật trạng thái mỗi 3 giây.</p>
          </div>
        ) : trangThaiCaNhan === "da_ket_noi" ? (
          <p className="text-green-700 font-medium my-3">✅ Tài khoản Zalo cá nhân đang kết nối qua dịch vụ phụ. Tin nhắn đến sẽ được chuyển về hệ thống tự động.</p>
        ) : (
          <p className="text-sm text-gray-500 my-3">Chưa có mã QR. Bấm “Tạo QR mới” để bắt đầu đăng nhập.</p>
        )}

        <div className="flex flex-wrap gap-3">
          <Nut onClick={taoQr} disabled={dangTaoQr}>{dangTaoQr ? "Đang tạo QR..." : "Tạo QR mới"}</Nut>
          <Nut mau="do" onClick={ngatCaNhan}>Ngắt kết nối</Nut>
          <Nut mau="xam" onClick={taiTrangThaiCaNhan}>Kiểm tra trạng thái</Nut>
        </div>
      </section>

      {/* Khu 2: Mô phỏng */}
      <section className="bg-white dark:bg-neutral-900 p-5 rounded shadow">
        <h2 className="font-bold text-lg mb-2">2. Kênh mô phỏng (Mock) — dùng để kiểm thử</h2>
        <p className="text-sm text-gray-500 mb-3">
          Đây là môi trường <b>mô phỏng</b>, không phải tài khoản Zalo thật. Gửi một tin nhắn giả lập để kiểm tra toàn bộ pipeline:
          chống trùng → phân loại ý định → truy xuất tri thức/bộ nhớ → quy tắc → AI trả lời → lưu hội thoại.
          Kết quả thật xuất hiện tại trang Hội thoại.
        </p>
        {kiemTra?.mock && <p className="text-sm mb-3">Trạng thái connector mô phỏng: <HuyHieuTrangThai giaTri={kiemTra.mock.trang_thai} /></p>}
        <div className="grid md:grid-cols-[220px_1fr_auto] gap-2">
          <input className={oNhap} value={tenKhachMoPhong} onChange={(e) => setTenKhachMoPhong(e.target.value)} placeholder="Tên khách giả lập" />
          <input className={oNhap} value={tinMoPhong} onChange={(e) => setTinMoPhong(e.target.value)}
            placeholder="Nội dung tin nhắn giả lập, ví dụ: Cho hỏi giá dịch vụ chăm sóc khách hàng?"
            onKeyDown={(e) => { if (e.key === "Enter") guiMoPhong(); }} />
          <Nut onClick={guiMoPhong} disabled={dangGuiMoPhong || !tinMoPhong.trim()}>
            {dangGuiMoPhong ? "Đang xử lý..." : "Gửi tin mô phỏng"}
          </Nut>
        </div>
        {ketQuaMoPhong && (
          <div className="mt-3 text-sm border rounded p-3 bg-gray-50 dark:bg-neutral-800">
            {ketQuaMoPhong.loi ? (
              <span className="text-red-600">Lỗi: {ketQuaMoPhong.loi}</span>
            ) : (
              <>
                <p>Kết quả xử lý: <b>{ketQuaMoPhong.trung ? "Trùng tin (đã chống gửi trùng)" : ketQuaMoPhong.ly_do || "đã xử lý"}</b>
                  {ketQuaMoPhong.conversation_id && <> · Hội thoại #{ketQuaMoPhong.conversation_id}</>}</p>
                <p className="mt-1">Câu trả lời của bot: {ketQuaMoPhong.tra_loi ? <b>{ketQuaMoPhong.tra_loi}</b> : <i>(không trả lời — bot đang dừng, đã chuyển nhân viên, hoặc đang chờ duyệt)</i>}</p>
              </>
            )}
          </div>
        )}
      </section>

      {/* Khu 3: Zalo OA stub */}
      <section className="bg-white dark:bg-neutral-900 p-5 rounded shadow">
        <h2 className="font-bold text-lg mb-2">3. Zalo OA (Official Account) — API chính thức</h2>
        <p className="text-sm text-gray-600 dark:text-gray-300">
          Zalo OA có API chính thức nhưng cần: tài khoản OA, ứng dụng (app) được Zalo phê duyệt và token truy cập OA hợp lệ.
          Phiên bản hiện tại <b>chưa gọi API OA thật</b> — trạng thái là{" "}
          <b>{kiemTra?.oa_stub?.trang_thai || "chua_ho_tro"}</b>, hệ thống không giả vờ đã kết nối.
        </p>
        <ul className="text-sm text-gray-500 list-disc ml-5 mt-2 space-y-1">
          <li>Bước 1: Đăng ký Zalo OA và tạo ứng dụng tại nền tảng nhà phát triển của Zalo.</li>
          <li>Bước 2: Lấy token truy cập OA theo quy trình chính thức (không chia sẻ token qua kênh không an toàn).</li>
          <li>Bước 3: Viết adapter OA theo đúng interface connector hiện có — không phải sửa bộ điều phối AI.</li>
        </ul>
        <p className="text-sm text-gray-500 mt-2">Chi tiết giới hạn: xem tài liệu <code>docs/GIOI_HAN_ZALO.md</code> trong mã nguồn.</p>
      </section>

      {/* Danh sách tài khoản */}
      <section className="bg-white dark:bg-neutral-900 p-5 rounded shadow">
        <h2 className="font-bold text-lg mb-3">Danh sách tài khoản đã cấu hình</h2>
        {taiKhoan.length === 0 ? (
          <p className="text-sm text-gray-500">Chưa có tài khoản nào trong cơ sở dữ liệu.</p>
        ) : (
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left bg-gray-50 dark:bg-neutral-800">
                <th className="p-3 border-b">Tên tài khoản</th>
                <th className="p-3 border-b">Loại</th>
                <th className="p-3 border-b">Trạng thái</th>
                <th className="p-3 border-b">Lỗi gần nhất</th>
              </tr>
            </thead>
            <tbody>
              {taiKhoan.map((a) => (
                <tr key={a.id} className="hover:bg-gray-50 dark:hover:bg-neutral-800">
                  <td className="p-3 border-b font-medium">{a.name}</td>
                  <td className="p-3 border-b">{NHAN_LOAI_TK[a.account_type] || a.account_type}</td>
                  <td className="p-3 border-b"><HuyHieuTrangThai giaTri={a.status} /></td>
                  <td className="p-3 border-b text-red-600">{a.last_error || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
