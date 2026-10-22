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

## 9. Bổ sung (LAM thêm lúc 16:23 cùng ngày)

### 9.1 Bật/tắt provider nhanh
- Trong danh sách Nhà cung cấp AI: nút gạt bật/tắt `is_active` ngay tại danh sách (không cần mở form), endpoint PATCH riêng cho thao tác này.
- Provider đang tắt: không được dùng khi gửi tin; nếu tắt provider đang là mặc định thì UI cảnh báo và yêu cầu chọn mặc định khác (hoặc tự gỡ cờ mặc định + báo rõ). Trạng thái tắt hiển thị xám + nhãn "Đang tắt".

### 9.2 Hiển thị hội thoại đã nhắn tin
- Trang Hội thoại: bộ lọc Tất cả / Đã nhắn tin (có từ 1 tin trở lên) / Chưa nhắn; mỗi dòng hiện số lượng tin, tin cuối + thời gian tin cuối, sắp xếp theo hoạt động gần nhất. Áp dụng mọi kênh (mô phỏng + cá nhân).

### 9.3 Xem người dùng (user)
- Trang Người dùng hoàn chỉnh: danh sách + chi tiết gồm username, họ tên, email (nếu có), vai trò, trạng thái hoạt động/khóa, lần đăng nhập cuối (ghi `last_login_at` khi đăng nhập bằng username), số khách hàng và số bạn bè Zalo được phân bổ phụ trách.

### 9.4 Xem tài khoản đang liên kết
- Trang Tài khoản Zalo: hiển thị danh sách tài khoản đang liên kết lấy từ trạng thái thật của sidecar (tên hiển thị nếu lấy được, ID tài khoản, trạng thái kết nối, thời điểm bắt đầu phiên). Cấu trúc sẵn sàng cho nhiều tài khoản (danh sách, không hard-code 1 mục). Có nút "Ngắt liên kết" — chỉ hoạt động thật khi sidecar hỗ trợ đăng xuất/xóa phiên (thêm endpoint tương ứng); nếu chưa hỗ trợ thì không hiển thị nút giả.

### 9.5 Phân bổ admin cho danh sách bạn bè Zalo
- Sidecar: endpoint lấy danh sách bạn bè của tài khoản đang đăng nhập (kiểm tra zca-js có API kiểu getAllFriends/fetchAllFriend — dùng đúng API thật của thư viện, không chế dữ liệu). Mỗi bạn: id, tên hiển thị, avatar (nếu có).
- Backend: bảng `phan_bo_ban_be` (zalo_friend_id duy nhất, ten_hien_thi, avatar_url, admin_user_id nullable, ghi_chu, updated_at) + endpoint đồng bộ bạn bè từ sidecar (upsert, không xóa phân bổ đã có), API gán/đổi/bỏ admin phụ trách cho 1 bạn và cho nhiều bạn cùng lúc, lọc theo admin/trạng thái phân bổ.
- Vận hành: khi một người bạn trong danh sách nhắn tin tới, khách hàng/hội thoại tương ứng được gắn admin phụ trách theo phân bổ (chỉ khi chưa có người phụ trách).
- Frontend: trang "Bạn bè Zalo" riêng (menu có icon Font Awesome): bảng bạn bè, cột Admin phụ trách (dropdown chọn nhân viên), tìm kiếm theo tên, lọc Chưa phân bổ/Đã phân bổ/từng admin, thống kê số bạn theo admin, nút Đồng bộ từ Zalo.
- Nếu thư viện không lấy được danh sách bạn bè: hiển thị trạng thái thật trên trang + ghi rõ vào báo cáo nghiệm thu, không fake dữ liệu.

## 10. Trả lời linh hoạt, chống "một motip" (LAM phàn nàn 16:26 — ƯU TIÊN CAO)

Chẩn đoán đã xác minh trong code hiện tại: (a) SYSTEM_PROMPT là một câu cứng chung chung; (b) `generate_reply` KHÔNG truyền lịch sử hội thoại cho provider thật — mỗi tin model coi như cuộc mới nên chào lại, lặp thông tin, kết câu khuôn mẫu; (c) không gửi `temperature` và không dùng `max_tokens` đã cấu hình; (d) ngữ cảnh tri thức bị dán thẳng vào câu hỏi của khách.

Yêu cầu sửa trong `ai_gateway.generate_reply` + orchestrator:
- **Truyền lịch sử thật**: orchestrator truyền ~10 tin gần nhất của hội thoại (role user/assistant) vào mảng messages theo đúng thứ tự; ngữ cảnh tri thức + bộ nhớ chuyển vào phần system, không dán vào câu hỏi.
- **System prompt mới theo persona + luật chống motip**: nhân viên chat Zalo như người thật — bắt nhịp cách nói của khách, không chào lại giữa cuộc, không mở đầu bằng câu mẫu ("Dạ chào bạn", "Rất vui được hỗ trợ"), không kết câu khuôn mẫu, trả lời gọn đúng trọng tâm, hỏi ngược thông minh theo ngữ cảnh, đa dạng cách diễn đạt giữa các lượt.
- **Cấu hình được trong Cài đặt** (nhóm "Phong cách trả lời"): `bot_ten_hien_thi`, `bot_cach_xung_ho` (mặc định em/bạn), `bot_giong_dieu` (tự nhiên thân thiện / lịch sự trang trọng / ngắn gọn thẳng thắn — mỗi giọng một đoạn hướng dẫn phong cách riêng trong prompt), `ai_temperature` (mặc định 0.85, khoảng 0-1.5), `ai_do_dai_tra_loi` (ngắn/vừa/chi tiết), `prompt_bo_sung` (đoạn hướng dẫn riêng admin tự thêm).
- **Payload provider**: gửi kèm `temperature` theo cài đặt và `max_tokens` từ cấu hình provider (trước đây bị bỏ quên).
- **Mock provider**: mỗi intent có 2-3 biến thể câu trả lời chọn luân phiên để bản demo cũng không motip.
- Test: monkeypatch http client bắt payload kiểm chứng có đủ lịch sử + temperature + max_tokens; system prompt chứa tên bot/giọng từ cài đặt và luật chống motip; ngữ cảnh nằm ở system không nằm ở user; đổi giọng trong cài đặt làm prompt thay đổi tương ứng.
- Đã kiểm chứng A/B với provider thật (22/10): prompt cũ trả "Dạ chào bạn..." + lặp toàn bộ thông tin ở lượt 3; prompt mới + lịch sử + temperature 0.85 trả ngắn gọn tự nhiên, nhớ ngữ cảnh, gợi ý bước tiếp theo.

## 11. Responsive + Trung tâm cấu hình toàn diện trên UI (LAM thêm 16:29)

### 11.1 Responsive toàn diện
- Toàn bộ giao diện quản trị dùng tốt trên điện thoại/tablet/desktop: sidebar thu gọn thành menu trượt trên màn nhỏ, bảng dữ liệu chuyển dạng thẻ (card) hoặc cuộn ngang có kiểm soát, nút/chữ đủ lớn để chạm, form 1 cột trên mobile, header + chuông thông báo co gọn hợp lý. Kiểm tra ở các mốc 375px / 768px / 1280px, không vỡ layout, không tràn ngang.

### 11.2 Nguyên tắc "cấu hình mọi thứ trên UI, không build lại"
- Mở rộng thành **registry cài đặt**: mỗi khóa cài đặt có khai báo {nhóm, nhãn tiếng Việt, mô tả, kiểu (text/number/bool/select/textarea/màu/thời gian), giá trị mặc định, ràng buộc}. API cài đặt trả về theo registry; trang Cài đặt tự sinh控件 theo đúng kiểu; mọi thay đổi lưu DB và có hiệu lực ngay ở lần xử lý tiếp theo (đọc runtime, không cache cứng, không cần khởi động lại, tuyệt đối không cần sửa code/build lại khi đổi cấu hình).
- Chuyển hết các hằng số đang nằm rải rác trong code thành cài đặt có mặc định bằng giá trị hiện tại: số tin lịch sử truyền cho AI, độ trễ chia tin, độ dài tối đa mỗi phần tin, cửa sổ chống trùng thông báo (10 phút), khoảng cách gửi thông báo Zalo admin (60 giây), intent được hỏi SĐT, ngưỡng tự chuyển nhân viên, giờ hoạt động của bot (ngoài giờ → câu trả lời ngoài giờ cấu hình được), tin nhắn chào khách mới, tin nhắn khi bot không trả lời được, thông tin doanh nghiệp (tên, địa chỉ, hotline, giờ mở cửa — đưa vào ngữ cảnh AI), bật/tắt từng module lớn (thu thập thông tin, thông báo Zalo admin, thả tim, chia tin, bot trong nhóm...).
- Trang Cài đặt làm lại theo phong cách cao cấp: menu nhóm bên trái (hoặc tab có icon Font Awesome), ô tìm kiếm cài đặt, thẻ nhóm có mô tả, nút gạt/toggle đẹp cho boolean, nút Lưu theo nhóm + Khôi phục mặc định theo nhóm, hiển thị "đã lưu lúc..." — sành điệu, nhất quán với design system của mục 8.
- Bí mật (khóa API, connector secret) KHÔNG đưa vào registry này — vẫn ở trang chuyên biệt với hiển thị che.

## Kiểm thử bắt buộc của đợt
- Test đăng nhập chỉ username (đúng/sai username, tài khoản bị khóa).
- Test hàm định dạng: ##, **, bảng, link, list.
- Test chia tin: text dài → đúng số phần, thứ tự, giới hạn ký tự; tắt tính năng thì gửi 1 tin.
- Test logic nhóm: mention đúng UID bot → trả lời; mention @all → im lặng; không mention → im lặng; tin 1-1 không đổi hành vi.
- Test thả tim: tắt → không gọi API reaction; bật → gọi đúng 1 lần/tin (mock connector/sidecar stub).
- Toàn bộ test cũ + test của Giai đoạn mở rộng 1 vẫn pass; frontend build thành công.
