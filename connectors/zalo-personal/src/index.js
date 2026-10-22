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

function saveFile600(file, data) {
  fs.writeFileSync(file, data);
  try { fs.chmodSync(file, 0o600); } catch {}
}

async function forwardMessage(msg) {
  // Chỉ chuyển các trường nghiệp vụ cần thiết, không chuyển credentials/session.
  const payload = {
    external_id: String(msg?.data?.msgId || msg?.data?.cliMsgId || msg?.msgId || Date.now()),
    customer_external_id: String(msg?.threadId || msg?.data?.uidFrom || ""),
    customer_name: String(msg?.data?.dName || "Khách Zalo cá nhân"),
    content: typeof msg?.data?.content === "string" ? msg.data.content : "",
  };
  if (!payload.content) return;
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
    api.listener.start();
  } catch { /* listener không khả dụng trong bản thư viện hiện tại */ }
}

async function loginQR(res) {
  if (!ZaloCtor) return send(res, 501, { trang_thai: "chua_cai_thu_vien", thong_bao: libError });
  if (state.trang_thai === "da_ket_noi" && api) return send(res, 200, publicState());
  state = { ...state, trang_thai: "cho_quet", thong_bao: "Đang tạo mã QR, hãy quét bằng ứng dụng Zalo", qr_base64: "" };
  send(res, 200, { ...publicState(), dang_tao_qr: true });
  try {
    const zalo = new ZaloCtor();
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
    startListener();
  } catch (e) {
    state = { ...state, trang_thai: "mat_ket_noi", thong_bao: `Đăng nhập QR thất bại: ${e?.message || "lỗi không rõ"}` };
  }
}

function publicState() {
  return { trang_thai: state.trang_thai, thong_bao: state.thong_bao, qr_base64: state.qr_base64 || "", qr_duong_dan: state.qr_base64 ? "/qr.png" : "", qr_updated_at: state.qr_updated_at, moi_truong: "ca_nhan_sidecar", canh_bao: "Thư viện không chính thức, có rủi ro bị Zalo hạn chế/khóa tài khoản" };
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
    const zalo = new ZaloCtor();
    api = await zalo.login(credentials);
    state = { ...state, trang_thai: "da_ket_noi", thong_bao: "Đã khôi phục phiên đăng nhập từ dữ liệu local" };
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
      await fn.call(api, b.icon || "HEART", dest);
      return send(res, 200, { thanh_cong: true });
    }
    if (req.method === "POST" && url.pathname === "/gui-sticker") {
      if (!requireApi(res)) return;
      if (typeof api.sendSticker !== "function") return send(res, 501, { thong_bao: "Thư viện zca-js hiện tại không hỗ trợ gửi sticker (không có sendSticker)" });
      const b = await readBody(req);
      const sticker = b.sticker || { id: Number(b.sticker_id || 0), cateId: Number(b.cate_id || 0), type: Number(b.sticker_type || 1) };
      if (!sticker.id) return send(res, 400, { thong_bao: "Thiếu sticker_id: cần id, cateId và type của sticker theo định dạng zca-js" });
      await api.sendSticker(sticker, String(b.thread_id || b.threadId || ""), b.thread_type ?? 0);
      return send(res, 200, { thanh_cong: true });
    }
    return send(res, 404, { thong_bao: "Không tìm thấy đường dẫn" });
  } catch (e) {
    return send(res, 500, { thong_bao: `Lỗi dịch vụ Zalo cá nhân: ${e?.message || "không rõ"}` });
  }
});
server.listen(PORT, () => console.log(`Dịch vụ Zalo cá nhân đang chạy tại http://localhost:${PORT} (zca-js: ${ZaloCtor ? "đã cài" : "chưa cài"})`));
