import { useCallback, useEffect, useRef, useState } from "react";
import { api, apiTaiFile, dinhDangThoiGian } from "../lib/api";
import { ChuaCoDuLieu, DangTai, HuyHieuTrangThai, LoiTai, Nut, PhanTrang, ThongBao, TieuDeTrang, oNhap } from "../components/dungChung";
import { useToast } from "../components/Toast";

// Hộp thư hội thoại 2 cột:
// - Trái: danh sách hội thoại (tên khách, tin gần nhất, trạng thái, bot/nhân viên), tìm kiếm + lọc trạng thái.
// - Phải: khung chat theo thời gian (khách/bot/nhân viên/hệ thống), gửi tin thủ công,
//   Tạm dừng bot / Bật lại bot / Chuyển nhân viên / Trả lại bot / Đổi trạng thái xử lý.

const NHAN_NGUOI_GUI: Record<string, string> = {
  khach: "Khách hàng",
  bot: "Bot tự động",
  nhan_vien: "Nhân viên",
  he_thong: "Hệ thống",
};

// Ảnh đính kèm trong tin nhắn: nếu là ảnh đã tải về máy chủ (đường dẫn
// /api/tep/...) thì phải tải qua API kèm token rồi hiển thị bằng object URL;
// nếu là URL gốc của Zalo (khi tải về lỗi) thì dùng thẳng làm nguồn ảnh.
// Bấm vào ảnh để mở xem lớn ở tab mới.
function AnhDinhKem({ nguon }: { nguon: string }) {
  const noiBo = (nguon || "").startsWith("/api/");
  const [urlHien, setUrlHien] = useState(noiBo ? "" : nguon);
  const [loiAnh, setLoiAnh] = useState(false);
  useEffect(() => {
    if (!noiBo) { setUrlHien(nguon); return; }
    let huy = false;
    let objUrl = "";
    (async () => {
      try {
        const { blob } = await apiTaiFile(nguon);
        objUrl = URL.createObjectURL(blob);
        if (!huy) setUrlHien(objUrl);
      } catch {
        if (!huy) setLoiAnh(true);
      }
    })();
    return () => { huy = true; if (objUrl) URL.revokeObjectURL(objUrl); };
  }, [nguon, noiBo]);
  if (loiAnh) {
    // Ảnh local trả 404 = đã bị dọn theo chính sách lưu (so_ngay_luu_anh_khach)
    // hoặc không tải được — hiện ô xám thay cho ảnh vỡ.
    return (
      <div className="mt-1.5 flex items-center gap-2 rounded-lg bg-gray-200 dark:bg-neutral-700 text-gray-500 dark:text-gray-300 px-3 py-2.5 text-xs max-w-[260px]">
        <i className="fa-regular fa-image text-base" />
        <span>Ảnh đã hết hạn lưu trữ</span>
      </div>
    );
  }
  if (!urlHien) {
    return <p className="text-xs text-gray-400 mt-1"><i className="fa-regular fa-image mr-1" />Đang tải ảnh...</p>;
  }
  return (
    <a href={urlHien} target="_blank" rel="noreferrer" title="Bấm để xem ảnh lớn">
      <img src={urlHien} alt="Ảnh khách gửi"
        className="mt-1.5 max-w-[260px] max-h-[260px] w-auto rounded-lg border dark:border-neutral-700 object-contain cursor-zoom-in"
        onError={() => setLoiAnh(true)} />
    </a>
  );
}

// Sticker bot gửi: attachment_url chứa JSON sticker {id, cate_id, type, nhan,
// url_xem_truoc}. Có ảnh xem trước thì hiện ảnh, không thì hiện nhãn [Sticker].
function StickerDinhKem({ urlJson }: { urlJson: string }) {
  let stk: any = null;
  try { stk = JSON.parse(urlJson || ""); } catch { stk = null; }
  const url = stk?.url_xem_truoc || "";
  const nhan = stk?.nhan || "";
  return (
    <div className="mt-1.5">
      {url ? (
        <img src={url} alt={nhan || "Sticker"} className="max-w-[130px] max-h-[130px] w-auto object-contain" />
      ) : null}
      <p className="text-xs text-gray-500 mt-0.5">
        <i className="fa-regular fa-face-smile mr-1" />[Sticker]{nhan ? ` ${nhan}` : ""}
      </p>
    </div>
  );
}

export default function HoiThoai() {
  const toast = useToast();
  const [danhSach, setDanhSach] = useState<any[]>([]);
  const [dangTai, setDangTai] = useState(true);
  const [loi, setLoi] = useState("");
  const [tuKhoa, setTuKhoa] = useState("");
  const [locTrangThai, setLocTrangThai] = useState("");
  const [locTin, setLocTin] = useState("");
  // Phân trang phía máy chủ (Đợt 3 mục 1): bộ lọc được giữ nguyên khi chuyển trang
  const [trang, setTrang] = useState(1);
  const [kichThuocTrang, setKichThuocTrang] = useState(20);
  const [tongMuc, setTongMuc] = useState(0);
  const [tongTrang, setTongTrang] = useState(1);
  const [dangChonId, setDangChonId] = useState<number | null>(null);
  const [chiTiet, setChiTiet] = useState<any>(null);
  const [dangTaiChiTiet, setDangTaiChiTiet] = useState(false);
  const [noiDungGui, setNoiDungGui] = useState("");
  const [dangGui, setDangGui] = useState(false);
  const [thongBao, setThongBao] = useState<{ loai: "thanh_cong" | "loi"; text: string } | null>(null);
  const cuoiChatRef = useRef<HTMLDivElement>(null);

  const taiDanhSach = useCallback(async () => {
    setDangTai(true);
    setLoi("");
    try {
      const thamSo = new URLSearchParams();
      if (locTrangThai) thamSo.set("trang_thai", locTrangThai);
      if (locTin) thamSo.set("loc_tin", locTin);
      if (tuKhoa.trim()) thamSo.set("tu_khoa", tuKhoa.trim());
      thamSo.set("trang", String(trang));
      thamSo.set("kich_thuoc_trang", String(kichThuocTrang));
      const kq = await api(`/api/hoi-thoai?${thamSo.toString()}`);
      const ds = Array.isArray(kq) ? kq : kq.muc || [];
      setDanhSach(ds);
      setTongMuc(Array.isArray(kq) ? kq.length : kq.tong || 0);
      setTongTrang(Array.isArray(kq) ? 1 : kq.tong_trang || 1);
      if (dangChonId === null && ds.length > 0) setDangChonId(ds[0].id);
    } catch (e: any) {
      setLoi(e.message);
    } finally {
      setDangTai(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locTrangThai, locTin, tuKhoa, trang, kichThuocTrang]);

  useEffect(() => {
    const t = setTimeout(taiDanhSach, tuKhoa ? 350 : 0);
    return () => clearTimeout(t);
  }, [taiDanhSach, tuKhoa]);

  const taiChiTiet = useCallback(async (id: number) => {
    setDangTaiChiTiet(true);
    try {
      setChiTiet(await api(`/api/hoi-thoai/${id}`));
    } catch (e: any) {
      setThongBao({ loai: "loi", text: `Không tải được hội thoại: ${e.message}` });
    } finally {
      setDangTaiChiTiet(false);
    }
  }, []);

  useEffect(() => {
    if (dangChonId !== null) taiChiTiet(dangChonId);
  }, [dangChonId, taiChiTiet]);

  useEffect(() => {
    cuoiChatRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [chiTiet?.messages?.length]);

  const thaoTac = async (duongDan: string, thanhCong: string, body?: any) => {
    if (dangChonId === null) return;
    try {
      await api(duongDan, { method: "POST", body: body ? JSON.stringify(body) : undefined });
      toast.thanhCong(thanhCong);
      await Promise.all([taiChiTiet(dangChonId), taiDanhSach()]);
    } catch (e: any) {
      toast.loi(e.message);
    }
  };

  const guiTin = async () => {
    if (dangChonId === null || !noiDungGui.trim()) return;
    setDangGui(true);
    try {
      const kq = await api(`/api/hoi-thoai/${dangChonId}/gui-tin-nhan`, {
        method: "POST",
        body: JSON.stringify({ content: noiDungGui.trim(), sender_type: "nhan_vien" }),
      });
      setNoiDungGui("");
      if (kq?.status === "loi_gui") toast.loi(`Gửi thất bại: ${kq.error || "connector lỗi"}`);
      await taiChiTiet(dangChonId);
    } catch (e: any) {
      toast.loi(e.message);
    } finally {
      setDangGui(false);
    }
  };

  return (
    <div className="p-4 sm:p-6">
      <TieuDeTrang tieuDe="Hội thoại" moTa="Hộp thư hội thoại thật từ hệ thống. Bot tự dừng khi nhân viên tiếp quản.">
        <Nut mau="xam" onClick={taiDanhSach}><i className="fa-solid fa-rotate mr-2" />Làm mới</Nut>
      </TieuDeTrang>
      {thongBao && <ThongBao loai={thongBao.loai}>{thongBao.text}</ThongBao>}

      <div className="grid lg:grid-cols-[360px_1fr] gap-4 items-start">
        {/* Cột trái — danh sách */}
        <section className="bg-white dark:bg-neutral-900 rounded shadow">
          <div className="p-3 border-b space-y-2">
            <input className={oNhap} placeholder="Tìm theo tên khách hoặc nội dung tin nhắn..."
              value={tuKhoa} onChange={(e) => { setTuKhoa(e.target.value); setTrang(1); }} />
            {/* Lọc theo tình trạng nhắn tin (mục 9.2) */}
            <div className="flex rounded-lg border overflow-hidden text-sm" role="tablist" aria-label="Lọc theo tình trạng nhắn tin">
              {[
                ["", "Tất cả"],
                ["da_nhan_tin", "Đã nhắn tin"],
                ["chua_nhan_tin", "Chưa nhắn"],
              ].map(([v, nhan]) => (
                <button key={v} role="tab" aria-selected={locTin === v}
                  onClick={() => { setLocTin(v); setTrang(1); }}
                  className={`flex-1 px-2 py-2 transition-colors duration-160 ${
                    locTin === v ? "bg-thuongHieu-600 text-white font-medium" : "bg-white dark:bg-neutral-900 hover:bg-gray-50 dark:hover:bg-neutral-800"}`}>
                  {nhan}
                </button>
              ))}
            </div>
            <select className={oNhap} value={locTrangThai} onChange={(e) => { setLocTrangThai(e.target.value); setTrang(1); }}>
              <option value="">Tất cả trạng thái</option>
              <option value="dang_xu_ly">Đang xử lý</option>
              <option value="cho_phan_hoi">Chờ phản hồi</option>
              <option value="da_giai_quyet">Đã giải quyết</option>
            </select>
          </div>
          <div className="max-h-[70vh] overflow-y-auto">
            {dangTai ? (
              <DangTai text="Đang tải hội thoại..." />
            ) : loi ? (
              <LoiTai loi={loi} onThuLai={taiDanhSach} />
            ) : danhSach.length === 0 ? (
              <p className="p-4 text-sm text-gray-500">Chưa có hội thoại nào khớp bộ lọc.</p>
            ) : (
              danhSach.map((c) => (
                <button key={c.id} onClick={() => setDangChonId(c.id)}
                  className={`block w-full text-left px-3.5 py-3 border-b hover:bg-gray-50 dark:hover:bg-neutral-800 ${dangChonId === c.id ? "bg-blue-50 dark:bg-neutral-800" : ""}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium truncate">{c.customer_name || `Khách hàng #${c.customer_id}`}</span>
                    <span className="text-xs text-gray-400 whitespace-nowrap">{dinhDangThoiGian(c.last_message_at || c.updated_at)}</span>
                  </div>
                  <p className="text-sm text-gray-500 truncate mt-0.5">{c.last_message || "Chưa có tin nhắn"}</p>
                  <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-1">
                    <i className="fa-regular fa-message" />
                    {(c.message_count || 0) === 0 ? "Chưa có tin nhắn nào" : `${c.message_count} tin nhắn`}
                    {c.channel && <> · Kênh: {c.channel === "ca_nhan" ? "Zalo cá nhân" : c.channel === "oa" ? "Zalo OA" : "Mô phỏng"}</>}
                    {c.assignee && <> · Phụ trách: {c.assignee}</>}
                  </p>
                  <div className="flex flex-wrap gap-1.5 mt-1.5 items-center">
                    <HuyHieuTrangThai giaTri={c.status} />
                    {c.human_takeover
                      ? <span className="text-xs bg-purple-100 text-purple-800 px-2 py-0.5 rounded-full">Nhân viên tiếp quản</span>
                      : c.bot_enabled
                        ? <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full">Bot đang bật</span>
                        : <span className="text-xs bg-gray-200 text-gray-700 px-2 py-0.5 rounded-full">Bot đã tạm dừng</span>}
                    {c.labels && <span className="text-xs text-gray-500"><i className="fa-solid fa-tag mr-1" />{c.labels}</span>}
                  </div>
                </button>
              ))
            )}
          </div>
          {!dangTai && !loi && (
            <div className="px-3 pb-3">
              <PhanTrang trang={trang} tongTrang={tongTrang} tong={tongMuc} kichThuoc={kichThuocTrang}
                onDoiTrang={setTrang}
                onDoiKichThuoc={(k) => { setKichThuocTrang(k); setTrang(1); }} />
            </div>
          )}
        </section>

        {/* Cột phải — khung chat */}
        <section className="bg-white dark:bg-neutral-900 rounded shadow flex flex-col min-h-[70vh]">
          {dangChonId === null ? (
            <div className="p-4 sm:p-6"><ChuaCoDuLieu text="Chưa có hội thoại nào. Hội thoại sẽ xuất hiện khi khách nhắn tin qua Zalo (hoặc qua kênh mô phỏng khi kiểm thử)." /></div>
          ) : dangTaiChiTiet && !chiTiet ? (
            <DangTai text="Đang tải tin nhắn..." />
          ) : !chiTiet ? (
            <p className="p-6 text-gray-500">Chọn một hội thoại ở cột trái để xem nội dung.</p>
          ) : (
            <>
              <div className="p-4 border-b">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-bold">{chiTiet.customer_name || `Khách hàng #${chiTiet.customer_id}`}</p>
                    <p className="text-xs text-gray-500">
                      {chiTiet.customer_phone && <>Số điện thoại: {chiTiet.customer_phone} · </>}
                      Ưu tiên: {chiTiet.priority || "trung_binh"}
                      {chiTiet.assignee && <> · Phụ trách: {chiTiet.assignee}</>}
                    </p>
                  </div>
                  <HuyHieuTrangThai giaTri={chiTiet.status} />
                </div>
                <div className="flex flex-wrap gap-2 mt-3">
                  {chiTiet.bot_enabled && !chiTiet.human_takeover ? (
                    <Nut mau="xam" onClick={() => thaoTac(`/api/hoi-thoai/${chiTiet.id}/tam-dung-bot`, "Đã tạm dừng bot cho hội thoại này.")}>
                      Tạm dừng bot
                    </Nut>
                  ) : (
                    <Nut mau="xam" onClick={() => thaoTac(`/api/hoi-thoai/${chiTiet.id}/tra-lai-bot`, "Đã bật lại bot và trả quyền xử lý cho bot.")}>
                      Trả lại cho bot
                    </Nut>
                  )}
                  {!chiTiet.human_takeover && (
                    <Nut mau="xam" onClick={() => thaoTac(`/api/hoi-thoai/${chiTiet.id}/chuyen-nhan-vien`, "Đã chuyển hội thoại cho nhân viên. Bot sẽ không tự trả lời nữa.")}>
                      Chuyển nhân viên
                    </Nut>
                  )}
                  {chiTiet.status !== "da_giai_quyet" ? (
                    <Nut mau="xam" onClick={() => thaoTac(`/api/hoi-thoai/${chiTiet.id}/doi-trang-thai`, "Đã đánh dấu hội thoại là đã giải quyết.", { status: "da_giai_quyet" })}>
                      Đánh dấu đã giải quyết
                    </Nut>
                  ) : (
                    <Nut mau="xam" onClick={() => thaoTac(`/api/hoi-thoai/${chiTiet.id}/doi-trang-thai`, "Đã mở lại hội thoại.", { status: "dang_xu_ly" })}>
                      Mở lại hội thoại
                    </Nut>
                  )}
                </div>
                {chiTiet.human_takeover && (
                  <p className="text-xs text-purple-700 bg-purple-50 border border-purple-200 rounded px-2.5 py-1.5 mt-3">
                    Nhân viên đang tiếp quản — bot không tự động gửi tin trong hội thoại này.
                  </p>
                )}
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50 dark:bg-neutral-950">
                {(chiTiet.messages || []).length === 0 ? (
                  <p className="text-sm text-gray-500 text-center">Hội thoại chưa có tin nhắn nào.</p>
                ) : (
                  chiTiet.messages.map((m: any) => {
                    const benKhach = m.sender_type === "khach";
                    const heThong = m.sender_type === "he_thong";
                    if (heThong) {
                      return (
                        <div key={m.id} className="text-center">
                          <span className="text-xs bg-gray-200 dark:bg-neutral-800 text-gray-600 dark:text-gray-300 px-2.5 py-1 rounded-full">
                            {m.content} · {dinhDangThoiGian(m.created_at)}
                          </span>
                        </div>
                      );
                    }
                    // Bong bóng kiểu app nhắn tin (design pass đợt 3): avatar nhỏ
                    // theo người gửi + ký hiệu trạng thái gửi ở góc bong bóng.
                    const avatar =
                      m.sender_type === "bot"
                        ? "bg-blue-600 text-white fa-solid fa-robot"
                        : m.sender_type === "nhan_vien"
                          ? "bg-green-600 text-white fa-solid fa-headset"
                          : "bg-gray-300 dark:bg-neutral-700 text-gray-600 dark:text-gray-200 fa-solid fa-user";
                    return (
                      <div key={m.id} className={`flex items-end gap-2 ${benKhach ? "justify-start" : "justify-end"}`}>
                        {benKhach && (
                          <span className={`${avatar} w-7 h-7 rounded-full flex-none flex items-center justify-center text-[11px]`} />
                        )}
                        <div className={`max-w-[75%] rounded-2xl px-3.5 py-2.5 shadow-sm ${
                          benKhach
                            ? "bg-white dark:bg-neutral-800 rounded-bl-sm"
                            : m.sender_type === "bot"
                              ? "bg-blue-100 dark:bg-blue-950 rounded-br-sm"
                              : "bg-green-100 dark:bg-green-950 rounded-br-sm"}`}>
                          <p className="text-[11px] font-medium text-gray-500 mb-0.5">
                            {NHAN_NGUOI_GUI[m.sender_type] || m.sender_type}
                          </p>
                          {m.attachment_type === "sticker" ? (
                            <StickerDinhKem urlJson={m.attachment_url || ""} />
                          ) : (
                            <p className="text-sm whitespace-pre-wrap break-words">{m.content}</p>
                          )}
                          {m.attachment_type === "anh" && m.attachment_url && (
                            <AnhDinhKem nguon={m.attachment_url} />
                          )}
                          <p className="text-[11px] text-gray-400 mt-1 text-right">
                            {dinhDangThoiGian(m.created_at)}
                            {!benKhach && m.status === "da_gui" && (
                              <span className="text-blue-500 ml-1" title="Đã gửi"><i className="fa-solid fa-check-double" /></span>
                            )}
                            {!benKhach && m.status === "loi_gui" && (
                              <span className="text-red-500 ml-1" title="Gửi lỗi"><i className="fa-solid fa-triangle-exclamation" /> Gửi lỗi</span>
                            )}
                            {m.status && m.status !== "da_gui" && m.status !== "loi_gui" ? ` · ${m.status}` : ""}
                          </p>
                          {m.error === "provider_khong_ho_tro_anh" ? (
                            <p className="text-[11px] text-amber-600 mt-0.5">
                              <i className="fa-solid fa-eye-slash mr-1" />Bot chưa xem được ảnh này — model AI hiện tại không hỗ trợ xem ảnh, bot đã trả lời dự phòng.
                            </p>
                          ) : m.error ? (
                            <p className="text-[11px] text-red-600 mt-0.5">Lỗi gửi: {m.error}</p>
                          ) : null}
                        </div>
                        {!benKhach && (
                          <span className={`${avatar} w-7 h-7 rounded-full flex-none flex items-center justify-center text-[11px]`} />
                        )}
                      </div>
                    );
                  })
                )}
                <div ref={cuoiChatRef} />
              </div>

              <div className="p-3 border-t flex gap-2">
                <textarea className={`${oNhap} resize-none`} rows={2}
                  placeholder="Nhập tin nhắn gửi với tư cách nhân viên... (Enter để gửi, Shift+Enter xuống dòng)"
                  value={noiDungGui}
                  onChange={(e) => setNoiDungGui(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); guiTin(); } }} />
                <Nut onClick={guiTin} disabled={dangGui || !noiDungGui.trim()}>
                  {dangGui ? "Đang gửi..." : "Gửi tin"}
                </Nut>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
