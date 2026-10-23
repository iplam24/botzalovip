/**
 * Dịch vụ phụ Zalo cá nhân - dùng thư viện KHÔNG chính thức zca-js.
 *
 * Nguyên tắc bắt buộc:
 * - Nếu chưa cài zca-js (chưa chạy `npm install`), mọi endpoint nghiệp vụ
 *   trả 501 kèm lý do tiếng Việt, TUYỆT ĐỐI không giả vờ đã kết nối.
 * - Không bypass CAPTCHA/OTP. Đăng nhập bằng quét QR do người dùng tự quét.
 * - Session/credentials chỉ lưu trong ../data/ (chmod 600, đã gitignore),
 *   không bao giờ ghi credentials vào log.
 * - Tin nhắn nhận được được chuyển về backend:
 *   POST {BACKEND_URL}/api/zalo/webhook/ca-nhan
 *   kèm header X-Connector-Secret lấy từ env CONNECTOR_SECRET.
 */
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, "..", "data");
const QR_PATH = path.join(DATA_DIR, "qr.png");
const PORT = process.env.PORT || 8791;
const BACKEND_URL = (process.env.BACKEND_URL || "http://localhost:8000").replace(/\/$/, "");
const CONNECTOR_SECRET = process.env.CONNECTOR_SECRET || process.env.ZALO_CONNECTOR_SECRET || "";

fs.mkdirSync(DATA_DIR, { recursive: true });
try { fs.chmodSync(DATA_DIR, 0o700); } catch {}

// Trạng thái nội bộ: chua_dang_nhap | cho_quet | da_quet_cho_xac_nhan | da_ket_noi | qr_het_han | mat_ket_noi | chua_cai_thu_vien
let state = { trang_thai: "chua_dang_nhap", thong_bao: "Chưa đăng nhập", qr_base64: "", qr_updated_at: null };
let api = null;
let ZaloCtor = null;
let libError = "";

try {
  const mod = await import("zca-js");
  ZaloCtor = mod.Zalo || mod.default;
  if (!ZaloCtor) libError = "Gói zca-js không xuất ra Zalo như mong đợi";
} catch (e) {
  libError = "Chưa cài đặt thư viện zca-js: hãy chạy `npm install` trong thư mục connectors/zalo-personal";
  state = { ...state, trang_thai: "chua_cai_thu_vien", thong_bao: libError };
}

// Môi trường máy này bắt buộc ra Internet qua proxy HTTP (biến *_PROXY).
// fetch() của Node tự dùng proxy qua NODE_USE_ENV_PROXY, nhưng WebSocket (gói `ws`)
// thì không — kết nối wss trực tiếp bị chặn sẽ lỗi EPROTO "wrong version number".
// zca-js cho truyền `agent` qua Options: dùng HttpsProxyAgent bọc qua proxy (CONNECT tunnel).
// TUYỆT ĐỐI không ghi URL proxy vào log (URL chứa thông tin xác thực của proxy).
let proxyAgent = null;
try {
  const proxyUrl = process.env.HTTPS_PROXY || process.env.https_proxy || process.env.ALL_PROXY || process.env.all_proxy || process.env.HTTP_PROXY || process.env.http_proxy || "";
  if (proxyUrl) {
    const { HttpsProxyAgent } = await import("https-proxy-agent");
    proxyAgent = new HttpsProxyAgent(proxyUrl);
    console.log("Đã bật proxy agent cho WebSocket Zalo (không ghi địa chỉ proxy)");
  }
} catch { proxyAgent = null; }
function createZalo() { return proxyAgent ? new ZaloCtor({ agent: proxyAgent }) : new ZaloCtor(); }

function saveFile600(file, data) {
  fs.writeFileSync(file, data);
  try { fs.chmodSync(file, 0o600); } catch {}
}

// Thông tin tài khoản đang đăng nhập (phục vụ hiển thị "tài khoản đang liên kết"
// và logic nhóm: backend cần UID của chính bot để nhận diện mention đích danh).
let thongTinTaiKhoan = { tai_khoan_id: "", ten_tai_khoan: "", avatar_url: "", phien_bat_dau_luc: null };

async function capNhatThongTinTaiKhoan() {
  if (!api) return;
  try {
    if (typeof api.getOwnId === "function") {
      const ownId = api.getOwnId();
      if (ownId) thongTinTaiKhoan.tai_khoan_id = String(ownId);
    }
  } catch {}
  try {
    if (typeof api.fetchAccountInfo === "function") {
      const info = await api.fetchAccountInfo();
      const profile = info?.profile || info || {};
      if (profile.userId) thongTinTaiKhoan.tai_khoan_id = String(profile.userId);
      thongTinTaiKhoan.ten_tai_khoan = String(profile.displayName || profile.zaloName || "");
      thongTinTaiKhoan.avatar_url = String(profile.avatar || "");
    }
  } catch {}
  thongTinTaiKhoan.phien_bat_dau_luc = new Date().toISOString();
}

// Trích đính kèm ẢNH từ tin zca-js. Cấu trúc thật (đã kiểm chứng trong
// node_modules/zca-js/dist/models/Message.d.ts): với tin có đính kèm,
// msg.data.content là OBJECT TAttachmentContent {title, description, href,
// thumb, childnumber, action, params, type} — href là URL ảnh đầy đủ,
// thumb là URL ảnh thu nhỏ; msg.data.msgType cho biết loại tin
// (vd "chat.photo" cho ảnh). Một số dạng cũ có thể nằm ở msg.data.attachments.
// Sticker (msgType chứa "sticker") KHÔNG tính là ảnh khách gửi.
function trichDinhKemAnh(msg) {
  const dinhKem = [];
  const msgType = String(msg?.data?.msgType || "");
  if (/sticker/i.test(msgType)) return dinhKem;
  const laLoaiAnh = /photo|image|gif|pict/i.test(msgType);
  const coDuoiAnh = (u) => /\.(jpe?g|png|gif|webp|bmp)(\?|#|$)/i.test(String(u || ""));
  const xetMot = (href, thumb) => {
    const url = typeof href === "string" ? href : "";
    if (!url) return;
    if (!laLoaiAnh && !coDuoiAnh(url)) return; // không có dấu hiệu là ảnh thì bỏ qua
    if (dinhKem.some((d) => d.url === url)) return;
    dinhKem.push({ loai: "anh", url, url_thumb: typeof thumb === "string" && thumb ? thumb : url });
  };
  const c = msg?.data?.content;
  if (c && typeof c === "object" && !Array.isArray(c)) {
    xetMot(c.href, c.thumb);
  }
  const atts = msg?.data?.attachments;
  if (Array.isArray(atts)) {
    for (const a of atts) {
      if (a && typeof a === "object") xetMot(a.href || a.url, a.thumb || a.thumbnail);
    }
  }
  return dinhKem;
}

async function forwardMessage(msg) {
  // Tin do CHÍNH tài khoản bot gửi (isSelf) không chuyển về backend:
  // tránh bot tự xử lý tin của mình (vòng lặp) trong cả chat 1-1 lẫn nhóm.
  if (msg?.isSelf) return;
  // Chỉ chuyển các trường nghiệp vụ cần thiết, không chuyển credentials/session.
  // Cấu trúc thật của zca-js: msg.type là ThreadType (0 = User, 1 = Group),
  // msg.threadId, msg.data.{msgId, cliMsgId, uidFrom, dName, content},
  // riêng tin nhóm có msg.data.mentions: [{uid, pos, len, type}].
  const loaiThread = typeof msg?.type === "number" ? msg.type : 0;
  const laNhom = loaiThread === 1;
  const mentions = laNhom && Array.isArray(msg?.data?.mentions)
    ? msg.data.mentions.map((m) => ({ uid: String(m?.uid ?? ""), pos: m?.pos ?? 0, len: m?.len ?? 0, type: m?.type ?? 0 }))
    : [];
  const payload = {
    external_id: String(msg?.data?.msgId || msg?.data?.cliMsgId || msg?.msgId || Date.now()),
    customer_external_id: String(msg?.threadId || msg?.data?.uidFrom || ""),
    customer_name: String(msg?.data?.dName || "Khách Zalo cá nhân"),
    content: typeof msg?.data?.content === "string" ? msg.data.content : "",
    // Đính kèm ảnh (nếu có) — backend tải về và cho bot "nhìn" ảnh.
    // Payload cũ không đổi; chỉ THÊM trường dinh_kem khi thật có ảnh.
    dinh_kem: trichDinhKemAnh(msg),
    // Trường nhóm (Đợt nâng cấp 2 mục 7): backend quyết định trả lời hay im lặng.
    la_nhom: laNhom,
    loai_thread: loaiThread,
    mentions,
    nguoi_gui_id: String(msg?.data?.uidFrom || ""),
    cli_msg_id: String(msg?.data?.cliMsgId || ""),
    bot_uid: thongTinTaiKhoan.tai_khoan_id || "",
  };
  // Tin CHỈ có ảnh (không chữ) vẫn phải chuyển về backend; tin rỗng hoàn toàn thì bỏ.
  if (!payload.content && payload.dinh_kem.length === 0) return;
  try {
    await fetch(`${BACKEND_URL}/api/zalo/webhook/ca-nhan`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Connector-Secret": CONNECTOR_SECRET },
      body: JSON.stringify(payload),
    });
  } catch {
    console.error("Không chuyển được tin nhắn về backend (backend chưa chạy?)");
  }
}

function startListener() {
  if (!api?.listener) return;
  try {
    api.listener.on("message", (msg) => { forwardMessage(msg).catch(() => {}); });
    api.listener.on("closed", () => { state = { ...state, trang_thai: "mat_ket_noi", thong_bao: "Kết nối Zalo đã đóng" }; });
    // Bắt buộc có handler "error": thiếu nó, lỗi WebSocket của zca-js sẽ ném
    // ERR_UNHANDLED_ERROR làm sập cả tiến trình (đã xảy ra thật 22/10/2026 ngay sau khi đăng nhập thành công).
    api.listener.on("error", (err) => { console.error("Lỗi listener Zalo (đã bắt, dịch vụ vẫn chạy):", err?.message || err); });
    api.listener.on("disconnected", (code, reason) => { console.error(`Listener Zalo ngắt kết nối: ${code} ${reason || ""}`); });
    api.listener.start({ retryOnClose: true });
  } catch (e) { console.error("Không khởi động được listener Zalo:", e?.message || e); }
}

// Mạng phòng thủ cuối: lỗi không bắt được ở tầng WebSocket không được làm sập dịch vụ.
process.on("uncaughtException", (err) => { console.error("Lỗi không bắt được (dịch vụ vẫn chạy):", err?.message || err); });

async function loginQR(res) {
  if (!ZaloCtor) return send(res, 501, { trang_thai: "chua_cai_thu_vien", thong_bao: libError });
  if (state.trang_thai === "da_ket_noi" && api) return send(res, 200, publicState());
  state = { ...state, trang_thai: "cho_quet", thong_bao: "Đang tạo mã QR, hãy quét bằng ứng dụng Zalo", qr_base64: "" };
  send(res, 200, { ...publicState(), dang_tao_qr: true });
  try {
    const zalo = createZalo();
    // zca-js: loginQR(options, callback sự kiện QR). Callback xử lý chung các dạng sự kiện đã biết.
    // LoginQRCallbackEventType của zca-js 2.x là enum số: 0=QRCodeGenerated,
    // 1=QRCodeExpired, 2=QRCodeScanned, 3=QRCodeDeclined, 4=GotLoginInfo.
    const TYPE_NAMES = { 0: "QRCodeGenerated", 1: "QRCodeExpired", 2: "QRCodeScanned", 3: "QRCodeDeclined", 4: "GotLoginInfo" };
    const onEvent = (event) => {
      const type = TYPE_NAMES[event?.type] || event?.type;
      if (type === "GotLoginInfo" && event?.data) {
        // Lưu credentials vào data/ (chmod 600, gitignore) để khôi phục phiên.
        // TUYỆT ĐỐI không ghi nội dung credentials vào log.
        try { saveFile600(path.join(DATA_DIR, "credentials.json"), JSON.stringify(event.data)); } catch {}
      }
      if (type === "QRCodeGenerated" || event?.data?.image) {
        const image = event?.data?.image;
        if (image) {
          state.qr_base64 = image.startsWith("data:") ? image : `data:image/png;base64,${image}`;
          saveFile600(QR_PATH, Buffer.from(image.replace(/^data:image\/png;base64,/, ""), "base64"));
        }
        if (event?.actions?.saveToFile) { try { event.actions.saveToFile(QR_PATH); } catch {} }
        state = { ...state, trang_thai: "cho_quet", qr_updated_at: new Date().toISOString(), thong_bao: "Hãy quét mã QR bằng ứng dụng Zalo" };
      }
      if (type === "QRCodeScanned") state = { ...state, trang_thai: "da_quet_cho_xac_nhan", thong_bao: "Đã quét QR, hãy xác nhận đăng nhập trên điện thoại" };
      if (type === "QRCodeExpired") state = { ...state, trang_thai: "qr_het_han", thong_bao: "Mã QR đã hết hạn, hãy tạo mã QR mới" };
      if (type === "QRCodeDeclined") state = { ...state, trang_thai: "chua_dang_nhap", thong_bao: "Người dùng đã từ chối đăng nhập trên điện thoại" };
    };
    api = await zalo.loginQR({ qrPath: QR_PATH }, onEvent);
    // Nếu loginQR không dùng callback, thử đọc file QR vừa sinh.
    if (!state.qr_base64 && fs.existsSync(QR_PATH)) {
      state.qr_base64 = "data:image/png;base64," + fs.readFileSync(QR_PATH).toString("base64");
      state.qr_updated_at = new Date().toISOString();
    }
    state = { ...state, trang_thai: "da_ket_noi", thong_bao: "Đã kết nối Zalo cá nhân" };
    await capNhatThongTinTaiKhoan();
    startListener();
  } catch (e) {
    state = { ...state, trang_thai: "mat_ket_noi", thong_bao: `Đăng nhập QR thất bại: ${e?.message || "lỗi không rõ"}` };
  }
}

function publicState() {
  return { trang_thai: state.trang_thai, thong_bao: state.thong_bao, qr_base64: state.qr_base64 || "", qr_duong_dan: state.qr_base64 ? "/qr.png" : "", qr_updated_at: state.qr_updated_at, moi_truong: "ca_nhan_sidecar", canh_bao: "Thư viện không chính thức, có rủi ro bị Zalo hạn chế/khóa tài khoản",
    // Tài khoản đang liên kết (mục 9.4): lấy thật từ getOwnId/fetchAccountInfo của zca-js
    tai_khoan_id: thongTinTaiKhoan.tai_khoan_id, ten_tai_khoan: thongTinTaiKhoan.ten_tai_khoan,
    avatar_url: thongTinTaiKhoan.avatar_url, phien_bat_dau_luc: thongTinTaiKhoan.phien_bat_dau_luc };
}
function send(res, code, obj) { const b = JSON.stringify(obj); res.writeHead(code, { "Content-Type": "application/json; charset=utf-8" }); res.end(b); }
function readBody(req) { return new Promise((resolve) => { let d = ""; req.on("data", (c) => (d += c)); req.on("end", () => { try { resolve(JSON.parse(d || "{}")); } catch { resolve({}); } }); }); }
function requireApi(res) {
  if (!ZaloCtor) { send(res, 501, { thong_bao: libError }); return false; }
  if (!api || state.trang_thai !== "da_ket_noi") { send(res, 409, { thong_bao: "Chưa kết nối Zalo cá nhân: hãy đăng nhập bằng mã QR trước" }); return false; }
  return true;
}

// Khôi phục phiên cũ nếu đã có credentials trong data/ (không log nội dung).
async function tryRestore() {
  const credPath = path.join(DATA_DIR, "credentials.json");
  if (!ZaloCtor || !fs.existsSync(credPath)) return;
  try {
    const credentials = JSON.parse(fs.readFileSync(credPath, "utf8"));
    const zalo = createZalo();
    api = await zalo.login(credentials);
    state = { ...state, trang_thai: "da_ket_noi", thong_bao: "Đã khôi phục phiên đăng nhập từ dữ liệu local" };
    await capNhatThongTinTaiKhoan();
    startListener();
  } catch {
    state = { ...state, trang_thai: "chua_dang_nhap", thong_bao: "Phiên cũ không còn hợp lệ, hãy đăng nhập lại bằng mã QR" };
  }
}
tryRestore();

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://localhost");
  try {
    if (req.method === "GET" && url.pathname === "/suc-khoe") return send(res, 200, { trang_thai: "khoe", thu_vien_zca_js: ZaloCtor ? "da_cai" : "chua_cai" });
    if (req.method === "GET" && url.pathname === "/trang-thai") return send(res, 200, publicState());
    if (req.method === "GET" && url.pathname === "/qr.png") {
      if (!fs.existsSync(QR_PATH)) return send(res, 404, { thong_bao: "Chưa có mã QR" });
      res.writeHead(200, { "Content-Type": "image/png" }); return res.end(fs.readFileSync(QR_PATH));
    }
    if (req.method === "POST" && url.pathname === "/dang-nhap-qr") return loginQR(res);
    if (req.method === "POST" && url.pathname === "/ngat-ket-noi") {
      try { api?.listener?.stop?.(); } catch {}
      api = null; state = { trang_thai: "chua_dang_nhap", thong_bao: "Đã ngắt kết nối", qr_base64: "", qr_updated_at: null };
      return send(res, 200, publicState());
    }
    if (req.method === "POST" && url.pathname === "/gui-tin-nhan") {
      if (!requireApi(res)) return;
      const b = await readBody(req);
      if (typeof api.sendMessage !== "function") return send(res, 501, { thong_bao: "Bản zca-js hiện tại không hỗ trợ gửi tin nhắn qua hàm sendMessage" });
      await api.sendMessage(b.content || b.message || "", String(b.thread_id || b.threadId || ""), b.thread_type ?? 0);
      return send(res, 200, { thanh_cong: true });
    }
    if (req.method === "POST" && url.pathname === "/tha-cam-xuc") {
      if (!requireApi(res)) return;
      const fn = api.addReaction || api.sendReaction;
      if (typeof fn !== "function") return send(res, 501, { thong_bao: "Thư viện zca-js hiện tại không hỗ trợ thả cảm xúc (không có addReaction)" });
      const b = await readBody(req);
      const dest = { data: { msgId: String(b.message_id || ""), cliMsgId: String(b.cli_msg_id || b.message_id || "") }, threadId: String(b.thread_id || ""), type: b.thread_type ?? 0 };
      // zca-js nhận icon theo GIÁ TRỊ enum Reactions (vd HEART = "/-heart"), không phải tên enum
      const ICON_MAP = { HEART: "/-heart", LIKE: "/-strong", HAHA: ":>", WOW: ":o", CRY: ":-(( ", ANGRY: ":-h" };
      const icon = ICON_MAP[b.icon] || b.icon || "/-heart";
      await fn.call(api, icon, dest);
      return send(res, 200, { thanh_cong: true });
    }
    if (req.method === "POST" && url.pathname === "/tha-tim") {
      // Thả tim (Đợt nâng cấp 2 mục 4): zca-js CÓ addReaction thật
      // (đã kiểm chứng trong dist/apis/addReaction.js, icon Reactions.HEART = "/-heart").
      if (!requireApi(res)) return;
      if (typeof api.addReaction !== "function") return send(res, 501, { thong_bao: "Thư viện zca-js hiện tại không hỗ trợ thả cảm xúc (không có addReaction)" });
      const b = await readBody(req);
      if (!b.thread_id || !b.message_id) return send(res, 400, { thong_bao: "Thiếu thread_id hoặc message_id" });
      const dest = {
        data: { msgId: String(b.message_id), cliMsgId: String(b.cli_msg_id || b.message_id) },
        threadId: String(b.thread_id),
        type: b.loai_thread ?? b.thread_type ?? 0, // ThreadType: 0 = User, 1 = Group
      };
      await api.addReaction("/-heart", dest);
      return send(res, 200, { thanh_cong: true });
    }
    if (req.method === "POST" && (url.pathname === "/dang-soan-tin" || url.pathname === "/dang-soan")) {
      // Hiệu ứng "đang soạn tin": zca-js CÓ sendTypingEvent(threadId, type)
      // thật — đã kiểm chứng dist/apis/sendTypingEvent.d.ts.
      // /dang-soan là tên chuẩn mới (body {thread_id, loai_thread, bat});
      // /dang-soan-tin giữ lại để tương thích bản backend cũ.
      if (!requireApi(res)) return;
      if (typeof api.sendTypingEvent !== "function") return send(res, 501, { thong_bao: "Thư viện zca-js hiện tại không hỗ trợ hiệu ứng đang soạn tin (không có sendTypingEvent)" });
      const b = await readBody(req);
      if (!b.thread_id) return send(res, 400, { thong_bao: "Thiếu thread_id" });
      await api.sendTypingEvent(String(b.thread_id), b.loai_thread ?? b.thread_type ?? 0);
      return send(res, 200, { thanh_cong: true });
    }
    if (req.method === "GET" && url.pathname === "/sticker-goi-y") {
      // Gợi ý sticker THẬT qua zca-js: getStickers(keyword) -> [id...],
      // getStickersDetail(ids) -> chi tiết {id, cateId, type, text, stickerUrl...}.
      // Đã kiểm chứng cả hai hàm tồn tại trong dist/apis của thư viện.
      if (!requireApi(res)) return;
      if (typeof api.getStickers !== "function") return send(res, 501, { thong_bao: "Thư viện zca-js hiện tại không hỗ trợ tra cứu sticker (không có getStickers)" });
      const q = url.searchParams.get("q") || "";
      const ids = await api.getStickers(q);
      const danhSachId = (Array.isArray(ids) ? ids : []).slice(0, 20);
      let ket_qua = danhSachId.map((id) => ({ id: Number(id), cate_id: 0, type: 1, nhan: "", url_xem_truoc: "" }));
      if (danhSachId.length && typeof api.getStickersDetail === "function") {
        const chiTiet = await api.getStickersDetail(danhSachId);
        if (Array.isArray(chiTiet)) {
          ket_qua = chiTiet.map((d) => ({
            id: Number(d?.id || 0),
            cate_id: Number(d?.cateId || 0),
            type: Number(d?.type || 1),
            nhan: String(d?.text || ""),
            url_xem_truoc: String(d?.stickerUrl || d?.stickerWebpUrl || d?.uri || ""),
          })).filter((s) => s.id);
        }
      }
      return send(res, 200, { ket_qua });
    }
    if (req.method === "GET" && url.pathname === "/ban-be") {
      // Danh sách bạn bè THẬT qua zca-js getAllFriends (mục 9.5) — không chế dữ liệu.
      if (!requireApi(res)) return;
      if (typeof api.getAllFriends !== "function") return send(res, 501, { thong_bao: "Thư viện zca-js hiện tại không hỗ trợ lấy danh sách bạn bè (không có getAllFriends)" });
      const friends = await api.getAllFriends();
      const ban_be = (Array.isArray(friends) ? friends : []).map((f) => ({
        id: String(f?.userId || f?.uid || ""),
        ten_hien_thi: String(f?.displayName || f?.zaloName || ""),
        avatar_url: String(f?.avatar || ""),
      })).filter((f) => f.id);
      return send(res, 200, { ban_be });
    }
    if (req.method === "POST" && url.pathname === "/ngat-lien-ket") {
      // Ngắt LIÊN KẾT hẳn (mục 9.4): dừng listener + XÓA credentials đã lưu.
      // zca-js không có API logout phía server Zalo — thao tác này ngắt phiên
      // local thật: muốn kết nối lại phải quét QR và đăng nhập lại từ đầu.
      try { api?.listener?.stop?.(); } catch {}
      api = null;
      try {
        const credPath = path.join(DATA_DIR, "credentials.json");
        if (fs.existsSync(credPath)) fs.unlinkSync(credPath);
        if (fs.existsSync(QR_PATH)) fs.unlinkSync(QR_PATH);
      } catch {}
      thongTinTaiKhoan = { tai_khoan_id: "", ten_tai_khoan: "", avatar_url: "", phien_bat_dau_luc: null };
      state = { trang_thai: "chua_dang_nhap", thong_bao: "Đã ngắt liên kết và xóa phiên đăng nhập đã lưu", qr_base64: "", qr_updated_at: null };
      return send(res, 200, publicState());
    }
    if (req.method === "POST" && url.pathname === "/gui-sticker") {
      // Gửi sticker THẬT qua zca-js sendSticker({id, cateId, type}, threadId, type)
      // — đã kiểm chứng dist/apis/sendSticker.d.ts.
      // Body chuẩn: {thread_id, loai_thread, sticker:{id, cate_id, type}}
      // (backend dùng cate_id snake_case, sidecar ánh xạ sang cateId của thư viện;
      // vẫn nhận định dạng cũ {sticker_id, cate_id, sticker_type, thread_type}).
      if (!requireApi(res)) return;
      if (typeof api.sendSticker !== "function") return send(res, 501, { thong_bao: "Thư viện zca-js hiện tại không hỗ trợ gửi sticker (không có sendSticker)" });
      const b = await readBody(req);
      const tho = (b.sticker && typeof b.sticker === "object") ? b.sticker : null;
      const sticker = tho
        ? { id: Number(tho.id || 0), cateId: Number(tho.cateId ?? tho.cate_id ?? 0), type: Number(tho.type ?? 1) }
        : { id: Number(b.sticker_id || 0), cateId: Number(b.cate_id || 0), type: Number(b.sticker_type || 1) };
      const threadId = String(b.thread_id || b.threadId || "");
      if (!threadId) return send(res, 400, { thong_bao: "Thiếu thread_id" });
      if (!sticker.id) return send(res, 400, { thong_bao: "Thiếu sticker: cần {id, cate_id, type} của sticker" });
      await api.sendSticker(sticker, threadId, b.loai_thread ?? b.thread_type ?? 0);
      return send(res, 200, { thanh_cong: true });
    }
    return send(res, 404, { thong_bao: "Không tìm thấy đường dẫn" });
  } catch (e) {
    return send(res, 500, { thong_bao: `Lỗi dịch vụ Zalo cá nhân: ${e?.message || "không rõ"}` });
  }
});
server.listen(PORT, () => console.log(`Dịch vụ Zalo cá nhân đang chạy tại http://localhost:${PORT} (zca-js: ${ZaloCtor ? "đã cài" : "chưa cài"})`));
