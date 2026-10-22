# Giới hạn tích hợp Zalo (bắt buộc đọc)

## Đã xác minh theo thiết kế MVP
- **Zalo OA (Official Account):** Có API chính thức, nhưng cần tài khoản OA, ứng dụng (app) được phê duyệt, token truy cập OA và tuân thủ chính sách Zalo. Thiếu các điều kiện này, hệ thống báo **CHƯA HỖ TRỢ** qua `ZaloOAStubConnector`, không giả vờ đã kết nối.
- **Tài khoản Zalo cá nhân:** **Không có API công khai chính thức** cho việc tự động nhận/gửi tin nhắn như OA. Không mặc định cá nhân và OA có cùng khả năng.
- **Không thực hiện:** vượt CAPTCHA, vượt OTP, thu thập phiên đăng nhập không an toàn, lưu mật khẩu Zalo dạng văn bản. Các hành động này nằm ngoài phạm vi và bị cấm trong dự án.
- Một số thao tác (thả cảm xúc, gửi sticker, gửi tệp/hình) chỉ khả thi khi connector thực tế hỗ trợ; interface đã có nhưng Mock/OA Stub sẽ ném lỗi `Chưa hỗ trợ` rõ ràng.

## Trong MVP hiện tại
| Connector | Trạng thái | Dùng cho |
|---|---|---|
| MockZaloConnector | Đã triển khai + kiểm thử | Phát triển, kiểm thử tự động, demo luồng hội thoại |
| ZaloOAStubConnector | Stub - chưa hỗ trợ gọi API thật | Giữ interface, ghi rõ điều kiện cần (OA token/app) |

## Điều kiện để triển khai thật
1. Đăng ký Zalo OA và app, lấy token hợp lệ qua kênh chính thức của Zalo.
2. Viết adapter mới tuân interface `ZaloConnector` (connect/disconnect/status/send_text/...), kiểm thử trên tài khoản OA thử nghiệm.
3. Không thay đổi interface của orchestrator - chỉ thay connector.

## Cập nhật: Zalo cá nhân + đăng nhập QR qua zca-js (theo lựa chọn của người dùng)

Người dùng đã chọn dùng **tài khoản Zalo cá nhân** và tự quét QR. Triển khai qua
dịch vụ phụ (sidecar) Node.js tại `connectors/zalo-personal/` dùng thư viện
**zca-js** — đây là thư viện **không chính thức**, không phải API của Zalo.

- **Rủi ro đã công bố rõ:** tài khoản có thể bị Zalo **hạn chế hoặc khóa** khi
  dùng thư viện không chính thức. Giao diện trang Tài khoản Zalo hiển thị cảnh
  báo này trước khi tạo QR.
- **Đăng nhập QR:** sidecar tạo QR (`POST /dang-nhap-qr`), giao diện hiển thị
  QR và polling trạng thái: Chờ quét → Đã quét, chờ xác nhận trên điện thoại →
  Đã kết nối / QR hết hạn. Người dùng tự quét và xác nhận trên điện thoại.
- **Không bypass CAPTCHA/OTP**, không lưu mật khẩu Zalo. Nếu Zalo yêu cầu
  xác thực bổ sung, người dùng tự thực hiện trên điện thoại.
- **Session/credentials** của zca-js chỉ lưu tại `connectors/zalo-personal/data/`
  (chmod 600, đã đưa vào `.gitignore`), không commit, không ghi vào log.
- **Không fake kết nối:** nếu sidecar chưa chạy hoặc chưa cài zca-js, backend
  báo "Mất kết nối / Chưa chạy dịch vụ Zalo cá nhân" (sidecar trả
  `chua_cai_thu_vien` kèm lý do), không bao giờ báo "Đã kết nối" giả.
- **Thao tác theo khả năng thư viện:** gửi tin nhắn dùng `sendMessage`; thả
  cảm xúc dùng `addReaction` và gửi sticker dùng `sendSticker` của zca-js 2.x —
  nếu bản thư viện không hỗ trợ, endpoint trả `501` kèm lý do tiếng Việt.
- Tin nhắn thật được sidecar chuyển về `POST /api/zalo/webhook/ca-nhan` kèm
  header `X-Connector-Secret` (lấy từ env, không log secret).
