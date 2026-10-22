# Dịch vụ phụ Zalo cá nhân (zca-js)

Sidecar Node.js kết nối tài khoản Zalo **cá nhân** bằng thư viện **không chính thức** `zca-js`, phục vụ backend Zalo AI Hub qua HTTP nội bộ.

> ⚠️ **Cảnh báo rủi ro:** Đây không phải API chính thức của Zalo. Việc sử dụng có thể khiến tài khoản bị hạn chế hoặc khóa. Không bypass CAPTCHA/OTP — đăng nhập do chính người dùng quét QR và xác nhận trên điện thoại.

## Cài đặt và chạy

```bash
cd connectors/zalo-personal
npm install
cp .env.example .env   # đặt CONNECTOR_SECRET trùng với ZALO_CONNECTOR_SECRET của backend (nếu dùng)
npm start              # mặc định http://localhost:8791
```

Nếu chưa chạy `npm install`, dịch vụ vẫn khởi động nhưng các endpoint nghiệp vụ trả `501` với lý do tiếng Việt và trạng thái `chua_cai_thu_vien` — không giả vờ đã kết nối.

## API nội bộ

| Phương thức | Đường dẫn | Mô tả |
|---|---|---|
| POST | `/dang-nhap-qr` | Tạo QR đăng nhập, trả trạng thái + QR (base64/đường dẫn `/qr.png`) |
| GET | `/trang-thai` | `cho_quet` / `da_quet_cho_xac_nhan` / `da_ket_noi` / `qr_het_han` / `mat_ket_noi` / `chua_cai_thu_vien` |
| POST | `/gui-tin-nhan` | Gửi tin nhắn văn bản `{thread_id, content}` |
| POST | `/tha-cam-xuc` | Thả cảm xúc nếu bản zca-js hỗ trợ, không thì `501` kèm lý do tiếng Việt |
| POST | `/gui-sticker` | Gửi sticker nếu bản zca-js hỗ trợ, không thì `501` kèm lý do tiếng Việt |
| POST | `/ngat-ket-noi` | Ngắt listener và đăng xuất phiên trong bộ nhớ |
| GET | `/suc-khoe` | Kiểm tra dịch vụ + thư viện đã cài chưa |

Tin nhắn đến được chuyển về `POST {BACKEND_URL}/api/zalo/webhook/ca-nhan` kèm header `X-Connector-Secret` (lấy từ env, không ghi vào log).

## Dữ liệu phiên

Session/credentials chỉ nằm trong `data/` (quyền thư mục 700, file 600, đã có trong `.gitignore`). **Tuyệt đối không commit, không chia sẻ, không ghi vào log.**
