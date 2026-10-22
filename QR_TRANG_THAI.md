# Trạng thái QR đăng nhập Zalo cá nhân

Cập nhật lúc: **2026-10-22 15:20:50 (Asia/Ho_Chi_Minh)** — 08:20:50 UTC (QR mới nhất, tạo lúc 15:20:49 giờ Việt Nam)

## Kết quả: ĐÃ TẠO ĐƯỢC MÃ QR THẬT ✅

- **Đường dẫn file QR:** `/home/hatch/workspace/zalo-ai-hub/connectors/zalo-personal/data/qr.png`
  (đường dẫn tương đối trong repo: `connectors/zalo-personal/data/qr.png` — thư mục này đã gitignore, không commit)
- **Định dạng:** PNG 399×399, 16.938 byte, quyền file 600.
- **Thời gian tạo QR:** 2026-10-22T08:20:49.866Z (15:20:49 giờ Việt Nam), trường `qr_updated_at` do sidecar trả về.
- **Đã xác minh lại ngay trước bàn giao:** `GET /trang-thai` = `cho_quet`, `GET /suc-khoe` = khỏe + zca-js `da_cai`, sidecar PID còn sống.
- Ghi chú trung thực: QR đợt 15:12 đã hết hạn vì không được quét (zca-js báo "Cannot get scan result") — đây là QR mới tạo thay thế. Nếu QR này cũng hết hạn trước khi người dùng quét, tạo lại theo lệnh ở mục dưới (mất ~5 giây).
- **Trạng thái sidecar lúc tạo:** `cho_quet` — "Hãy quét mã QR bằng ứng dụng Zalo".
- **GET /suc-khoe:** `{"trang_thai":"khoe","thu_vien_zca_js":"da_cai"}` (zca-js 2.2.0, `npm install` thành công, `node --check src/index.js` OK).
- **Sidecar đang chạy nền bền:** PID ghi tại `connectors/zalo-personal/data/sidecar.pid`, log tại `connectors/zalo-personal/data/sidecar.log`, cổng 8791.
  Lệnh chạy lại nếu cần: `cd connectors/zalo-personal && nohup node src/index.js > data/sidecar.log 2>&1 &`

## ⚠️ Lưu ý hết hạn — đọc trước khi gửi cho người dùng

Mã QR Zalo **hết hạn rất nhanh** (lần thử trước, QR không được quét đã chuyển sang lỗi
"Đăng nhập QR thất bại: Cannot get scan result"). Nếu lúc người dùng quét mà QR trên đã hết hạn,
main agent chỉ cần tạo QR mới rồi gửi lại ngay:

```bash
curl -X POST http://localhost:8791/dang-nhap-qr
sleep 5   # QR sinh sau ~3-5 giây, file ghi vào connectors/zalo-personal/data/qr.png
curl http://localhost:8791/trang-thai   # phải thấy trang_thai = cho_quet
```

Sau khi người dùng quét và xác nhận trên điện thoại, trạng thái chuyển:
`cho_quet` → `da_quet_cho_xac_nhan` → `da_ket_noi`, và credentials được sidecar lưu tại
`connectors/zalo-personal/data/credentials.json` (chmod 600, gitignore) để khôi phục phiên.

## Cách người dùng quét

Mở ứng dụng Zalo trên điện thoại → biểu tượng QR ở ô tìm kiếm → quét ảnh `qr.png` → bấm xác nhận đăng nhập.
Đây là thư viện **không chính thức** (zca-js), có rủi ro bị Zalo hạn chế/khóa tài khoản — nên dùng tài khoản phụ để thử nghiệm.
