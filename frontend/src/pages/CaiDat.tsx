import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import { DangTai, LoiTai, Nut, ThongBao, Truong, oNhap } from "../components/dungChung";

// Cài đặt hệ thống lưu bền vững trong DB qua /api/cai-dat (cần quyền quản trị viên để lưu).
// Bao gồm: tự động trả lời toàn cục, thời gian gom tin, chế độ duyệt trước khi gửi,
// múi giờ, số tin nhắn ngữ cảnh cho AI, tên hiển thị của bot.
const MUI_GIO = [
  "Asia/Ho_Chi_Minh",
  "Asia/Bangkok",
  "Asia/Singapore",
  "Asia/Tokyo",
  "UTC",
];

export default function CaiDat() {
  const [form, setForm] = useState<any>(null);
  const [dangTai, setDangTai] = useState(true);
  const [loi, setLoi] = useState("");
  const [dangLuu, setDangLuu] = useState(false);
  const [thongBao, setThongBao] = useState<{ loai: "thanh_cong" | "loi"; text: string } | null>(null);
  const [sucKhoe, setSucKhoe] = useState<any>(null);

  const tai = useCallback(async () => {
    setDangTai(true);
    setLoi("");
    try {
      const [cd, sk] = await Promise.all([api("/api/cai-dat"), fetch("/api/suc-khoe").then((r) => r.json()).catch(() => null)]);
      setForm(cd);
      setSucKhoe(sk);
    } catch (e: any) {
      setLoi(e.message);
    } finally {
      setDangTai(false);
    }
  }, []);

  useEffect(() => { tai(); }, [tai]);

  const luu = async (e: FormEvent) => {
    e.preventDefault();
    if (!form) return;
    setDangLuu(true);
    setThongBao(null);
    try {
      const kq = await api("/api/cai-dat", {
        method: "PUT",
        body: JSON.stringify({
          tu_dong_tra_loi_toan_cuc: !!form.tu_dong_tra_loi_toan_cuc,
          thoi_gian_gom_tin_ms: Number(form.thoi_gian_gom_tin_ms) || 0,
          che_do_duyet_truoc_khi_gui: !!form.che_do_duyet_truoc_khi_gui,
          mui_gio: form.mui_gio,
          so_tin_nhan_ngu_canh: Number(form.so_tin_nhan_ngu_canh) || 10,
          ten_hien_thi_bot: form.ten_hien_thi_bot || "",
          thong_bao_admin_zalo_thread_id: form.thong_bao_admin_zalo_thread_id || "",
          thong_bao_khach_moi: !!form.thong_bao_khach_moi,
          thong_bao_co_so_dien_thoai: !!form.thong_bao_co_so_dien_thoai,
          thong_bao_du_thong_tin: !!form.thong_bao_du_thong_tin,
          thong_bao_gap_nhan_vien: !!form.thong_bao_gap_nhan_vien,
          thong_bao_khieu_nai: !!form.thong_bao_khieu_nai,
          thong_bao_bot_khong_tra_loi_duoc: !!form.thong_bao_bot_khong_tra_loi_duoc,
          thong_bao_loi_he_thong: !!form.thong_bao_loi_he_thong,
        }),
      });
      setForm(kq);
      setThongBao({ loai: "thanh_cong", text: "Đã lưu cài đặt vào cơ sở dữ liệu. Cài đặt có hiệu lực cho các lượt xử lý tiếp theo." });
    } catch (err: any) {
      setThongBao({ loai: "loi", text: `Lưu thất bại: ${err.message} (lưu cài đặt yêu cầu quyền quản trị viên)` });
    } finally {
      setDangLuu(false);
    }
  };

  if (dangTai) return <DangTai />;
  if (loi || !form) return <LoiTai loi={loi || "Không đọc được cài đặt"} onThuLai={tai} />;

  const dat = (k: string) => (e: any) =>
    setForm((f: any) => ({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));

  return (
    <div className="p-6 max-w-3xl">
      <h1 className="text-2xl font-bold mb-1">Cài đặt hệ thống</h1>
      <p className="text-sm text-gray-500 mb-5">
        Mọi thay đổi được xác thực, lưu bền vững trong cơ sở dữ liệu và áp dụng cho toàn hệ thống.
        Cài đặt riêng cho AI nằm tại “Nhà cung cấp AI”, riêng cho Zalo nằm tại “Tài khoản Zalo”.
      </p>
      {thongBao && <ThongBao loai={thongBao.loai}>{thongBao.text}</ThongBao>}

      <form onSubmit={luu} className="space-y-5">
        <section className="bg-white dark:bg-neutral-900 rounded shadow p-5">
          <h2 className="font-bold mb-3">Cài đặt hội thoại và tự động hóa</h2>
          <label className="flex items-start gap-3 mb-4 cursor-pointer">
            <input type="checkbox" className="mt-1" checked={!!form.tu_dong_tra_loi_toan_cuc} onChange={dat("tu_dong_tra_loi_toan_cuc")} />
            <span className="text-sm">
              <b>Tự động trả lời toàn cục</b>
              <span className="block text-gray-500">Khi tắt, bot không tự trả lời ở mọi hội thoại (vẫn nhận và lưu tin). Có thể bật/tắt riêng từng hội thoại ở trang Hội thoại.</span>
            </span>
          </label>
          <label className="flex items-start gap-3 mb-4 cursor-pointer">
            <input type="checkbox" className="mt-1" checked={!!form.che_do_duyet_truoc_khi_gui} onChange={dat("che_do_duyet_truoc_khi_gui")} />
            <span className="text-sm">
              <b>Chế độ duyệt trước khi gửi</b>
              <span className="block text-gray-500">Bot chỉ soạn câu trả lời, nhân viên duyệt mới gửi đi. An toàn hơn cho nội dung nhạy cảm.</span>
            </span>
          </label>
          <div className="grid grid-cols-2 gap-4">
            <Truong nhan="Thời gian gom tin nhắn (mili-giây)">
              <input className={oNhap} type="number" min={0} max={30000} value={form.thoi_gian_gom_tin_ms} onChange={dat("thoi_gian_gom_tin_ms")} />
              <span className="text-xs text-gray-400">Chờ gom nhiều tin liên tiếp của khách thành một ngữ cảnh trước khi trả lời. Có giới hạn chờ tối đa để tránh treo.</span>
            </Truong>
            <Truong nhan="Số tin nhắn gần nhất đưa vào ngữ cảnh AI">
              <input className={oNhap} type="number" min={1} max={100} value={form.so_tin_nhan_ngu_canh} onChange={dat("so_tin_nhan_ngu_canh")} />
              <span className="text-xs text-gray-400">Chỉ đưa số tin liên quan, không nạp toàn bộ lịch sử vào mỗi lần gọi AI.</span>
            </Truong>
          </div>
        </section>

        <section className="bg-white dark:bg-neutral-900 rounded shadow p-5">
          <h2 className="font-bold mb-3">Cài đặt hiển thị và danh tính bot</h2>
          <div className="grid grid-cols-2 gap-4">
            <Truong nhan="Múi giờ hệ thống">
              <select className={oNhap} value={form.mui_gio} onChange={dat("mui_gio")}>
                {MUI_GIO.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
              <span className="text-xs text-gray-400">Mặc định Asia/Ho_Chi_Minh. Định dạng ngày DD/MM/YYYY, tiền tệ VND.</span>
            </Truong>
            <Truong nhan="Tên hiển thị của bot">
              <input className={oNhap} value={form.ten_hien_thi_bot || ""} onChange={dat("ten_hien_thi_bot")}
                placeholder="Ví dụ: Trợ lý hỗ trợ khách hàng" />
              <span className="text-xs text-gray-400">Danh tính bot được khóa trong lời nhắc hệ thống — mô hình không tự giới thiệu sai danh tính.</span>
            </Truong>
          </div>
        </section>

        <section className="bg-white dark:bg-neutral-900 rounded shadow p-5">
          <h2 className="font-bold mb-3">Thông báo cho quản trị viên</h2>
          <p className="text-sm text-gray-500 mb-4">
            Thông báo luôn được ghi vào Trung tâm thông báo (mục “Thông báo” + chuông ở thanh trên).
            Nếu điền ID hội thoại admin, hệ thống còn gửi thêm qua Zalo cá nhân (chỉ với sự kiện từ kênh cá nhân,
            tối thiểu 60 giây giữa hai lần gửi để chống spam). Tắt từng loại nếu không muốn nhận.
          </p>
          <Truong nhan="ID hội thoại Zalo của admin (để trống = không gửi qua Zalo)">
            <input className={oNhap} value={form.thong_bao_admin_zalo_thread_id || ""}
              onChange={dat("thong_bao_admin_zalo_thread_id")}
              placeholder="ID thread Zalo cá nhân của admin" />
            <span className="text-xs text-gray-400">Là định danh cuộc trò chuyện Zalo mà tài khoản bot dùng để nhắn cho admin.</span>
          </Truong>
          <div className="grid grid-cols-2 gap-x-4 gap-y-2 mt-3">
            {[
              ["thong_bao_khach_moi", "Khách hàng mới nhắn tin lần đầu"],
              ["thong_bao_co_so_dien_thoai", "Khách để lại số điện thoại"],
              ["thong_bao_du_thong_tin", "Đã thu thập đủ thông tin khách"],
              ["thong_bao_gap_nhan_vien", "Khách yêu cầu gặp nhân viên"],
              ["thong_bao_khieu_nai", "Khách có dấu hiệu khiếu nại"],
              ["thong_bao_bot_khong_tra_loi_duoc", "Bot không trả lời được (lỗi AI)"],
              ["thong_bao_loi_he_thong", "Lỗi hệ thống / lỗi gửi tin"],
            ].map(([khoa, nhan]) => (
              <label key={khoa} className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={!!form[khoa]} onChange={dat(khoa)} />
                {nhan}
              </label>
            ))}
          </div>
        </section>

        <section className="bg-white dark:bg-neutral-900 rounded shadow p-5">
          <h2 className="font-bold mb-2">Sức khỏe hệ thống</h2>
          <p className="text-sm">
            Trạng thái qua <code>/api/suc-khoe</code>:{" "}
            {sucKhoe
              ? <span className="text-green-700 font-medium">{sucKhoe.trang_thai === "khoe" ? "Đang khỏe" : sucKhoe.trang_thai} — {sucKhoe.dich_vu}</span>
              : <span className="text-red-600">Không gọi được API sức khỏe</span>}
          </p>
          <p className="text-xs text-gray-400 mt-2">
            Sao lưu dữ liệu tại “Sao lưu và khôi phục”. Đường dẫn dữ liệu, chính sách giữ nhật ký và giới hạn tệp được cấu hình bằng biến môi trường khi triển khai (xem tài liệu hướng dẫn Windows/Linux).
          </p>
        </section>

        <div className="flex gap-2">
          <Nut type="submit" disabled={dangLuu}>{dangLuu ? "Đang lưu..." : "Lưu cài đặt"}</Nut>
          <Nut mau="xam" onClick={tai}>Tải lại từ máy chủ</Nut>
        </div>
      </form>
    </div>
  );
}
