import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import { Nut, ThongBao, TieuDeTrang, Truong, oNhap } from "../components/dungChung";

// Trung tâm kiểm thử AI: chọn nhà cung cấp/dịch vụ, nhập câu hỏi, xem câu trả lời
// cùng dữ liệu truy xuất được và nguồn tri thức đã dùng. Kèm danh sách công cụ (Tool Registry).
const CAU_HOI_MAU = [
  "Xin chào, bên mình có dịch vụ gì?",
  "Giá dịch vụ là bao nhiêu?",
  "Cho mình hỏi về chính sách",
  "gia dich vu bao nhieu", // không dấu
  "Tôi muốn gặp nhân viên",
  "Câu hỏi hoàn toàn ngoài phạm vi: thời tiết hôm nay thế nào?",
];

export default function KiemThuAI() {
  const [cauHoi, setCauHoi] = useState("");
  const [providerId, setProviderId] = useState("");
  const [serviceId, setServiceId] = useState("");
  const [providers, setProviders] = useState<any[]>([]);
  const [dichVu, setDichVu] = useState<any[]>([]);
  const [ketQua, setKetQua] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [dangChay, setDangChay] = useState(false);
  const [congCu, setCongCu] = useState<any[]>([]);

  const taiDanhMuc = useCallback(async () => {
    try {
      const [p, s, c] = await Promise.all([
        api("/api/ai-providers"), api("/api/dich-vu"), api("/api/kiem-thu-ai/cong-cu"),
      ]);
      setProviders(p);
      setDichVu(s);
      setCongCu(c);
    } catch {
      // danh mục rỗng thì vẫn cho nhập câu hỏi kiểm thử với cấu hình mặc định
    }
  }, []);

  useEffect(() => { taiDanhMuc(); }, [taiDanhMuc]);

  const chay = async (q?: string) => {
    const cau = (q ?? cauHoi).trim();
    if (!cau) return;
    if (q) setCauHoi(q);
    setDangChay(true);
    setLoi("");
    setKetQua(null);
    try {
      const body: any = { question: cau };
      if (providerId) body.provider_id = Number(providerId);
      if (serviceId) body.service_id = Number(serviceId);
      setKetQua(await api("/api/kiem-thu-ai", { method: "POST", body: JSON.stringify(body) }));
    } catch (e: any) {
      setLoi(e.message);
    } finally {
      setDangChay(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl">
      <TieuDeTrang
        tieuDe="Trung tâm kiểm thử AI"
        moTa="Kiểm tra câu trả lời trước khi bật tự động hóa thật: xem AI dùng nguồn tri thức nào, có bịa khi thiếu dữ liệu không, xử lý tiếng Việt không dấu ra sao."
      />
      {loi && <ThongBao loai="loi">Lỗi khi gọi AI: {loi}</ThongBao>}

      <section className="bg-white dark:bg-neutral-900 rounded shadow p-5">
        <div className="grid md:grid-cols-2 gap-3">
          <Truong nhan="Nhà cung cấp / mô hình">
            <select className={oNhap} value={providerId} onChange={(e) => setProviderId(e.target.value)}>
              <option value="">Mặc định của hệ thống</option>
              {providers.map((p) => (
                <option key={p.id} value={p.id}>{p.name} — {p.model} ({p.status})</option>
              ))}
            </select>
          </Truong>
          <Truong nhan="Dịch vụ để lọc tri thức">
            <select className={oNhap} value={serviceId} onChange={(e) => setServiceId(e.target.value)}>
              <option value="">Tất cả dịch vụ</option>
              {dichVu.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </Truong>
        </div>
        <Truong nhan="Câu hỏi kiểm thử" batBuoc>
          <textarea className={oNhap} rows={3} value={cauHoi} onChange={(e) => setCauHoi(e.target.value)}
            placeholder="Nhập câu hỏi như khách hàng thật sẽ hỏi..." />
        </Truong>
        <div className="flex flex-wrap gap-2 mb-4">
          {CAU_HOI_MAU.map((m) => (
            <button key={m} onClick={() => chay(m)} disabled={dangChay}
              className="text-xs bg-gray-100 hover:bg-gray-200 dark:bg-neutral-800 px-2.5 py-1.5 rounded-full disabled:opacity-50">
              {m}
            </button>
          ))}
        </div>
        <Nut onClick={() => chay()} disabled={dangChay || !cauHoi.trim()}>
          {dangChay ? "Đang kiểm thử..." : "Chạy kiểm thử"}
        </Nut>

        {ketQua && (
          <div className="mt-5 space-y-4">
            <div className="border rounded p-4">
              <p className="text-sm text-gray-500">Câu trả lời — mô hình thực tế đã dùng: <b>{ketQua.model}</b></p>
              <p className="mt-2 whitespace-pre-wrap">{ketQua.cau_tra_loi}</p>
            </div>
            <div>
              <p className="font-semibold text-sm mb-2">
                Dữ liệu truy xuất được ({(ketQua.nguon || []).length} đoạn) — AI chỉ được trả lời dựa trên các nguồn này:
              </p>
              {(ketQua.nguon || []).length === 0 ? (
                <p className="text-sm text-amber-700 bg-amber-50 border border-amber-300 rounded p-3">
                  Không truy xuất được đoạn tri thức nào. Trả lời phía trên phải là câu hỏi lại hoặc giới hạn phạm vi — nếu AI vẫn trả lời chắc chắn thì cần xem lại cấu hình.
                </p>
              ) : (
                <div className="space-y-2">
                  {ketQua.nguon.map((n: any) => (
                    <div key={n.chunk_id} className="border rounded p-3 text-sm">
                      <div className="flex justify-between gap-2">
                        <span className="font-medium"><i className="fa-regular fa-file-lines mr-1.5 text-gray-400" />{n.title}</span>
                        <span className="text-gray-500">Điểm: {n.score}</span>
                      </div>
                      <p className="text-gray-600 dark:text-gray-300 mt-1 whitespace-pre-wrap">{n.content}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </section>

      <section className="bg-white dark:bg-neutral-900 rounded shadow p-5 mt-5">
        <h2 className="font-bold mb-2">Công cụ bot được phép dùng (Tool Registry)</h2>
        <p className="text-sm text-gray-500 mb-3">
          AI chỉ gọi được các công cụ trong danh sách cho phép này — không tự ý gọi API hay lệnh hệ thống ngoài danh sách.
        </p>
        {congCu.length === 0 ? (
          <p className="text-sm text-gray-500">Chưa tải được danh sách công cụ.</p>
        ) : (
          <ul className="text-sm space-y-2">
            {congCu.map((c) => (
              <li key={c.ten} className="flex items-center justify-between border-b pb-2 last:border-0">
                <span><code className="bg-gray-100 dark:bg-neutral-800 px-1.5 py-0.5 rounded">{c.ten}</code> — {c.mo_ta}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${c.trang_thai === "bat" ? "bg-green-100 text-green-800" : "bg-gray-200 text-gray-700"}`}>
                  {c.trang_thai === "bat" ? "Đang bật" : c.trang_thai}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
