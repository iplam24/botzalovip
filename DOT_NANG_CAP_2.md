# Đợt nâng cấp 2 — theo yêu cầu của LAM (22/10/2026 16:18)

Thực hiện SAU khi Giai đoạn mở rộng 1 (thu thập thông tin + Excel + thông báo admin) hoàn tất và pass test, để tránh hai đợt sửa cùng lúc vào một codebase.

## 1. Đăng nhập chỉ bằng username
- Tài khoản người dùng có trường `username` riêng (duy nhất). Màn hình đăng nhập và API đăng nhập chỉ cần nhập **username** — bỏ bước mật khẩu (giữ cột mật khẩu trong DB nhưng không dùng kiểm tra nữa, để sau này bật lại được).
- Admin mặc định: username `admin` (gán cho tài khoản admin hiện có bằng migration nhẹ). Trang Người dùng: quản lý username, vai trò, trạng thái khóa/mở.
- Lưu ý hiển thị rõ trong UI đây là đăng nhập nội bộ đơn giản theo lựa chọn của chủ hệ thống.

## 2. Icon Font Awesome toàn giao diện
- Nhúng Font Awesome (bản CDN hoặc package npm `@fortawesome/fontawesome-free`) và thay toàn bộ icon/emoji rời rạc trong menu + các trang bằng icon Font Awesome nhất quán (Tổng quan: gauge, Hội thoại: comments, Khách hàng: users, AI: robot, Tri thức: book, Dịch vụ: tags, Bộ nhớ: brain, Tự động hóa: bolt, Thông báo: bell, Nhật ký: list, Sao lưu: database, Cài đặt: gear...).
- Nút bấm chính có icon đi kèm; trạng thái dùng icon + màu thống nhất.

## 3. Quản trị sâu từng chức năng
- Mỗi module có trang cài đặt riêng sâu hơn: cấu hình hành vi bot (độ dài trả lời, giọng điệu, giờ hoạt động, từ khóa cấm), cấu hình thu thập thông tin (trường bắt buộc theo dịch vụ), cấu hình thông báo (bật/tắt từng loại, kênh, tần suất), cấu hình nhóm Zalo (nhóm nào bot được hoạt động).
- Mọi cấu hình lưu vào system_settings, có nút khôi phục mặc định, thay đổi có hiệu lực ngay không cần khởi động lại.

## 4. Bot thả tim tin nhắn (bật/tắt được)
- Cài đặt `bot_tha_tim` (mặc định TẮT): khi BẬT, bot thả reaction ❤ (tim) vào tin nhắn của khách trước/trong lúc trả lời — qua zca-js (kiểm tra API reaction trong thư viện: addReaction/sendReaction; nếu thư viện không hỗ trợ thật thì ghi rõ vào báo cáo, không fake).
- Áp dụng cả tin 1-1; trong nhóm chỉ thả tim khi bot được tag đúng điều kiện mục 7.

## 5. Gửi tin chia nhỏ như người thật
- Câu trả lời dài được tách thành nhiều tin liên tiếp: ưu tiên tách theo đoạn (xuống dòng), câu; mỗi tin tối đa ~300-400 ký tự; giữ thứ tự; nghỉ ngắn giữa các tin (cấu hình `do_tre_giua_cac_tin_ms`, mặc định ~700ms) và có thể bật hiệu ứng "đang soạn tin" nếu zca-js hỗ trợ.
- Áp dụng ở connector cá nhân (chia ở backend trước khi gửi: orchestrator chia text thành danh sách đoạn, connector gửi lần lượt; trạng thái tin ghi đầy đủ từng phần, lỗi phần nào ghi rõ phần đó).
- Cài đặt bật/tắt `gui_tin_chia_nho` + độ dài tối đa mỗi phần.

## 6. Chuẩn hoá định dạng văn bản AI trước khi gửi Zalo
- Zalo không render Markdown → tiền xử lý mọi câu trả lời AI trước khi gửi/lưu hiển thị:
  - `## Tiêu đề` / `#`, `###` → tiêu đề dạng chữ thường sạch, bỏ ký tự `#` (có thể viết hoa chữ đầu + xuống dòng rõ ràng).
  - `**đậm**` → bỏ dấu `**`, giữ nội dung (Zalo cá nhân không có bold thật qua API này — không chèn ký tự lạ).
  - `*nghiêng*` / `_nghiêng_` → bỏ ký tự bao, giữ nội dung.
  - Gạch đầu dòng `-`, `*` → đổi thành `• `; bảng Markdown → chuyển thành danh sách dòng "Tên: giá trị"; link `[chữ](url)` → `chữ (url)` hoặc nguyên url; code block/inline → bỏ backtick.
- Hàm format dùng chung `dinh_dang_tin_zalo(text)` ở backend, có test đơn vị cho từng trường hợp; giao diện quản trị hiển thị bản đã chuẩn hoá.

## 7. Hành vi trong nhóm Zalo
- Trong hội thoại NHÓM: bot CHỈ trả lời khi được tag/nhắc đích danh tài khoản bot (mention chứa đúng UID của tài khoản đăng nhập) hoặc chứa tên hiển thị của bot theo cấu hình `ten_bot_trong_nhom`.
- TUYỆT ĐỐI không trả lời khi `@all`/tag tất cả (mention toàn nhóm, vd uid -1) hoặc tin nhóm không nhắc tới bot — mặc định im lặng, chỉ ghi log "bo_qua_nhom_khong_tag".
- Cài đặt `bot_nhom_chi_khi_duoc_tag` (mặc định BẬT) + danh sách nhóm được phép (trống = mọi nhóm có tag đúng).
- Cần lấy trường mentions từ payload zca-js (data.mentions: [{uid, pos, len}]) và UID của chính tài khoản (đã có từ login: own ID) để so sánh; sidecar chuyển mentions lên backend qua webhook payload.

## 8. Giao diện đẹp hơn, mượt hơn
- Tinh chỉnh design system: khoảng cách, bo góc, bóng đổ nhẹ, màu thương hiệu nhất quán, dark sidebar + nền sáng; font chữ rõ ràng (Inter/Be Vietnam Pro cho tiếng Việt).
- Hiệu ứng chuyển trang/chuyển tab nhẹ (transition 150-200ms), skeleton/loading khi tải dữ liệu, toast thông báo khi thao tác thành công/thất bại thay alert thô.
- Tối ưu: build code-splitting theo trang (lazy import), giảm re-render danh sách dài (ảo hoá nếu cần ở trang Hội thoại/Khách hàng), kiểm tra lại bundle size sau build.
- Không đổi cấu trúc điều hướng hiện tại một cách vô cớ; giữ toàn bộ nhãn tiếng Việt.

## Kiểm thử bắt buộc của đợt
- Test đăng nhập chỉ username (đúng/sai username, tài khoản bị khóa).
- Test hàm định dạng: ##, **, bảng, link, list.
- Test chia tin: text dài → đúng số phần, thứ tự, giới hạn ký tự; tắt tính năng thì gửi 1 tin.
- Test logic nhóm: mention đúng UID bot → trả lời; mention @all → im lặng; không mention → im lặng; tin 1-1 không đổi hành vi.
- Test thả tim: tắt → không gọi API reaction; bật → gọi đúng 1 lần/tin (mock connector/sidecar stub).
- Toàn bộ test cũ + test của Giai đoạn mở rộng 1 vẫn pass; frontend build thành công.
