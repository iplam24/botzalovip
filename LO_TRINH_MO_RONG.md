# Lộ trình mở rộng Zalo AI Hub

Tầm nhìn của chủ sản phẩm (22/10/2026): bot không chỉ trả lời — bot là nhân viên số tự vận hành: tự thu thập thông tin khách hàng, lưu trữ có cấu trúc, xuất báo cáo, chủ động thông báo cho admin, và liên tục mở rộng thêm chức năng theo nhu cầu thực tế. Kiến trúc modular monolith + Tool Registry + hệ thống quy tắc hiện tại là nền để mở rộng mà không viết lại lõi.

## Giai đoạn mở rộng 1 — Dữ liệu khách hàng & thông báo (ưu tiên ngay sau deploy)

### 1. Bot tự thu thập thông tin khách hàng
- Tự trích xuất từ hội thoại: họ tên, số điện thoại, email, nhu cầu/dịch vụ quan tâm, ngân sách, thời gian mong muốn, địa chỉ/khu vực, ghi chú đặc biệt.
- Phương pháp: bộ trích xuất quy tắc cho dữ liệu có mẫu rõ (SĐT Việt Nam, email) + gọi AI trích xuất có cấu trúc (JSON schema) cho nhu cầu/ngữ cảnh; kết quả AI phải qua kiểm tra định dạng trước khi lưu.
- Lưu vào bảng riêng "Thông tin thu thập" gắn với khách hàng: trường dữ liệu, giá trị, nguồn tin nhắn, thời điểm, độ tin cậy, trạng thái xác minh. Không ghi đè im lặng khi có mâu thuẫn — tạo bản ghi mới và đánh dấu cần kiểm tra.
- Bot biết hỏi bổ sung khi thiếu trường quan trọng theo cấu hình từng dịch vụ (ví dụ: thiếu SĐT thì hỏi xin số để tư vấn viên liên hệ), không hỏi dồn, không lặp lại câu đã hỏi.
- Trang quản trị: xem/sửa/xác minh thông tin thu thập theo từng khách, lọc khách đã đủ/thiếu thông tin.

### 2. Xuất Excel
- Xuất danh sách khách hàng và thông tin thu thập ra .xlsx (openpyxl): chọn cột, lọc theo nhãn/thời gian/dịch vụ, tiếng Việt có dấu, tên cột tiếng Việt.
- Áp dụng cho cả báo cáo hội thoại/thống kê khi cần.

### 3. Thông báo cho admin
- Sự kiện được thông báo (cấu hình bật/tắt từng loại): khách hàng mới, khách để lại SĐT, thu thập đủ thông tin, khách yêu cầu gặp nhân viên, khiếu nại/từ khóa khẩn, bot không trả lời được, lỗi hệ thống/connector.
- Kênh: Trung tâm thông báo trong giao diện quản trị (đã có khung thiết kế) + gửi tin Zalo tới tài khoản/nhóm admin được cấu hình (dùng chính connector cá nhân, có giới hạn tần suất chống spam) + tùy chọn email sau này.
- Mỗi thông báo có mức độ, liên kết tới hội thoại liên quan, trạng thái đã đọc/đã xử lý.

## Giai đoạn mở rộng 2 — Vận hành thông minh hơn
- Chấm điểm khách tiềm năng (lead scoring) theo quy tắc + dữ liệu thu thập.
- Nhắc việc/theo dõi tự động: khách chưa phản hồi sau X giờ, lịch hẹn, hạn xử lý.
- Báo cáo định kỳ tự gửi admin (ngày/tuần) qua Zalo/email.
- Tìm kiếm ngữ nghĩa pgvector cho kho tri thức và bộ nhớ; nhập PDF/DOCX/XLSX vào kho tri thức.
- Hàng đợi Redis + worker thật cho tác vụ nền; workflow kéo-thả.

## Giai đoạn mở rộng 3 — Nền tảng mở
- Plugin/Tool Registry đầy đủ: đăng ký công cụ mới qua interface chuẩn (đã có khung), quản lý quyền theo vai trò.
- Tích hợp ngoài: Google Sheets/CRM, webhook ra/vào có chữ ký, API công khai cho đối tác.
- Đa tài khoản Zalo, đa doanh nghiệp (multi-tenant) khi có nhu cầu thật.

## Nguyên tắc giữ nguyên ở mọi giai đoạn
- Không làm giả tính năng; mọi trạng thái phải thật và kiểm thử được.
- Dữ liệu khách hàng chỉ thu thập khi cần cho nghiệp vụ, có nguồn gốc rõ ràng và xuất/xóa được theo yêu cầu.
- Mọi hành động tự động có giới hạn tần suất, nhật ký và khả năng tắt.
