import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { TieuDeTrang } from "../components/dungChung";
import { useToast } from "../components/Toast";

// Trợ lý cấu hình qua đoạn chat (Đợt nâng cấp 3, mục 2): gõ lệnh tự nhiên ->
// hệ thống phân tích thành các thay đổi cài đặt -> quản trị viên duyệt từng
// thẻ xác nhận (cũ -> mới) rồi mới áp dụng thật. Lịch sử giữ trong phiên.

type ThayDoi = {
  khoa: string; nhan: string; kieu: string;
  gia_tri_cu: any; gia_tri_moi: any;
};

type TinNhan = {
  id: number;
  tu: "admin" | "tro_ly";
  noi_dung: string;
  thay_doi?: ThayDoi[];
  trang_thai_the?: "cho_duyet" | "da_ap_dung" | "da_bo";
  goi_y?: string[];
};

let demId = 1;

function hienGiaTri(v: any): string {
  if (v === true) return "Bật";
  if (v === false) return "Tắt";
  if (v === null || v === undefined || v === "") return "(trống)";
  return String(v);
}

export default function TroLyCauHinh() {
  const toast = useToast();
  const [cacTin, setCacTin] = useState<TinNhan[]>([
    {
      id: 0, tu: "tro_ly",
      noi_dung: "Chào bạn! Hãy gõ lệnh cấu hình bằng tiếng Việt tự nhiên, ví dụ \"Bật chế độ trò chuyện tự do\" hoặc \"Đặt nhiệt độ AI thành 0.7\". Mình sẽ phân tích thành các thay đổi để bạn duyệt trước — chưa bấm Áp dụng là chưa đổi gì.",
      goi_y: ["Bật chế độ trò chuyện tự do", "Tắt thả tim", "Đặt nhiệt độ AI thành 0.7", "Đổi giọng bot sang ngắn gọn"],
    },
  ]);
  const [lenh, setLenh] = useState("");
  const [dangPhanTich, setDangPhanTich] = useState(false);
  const [dangApDungId, setDangApDungId] = useState<number | null>(null);
  const cuoiRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    cuoiRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [cacTin, dangPhanTich]);

  const guiLenh = async (cauLenh: string) => {
    const lenhSach = cauLenh.trim();
    if (!lenhSach || dangPhanTich) return;
    setLenh("");
    setCacTin((ds) => [...ds, { id: demId++, tu: "admin", noi_dung: lenhSach }]);
    setDangPhanTich(true);
    try {
      const kq = await api("/api/cau-hinh-chat/phan-tich", {
        method: "POST",
        body: JSON.stringify({ cau_lenh: lenhSach }),
      });
      setCacTin((ds) => [
        ...ds,
        {
          id: demId++, tu: "tro_ly",
          noi_dung: kq.loi_nhan || "Đã phân tích xong.",
          thay_doi: kq.thay_doi && kq.thay_doi.length ? kq.thay_doi : undefined,
          trang_thai_the: kq.thay_doi && kq.thay_doi.length ? "cho_duyet" : undefined,
          goi_y: kq.goi_y && kq.goi_y.length ? kq.goi_y : undefined,
        },
      ]);
    } catch (e: any) {
      setCacTin((ds) => [...ds, { id: demId++, tu: "tro_ly", noi_dung: `Không phân tích được lệnh: ${e.message}` }]);
    } finally {
      setDangPhanTich(false);
    }
  };

  const apDung = async (tin: TinNhan) => {
    if (!tin.thay_doi) return;
    setDangApDungId(tin.id);
    try {
      const kq = await api("/api/cau-hinh-chat/ap-dung", {
        method: "POST",
        body: JSON.stringify({
          thay_doi: tin.thay_doi.map((t) => ({ khoa: t.khoa, gia_tri: t.gia_tri_moi })),
        }),
      });
      setCacTin((ds) => ds.map((t) => (t.id === tin.id ? { ...t, trang_thai_the: "da_ap_dung" } : t)));
      toast.thanhCong(`Đã áp dụng ${kq.da_ap_dung?.length ?? tin.thay_doi.length} thay đổi cấu hình`);
    } catch (e: any) {
      toast.loi(`Không áp dụng được: ${e.message}`);
    } finally {
      setDangApDungId(null);
    }
  };

  const boQua = (tin: TinNhan) => {
    setCacTin((ds) => ds.map((t) => (t.id === tin.id ? { ...t, trang_thai_the: "da_bo" } : t)));
  };

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto">
      <TieuDeTrang
        tieuDe="Trợ lý cấu hình"
        moTa="Cấu hình hệ thống bằng câu lệnh tự nhiên: trợ lý phân tích lệnh thành các thay đổi trong Trung tâm cấu hình, bạn duyệt từng thay đổi rồi mới áp dụng. Mọi lần áp dụng đều được ghi nhật ký hệ thống."
      />
      <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-the flex flex-col" style={{ minHeight: "60vh" }}>
        <div className="flex-1 overflow-y-auto cuon-dep p-4 space-y-4">
          {cacTin.map((tin) =>
            tin.tu === "admin" ? (
              <div key={tin.id} className="flex justify-end">
                <div className="max-w-[80%] bg-blue-600 text-white rounded-2xl rounded-br-md px-4 py-2.5 text-sm shadow-nhe">
                  {tin.noi_dung}
                </div>
              </div>
            ) : (
              <div key={tin.id} className="flex justify-start">
                <div className="max-w-[88%] space-y-3">
                  <div className="bg-gray-100 dark:bg-neutral-800 rounded-2xl rounded-bl-md px-4 py-2.5 text-sm shadow-nhe">
                    <p className="font-semibold text-xs text-gray-500 mb-1">
                      <i className="fa-solid fa-terminal mr-1.5" />Trợ lý cấu hình
                    </p>
                    {tin.noi_dung}
                  </div>
                  {tin.thay_doi && (
                    <div className="space-y-2">
                      {tin.thay_doi.map((t) => (
                        <div key={t.khoa} className="border rounded-xl p-3.5 bg-white dark:bg-neutral-900 shadow-nhe">
                          <p className="text-sm font-semibold">{t.nhan}</p>
                          <p className="text-xs text-gray-400 mb-2">Khóa: {t.khoa}</p>
                          <div className="flex flex-wrap items-center gap-2 text-sm">
                            <span className="bg-gray-100 dark:bg-neutral-800 rounded px-2 py-1 line-through decoration-red-400/70">
                              {hienGiaTri(t.gia_tri_cu)}
                            </span>
                            <i className="fa-solid fa-arrow-right text-gray-400 text-xs" />
                            <span className="bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-900 rounded px-2 py-1 font-medium">
                              {hienGiaTri(t.gia_tri_moi)}
                            </span>
                          </div>
                        </div>
                      ))}
                      {tin.trang_thai_the === "cho_duyet" && (
                        <div className="flex gap-2">
                          <button
                            onClick={() => apDung(tin)}
                            disabled={dangApDungId === tin.id}
                            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 shadow-nhe"
                          >
                            <i className="fa-solid fa-check mr-1.5" />
                            {dangApDungId === tin.id ? "Đang áp dụng..." : "Áp dụng các thay đổi này"}
                          </button>
                          <button
                            onClick={() => boQua(tin)}
                            className="bg-white dark:bg-neutral-900 border px-4 py-2 rounded-lg text-sm hover:bg-gray-50 dark:hover:bg-neutral-800"
                          >
                            Bỏ qua
                          </button>
                        </div>
                      )}
                      {tin.trang_thai_the === "da_ap_dung" && (
                        <p className="text-sm text-green-600 font-medium">
                          <i className="fa-solid fa-circle-check mr-1.5" />Đã áp dụng — cài đặt đã đổi thật và được ghi vào Nhật ký hệ thống.
                        </p>
                      )}
                      {tin.trang_thai_the === "da_bo" && (
                        <p className="text-sm text-gray-400">
                          <i className="fa-solid fa-ban mr-1.5" />Đã bỏ qua — không thay đổi gì.
                        </p>
                      )}
                    </div>
                  )}
                  {tin.goi_y && (
                    <div className="flex flex-wrap gap-2">
                      {tin.goi_y.map((g) => (
                        <button key={g} onClick={() => guiLenh(g)}
                          className="text-xs border border-blue-200 dark:border-blue-900 text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-950/40 rounded-full px-3 py-1.5 hover:bg-blue-100 dark:hover:bg-blue-900/50">
                          {g}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ),
          )}
          {dangPhanTich && (
            <div className="flex justify-start">
              <div className="bg-gray-100 dark:bg-neutral-800 rounded-2xl rounded-bl-md px-4 py-2.5 text-sm text-gray-500">
                <span className="inline-block w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin align-[-3px] mr-2" />
                Đang phân tích lệnh...
              </div>
            </div>
          )}
          <div ref={cuoiRef} />
        </div>
        <form
          className="border-t p-3 flex gap-2"
          onSubmit={(e) => { e.preventDefault(); guiLenh(lenh); }}
        >
          <input
            className="flex-1 border rounded-full px-4 py-2.5 text-sm bg-white dark:bg-neutral-800 dark:border-neutral-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
            placeholder="Gõ lệnh cấu hình, ví dụ: Bật chế độ trò chuyện tự do..."
            value={lenh}
            onChange={(e) => setLenh(e.target.value)}
          />
          <button type="submit" disabled={dangPhanTich || !lenh.trim()}
            className="bg-blue-600 text-white w-11 h-11 rounded-full flex-none hover:bg-blue-700 disabled:opacity-50"
            title="Gửi lệnh">
            <i className="fa-solid fa-paper-plane" />
          </button>
        </form>
      </div>
    </div>
  );
}
