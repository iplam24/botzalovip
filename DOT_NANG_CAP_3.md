# Đợt nâng cấp 3 — hàng đợi yêu cầu (LAM dặn "cứ làm từ từ", 22/10/2026 17:06)

Làm sau khi hoàn tất: chế độ trò chuyện tự do + đính chính đăng nhập username/mật khẩu + nút Lưu nổi bật.

## 1. Phân trang cho các danh sách dài
- Áp dụng mọi danh sách có thể dài: Hội thoại, Khách hàng, Bạn bè Zalo, Thông báo, Nhật ký hệ thống, Thông tin thu thập, Bộ nhớ AI, Kho tri thức.
- Chuẩn chung: phân trang phía server (tham số `trang` + `kich_thuoc_trang`, mặc định 20, chọn được 10/20/50/100), API trả kèm tổng số bản ghi + tổng số trang; UI có thanh phân trang dùng chung (Trang trước/sau, số trang, "Hiển thị x–y / tổng z mục") + giữ nguyên bộ lọc/tìm kiếm khi chuyển trang.
- Component phân trang dùng chung ở frontend để mọi trang giống nhau; danh sách ngắn dưới 1 trang thì ẩn thanh phân trang.

## 2. Admin cấu hình qua đoạn chat
- Một khung chat "Cấu hình nhanh" trong trang quản trị (đặt ở Cài đặt và/hoặc một trang riêng "Trợ lý cấu hình"): admin gõ lệnh tự nhiên kiểu "bật chế độ trò chuyện tự do", "đặt nhiệt độ AI thành 0.7", "đổi giọng bot sang ngắn gọn", "tắt thả tim", "bot trả lời ngoài giờ là ...".
- Cách hoạt động: AI (provider đang cấu hình) phân tích câu lệnh thành {khóa cài đặt, giá trị} dựa trên registry cài đặt (53+ khóa hiện có); backend kiểm tra khóa/giá trị hợp lệ theo registry; thay đổi nào cũng hiển thị thẻ xác nhận trong chat (khóa, giá trị cũ → mới) trước khi áp dụng; áp dụng xong báo lại + ghi nhật ký hệ thống "cau_hinh_qua_chat" kèm người thực hiện.
- Lệnh mơ hồ/không khớp khóa nào: trợ lý chat trả lời lại gợi ý các lệnh mẫu, không tự bịa thay đổi. Có sẵn danh sách "lệnh mẫu" gợi ý trong UI.
- Mở rộng sau (khi ổn định): cho phép ra lệnh qua chính Zalo từ tài khoản admin được chỉ định.

## 3. Vector DB — tìm kiếm ngữ nghĩa cho tri thức + bộ nhớ (LAM thêm 17:16)
- Nền sẵn có: Postgres trên server đã là image `pgvector/pgvector:pg16` — chỉ cần `CREATE EXTENSION vector`, không thêm hệ thống mới.
- Nguồn embedding: ĐÃ KIỂM CHỨNG endpoint của LAM (68 model) KHÔNG có model embedding → dùng model embedding chạy local ngay trong backend (đa ngôn ngữ, hỗ trợ tiếng Việt tốt; ứng viên: `intfloat/multilingual-e5-small` hoặc `paraphrase-multilingual-MiniLM-L12-v2`), tải 1 lần khi khởi động/bật tính năng; đồng thời hỗ trợ cấu hình provider /embeddings tương thích OpenAI để sau này LAM có key embedding riêng thì chuyển sang. Test tự động dùng embedding giả xác định (deterministic) để pytest nhanh, không tải model thật.
- Phạm vi: cột embedding cho `knowledge_chunks` và `memories`; nhúng khi tạo/cập nhật tài liệu & ghi nhớ (hàng đợi đơn giản trong tiến trình, lỗi nhúng không chặn nghiệp vụ, có trạng thái đã/chưa nhúng + nút "Nhúng lại toàn bộ" trong UI); truy hồi ngữ nghĩa top-k hợp nhất với tìm từ khóa hiện tại khi bot trả lời (ngữ nghĩa ưu tiên khi có điểm tương đồng cao); trang Kho tri thức/Bộ nhớ hiển thị trạng thái vector (số chunk đã nhúng/tổng) và có ô test tìm kiếm ngữ nghĩa nhập câu tự nhiên.
- Cài đặt: `tim_kiem_ngu_nghia` bool mặc định BẬT khi model sẵn sàng, `so_ket_qua_ngu_nghia` mặc định 4. Nếu model local không tải được trên server (RAM/đĩa) → hệ thống tự rơi về tìm từ khóa và ghi rõ trạng thái trong UI, không âm thầm giả vờ.

## 4. Làm đẹp UI chuyên sâu (LAM thêm 17:16 — "ui vẫn xấu")
- Một đợt design pass riêng, không chỉ sửa lẻ: hệ thống màu + khoảng cách + bo góc + bóng đổ nhất quán; sidebar có điểm nhấn thương hiệu; thẻ thống kê Tổng quan có icon FA + số liệu nổi bật + biểu đồ nhỏ (hoạt động 7 ngày) nếu dữ liệu cho phép; bảng dữ liệu zebra/hover dễ đọc; khung chat Hội thoại giống ứng dụng nhắn tin thật (bong bóng, thời gian, trạng thái đã gửi); trạng thái rỗng có icon + hướng dẫn; nút/chip/badge đồng bộ; kiểm tra cả chế độ tối hiện có không bị lệch màu.
- Tiêu chí nghiệm thu: chụp/đối chiếu các trang chính ở 1280px và 375px không vỡ, không lệch tông; build pass; không đổi hành vi nghiệp vụ.

## 5. Nguyên tắc đợt
- Mỗi mục làm xong phải có test (API phân trang: tổng số/trang biên/lọc giữ nguyên; chat cấu hình: lệnh đúng → đổi thật, lệnh sai → không đổi + gợi ý, bắt buộc qua bước xác nhận).
- Không phá hành vi hiện tại; các mục độc lập nhau, xong mục nào deploy mục đó.
