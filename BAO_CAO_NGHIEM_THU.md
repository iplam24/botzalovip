# Báo cáo nghiệm thu - Zalo AI Hub MVP

Ngày: 22/10/2026 (Asia/Ho_Chi_Minh). Phương pháp: pytest + FastAPI TestClient, SQLite file. Kết quả: **29 passed** (25 cũ + 4 mới, xem mục "Cập nhật hoàn thiện" ở cuối).

## Đã triển khai và kiểm thử thành công
1. Đăng nhập quản trị + `GET /api/auth/me` (test_01)
2. Nhập/kiểm tra API key mock, key chỉ trả masked, không lộ full key (test_02, test_03, test_16)
3. Cấu hình AI lưu bền vững trong DB (test_02)
4. Tạo/quản lý dịch vụ mới (test_05)
5. Nhập dữ liệu tri thức (văn bản) + chia đoạn (test_06)
6. AI (Mock) trả lời dựa trên tri thức đã nhập, có nguồn (test_06)
7. Lưu lịch sử hội thoại (test_08)
8. Lưu và truy xuất bộ nhớ (CRUD + tự ghi sự kiện từ orchestrator) (test_08, test_09)
9. Dữ liệu tồn tại sau khi tạo session/engine mới trên cùng DB file (test_10)
10. Đổi mô hình qua API, không sửa source code (test_11)
11. Tạm dừng bot - bot không trả lời khi đã dừng (test_12)
12. Chuyển hội thoại cho nhân viên + trả lại bot (test_12)
13. Xem nhật ký hệ thống (test_13)
14. Phát hiện lỗi provider: URL/key sai -> trạng thái `loi` (test_04)
15. Phát hiện lỗi/giới hạn connector: OA stub -> `chua_ho_tro` (test_14)
16. Chống gửi trùng bằng `external_id` unique (test_08)
17. Sao lưu (ZIP/JSON, redact khóa API) và khôi phục có xác nhận (test_15)
18. Kiểm thử tự động: 20 test pytest (file này)
19. Giao diện và hướng dẫn bằng tiếng Việt: frontend đủ 14 phân hệ, README/docs tiếng Việt (kiểm tra thủ công cấu trúc file, chưa chạy e2e trình duyệt)
20. Giới hạn Zalo công bố rõ: `docs/GIOI_HAN_ZALO.md`

## Đã triển khai nhưng chưa kiểm thử đầy đủ
- Adapter OpenAI-compatible (gọi `/models` khi kiểm tra, `/chat/completions` khi sinh trả lời): có code + test lỗi kết nối, chưa test với provider thật có key thật.
- Quy tắc tự động hóa (từ khóa/intent/nhãn -> trả lời/gắn nhãn/chuyển nhân viên/tạm dừng): có model + API + evaluate trong orchestrator; test mới bao phủ tạo quy tắc, chưa bao phủ mọi tổ hợp hành động.
- Phân tích/tổng quan từ dữ liệu thật, công cụ (Tool Registry dạng danh sách tại `/api/kiem-thu-ai/cong-cu`).
- Frontend: đã viết lại hoàn chỉnh từng trang + build thành công (xem mục "Cập nhật hoàn thiện"); chưa chạy kiểm thử e2e bằng trình duyệt thật (click qua từng màn hình với backend đang chạy).
- Alembic: có cấu trúc `alembic.ini`, `alembic/env.py`, version 0001; MVP vẫn dùng `create_all` khi khởi động, chưa test migration nâng cấp schema phức tạp.
- Docker Compose: có file với pgvector/pgvector:pg16 + redis:7 + backend + frontend + healthcheck; chưa chạy `docker compose up` trong môi trường này.

## Đang phát triển
- Workflow trực quan kéo-thả, hàng đợi Redis/worker thật (hiện xử lý đồng bộ, model Job đã có), tổng hợp bộ nhớ định kỳ, embedding/pgvector semantic search (hiện truy xuất từ khóa + chuẩn hóa không dấu), nhập PDF/DOCX/XLSX/CSV (hiện chỉ văn bản qua API).

## Chưa hỗ trợ
- Gửi hình/tệp qua connector thật; đa tài khoản Zalo thật; thông báo thời gian thực. (Kết nối Zalo cá nhân bằng QR đã chạy thật tới bước tạo QR — xem mục cập nhật; xuất báo cáo CSV đã triển khai.)

## Bị giới hạn bởi nền tảng tích hợp
- Zalo OA thật: cần OA token + app được phê duyệt (xem GIOI_HAN_ZALO). Không bypass CAPTCHA/OTP.

## Lệnh kiểm thử đã chạy
```
cd backend && python -m pytest tests/test_mvp.py -v
# 29 passed, 4 warnings (deprecation: on_event, pydantic config, anyio alias)
cd frontend && npm install && npm run build
# tsc -b && vite build: thành công, dist/assets ~248 kB JS (gzip ~71 kB)
```

## Cập nhật bổ sung (Zalo cá nhân QR + provider test lần 2)

### Đã triển khai và kiểm thử
- Parser AI 2 dạng JSON/SSE: ghép `delta.content`, lấy `usage` + model thực tế server trả (test_21).
- Gateway luôn gửi `stream: false`; AIUsage ghi đúng `prompt_tokens` provider trả (ví dụ 2277 trong test giả lập, không tự ước lượng); system prompt khóa danh tính/xưng hô — cấm model tự giới thiệu là Gemini/Google/GPT, chỉ nhận là trợ lý hỗ trợ khách hàng (test_22).
- Seed cấu hình mẫu `LAM Token - code`: không hard-code khóa API; không có env `TEST_AI_API_KEY` thì khóa rỗng + trạng thái `chua_cau_hinh` (test_23). GET /models của provider này đã được main agent test thật: 200, 68 model, có `code` (kết quả test thật phía main agent, không chạy lại trong pytest vì cần khóa thật).
- ZaloPersonalConnector proxy sidecar: sidecar offline -> `mat_ket_noi` + "Mất kết nối / Chưa chạy dịch vụ Zalo cá nhân", không fake (test_24).
- Webhook cá nhân `POST /api/zalo/webhook/ca-nhan`: kiểm tra `X-Connector-Secret` khi env đã đặt (sai -> 401), đúng -> chạy orchestrator + chống trùng (test_25).
- Sidecar Node `connectors/zalo-personal/`: đã kiểm thử chạy thật tại máy này — chưa cài zca-js thì trạng thái `chua_cai_thu_vien` + endpoint nghiệp vụ 501 tiếng Việt; cài zca-js 2.2.0 (npm install thành công) thì `/suc-khoe` báo `da_cai`, trạng thái `chua_dang_nhap`, chưa đăng nhập thì gửi tin trả 409 tiếng Việt. Chữ ký hàm đã đối chiếu với zca-js 2.2.0: `loginQR(options, callback)` (enum sự kiện số, lưu credentials khi `GotLoginInfo` vào `data/credentials.json` chmod 600), `sendMessage(message, threadId, type)`, `addReaction(icon, dest)`, `sendSticker({id,cateId,type}, threadId, type)`, `listener.on("message")`.

### Chưa hỗ trợ / chưa kiểm thử đầy đủ
- Đăng nhập QR thật với tài khoản Zalo thật: chưa thực hiện trong môi trường kiểm thử (cần người dùng quét QR + xác nhận trên điện thoại). Luồng sẵn sàng ở giao diện Tài khoản Zalo.
- Gửi sticker/thả cảm xúc qua tài khoản thật: code theo đúng chữ ký thư viện, chỉ hoạt động sau khi đã đăng nhập; chưa test với tài khoản thật.

### GitHub
- Repo đích `botzalovip`: đã `git init`, cấu hình user, thêm remote `origin` bằng URL sạch (không chứa token). Chưa push (main agent thực hiện sau khi test pass).

## Cập nhật hoàn thiện (đợt 2 — frontend hoàn chỉnh, cài đặt, CSV, QR thật)

### Frontend — đã viết lại hoàn chỉnh từng trang (không còn trang 1 dòng bọc component chung)
Mọi trang đều gọi API thật, có trạng thái đang tải / chưa có dữ liệu / lỗi / thành công, nhãn tiếng Việt:
- **Tổng quan** (110 dòng): thẻ số liệu từ `/api/tong-quan` + `/api/phan-tich`, trạng thái nhà cung cấp AI mặc định và danh sách tài khoản Zalo thật.
- **Hội thoại** (264 dòng): bố cục 2 cột — danh sách có tìm kiếm + lọc trạng thái (API hỗ trợ `tu_khoa`, `trang_thai`), khung chat theo thời gian phân biệt khách/bot/nhân viên/hệ thống, gửi tin thủ công (Enter để gửi), Tạm dừng bot / Trả lại bot / Chuyển nhân viên / Đánh dấu đã giải quyết.
- **Khách hàng** (193 dòng): bảng + tìm kiếm phía máy chủ + form thêm/sửa (tên, điện thoại, định danh Zalo, nhãn, nhóm, phụ trách, ghi chú) + xóa có xác nhận.
- **Nhà cung cấp AI** (247 dòng): thẻ cấu hình (key chỉ masked) + form đầy đủ (tên, nhà cung cấp, địa chỉ API, khóa API, model hội thoại/embedding, giới hạn token, timeout, mặc định/kích hoạt) + Kiểm tra kết nối hiện kết quả thật/lỗi thật + Vô hiệu hóa + Xóa có xác nhận.
- **Kho tri thức** (230 dòng): danh sách + xem nội dung + form nhập văn bản (tiêu đề, nội dung, dịch vụ liên quan) + ô kiểm tra truy xuất hiện đoạn + tài liệu nguồn + điểm liên quan, kèm cảnh báo khi không tìm thấy.
- **Dịch vụ** (210 dòng): bảng + tìm kiếm + form đầy đủ (tên, mã, mô tả, danh mục, giá số + giá hiển thị, chính sách, FAQ, từ khóa, trạng thái), sửa tự tăng phiên bản.
- **Bộ nhớ AI** (250 dòng): lọc theo loại ký ức/khách hàng/từ khóa phía máy chủ + form thêm/sửa (nội dung, loại, khách, độ tin cậy trượt, ghim, xác minh) + gạt nhanh Ghim/Xác minh + xóa có xác nhận.
- **Quy tắc tự động hóa** (265 dòng): thẻ quy tắc (điều kiện → hành động, ưu tiên, bật/tắt nhanh, sửa/xóa) + số lần chạy và lần chạy gần nhất từ backend + xem lịch sử chạy (`GET /api/quy-tac/{id}/lan-chay` — endpoint mới).
- **Nhật ký hệ thống** (104 dòng): lọc phía máy chủ theo mức độ / phân hệ / từ khóa.
- **Phân tích và thống kê** (143 dòng): thẻ + bảng số liệu thật theo 3 nhóm, chọn khoảng ngày (áp dụng cho tin nhắn và lượt gọi AI), nút **Xuất báo cáo CSV**.
- **Sao lưu và khôi phục** (150 dòng): Tạo sao lưu, danh sách, Khôi phục có xác nhận (gửi `xac_nhan: true`), Xóa có xác nhận (endpoint `DELETE /api/sao-luu/{id}` mới — xóa cả file).
- **Cài đặt** (147 dòng): form lưu DB qua router mới `GET/PUT /api/cai-dat` (bảng `system_settings`): tự động trả lời toàn cục, thời gian gom tin, chế độ duyệt trước khi gửi, múi giờ, số tin nhắn ngữ cảnh, tên hiển thị bot; hiện trạng thái `/api/suc-khoe`. Lưu yêu cầu quyền quản trị viên.
- **Trung tâm kiểm thử AI** (156 dòng): chọn nhà cung cấp + dịch vụ lọc tri thức, câu hỏi mẫu (kể cả không dấu/ngoài phạm vi), xem câu trả lời + mô hình thực tế + nguồn truy xuất, danh sách công cụ (Tool Registry).
- **Tài khoản Zalo** (267 dòng): đủ 3 khu — Cá nhân QR (polling 3 giây, hiện thời điểm tạo QR), Mô phỏng (gửi tin giả lập xem kết quả pipeline thật), OA stub (ghi rõ chưa hỗ trợ + điều kiện cần) + bảng tài khoản đã cấu hình + nút kiểm tra tất cả connector.
- **App.tsx** (164 dòng): thanh điều hướng thu gọn được, tìm phân hệ, header hiện trạng thái thật từ `/api/suc-khoe` (chấm xanh/đỏ, kiểm tra lại mỗi 30 giây), hiện email + vai trò người dùng.
- Component dùng chung mới `src/components/dungChung.tsx` (158 dòng): trạng thái tải/lỗi/trống, hộp xác nhận, hộp biểu mẫu, huy hiệu trạng thái. Không trang nào còn dùng `TrangDanhSach` cũ.

### Kiểm thử bổ sung (test_26 → test_29, tổng 29 passed)
- Cài đặt: đọc mặc định + lưu xuống DB và đọc lại bằng session mới (test_26).
- Xuất CSV: đúng content-type, có tiêu đề tiếng Việt, chưa đăng nhập bị chặn; phân tích theo khoảng ngày (test_27).
- Xóa sao lưu: xóa xong không còn trong danh sách (test_28).
- Lần chạy quy tắc + các bộ lọc mới (nhật ký, khách hàng, bộ nhớ) + hội thoại làm giàu dữ liệu (tên khách, tin gần nhất) + đổi trạng thái hội thoại (test_29).
- Backend làm giàu thêm: danh sách hội thoại kèm `customer_name/last_message/message_count`; khách hàng/bộ nhớ/nhật ký hỗ trợ tham số lọc — không đổi vỡ các API cũ.

### Zalo cá nhân — QR THẬT đã tạo được
- `npm install` trong `connectors/zalo-personal`: thành công (zca-js 2.2.0). `node --check src/index.js`: OK.
- Sidecar chạy nền bền bằng `nohup` (PID tại `data/sidecar.pid`, log `data/sidecar.log`), cổng 8791. `GET /suc-khoe` → `{"trang_thai":"khoe","thu_vien_zca_js":"da_cai"}`.
- `POST /dang-nhap-qr` → tạo được **ảnh QR thật** tại `connectors/zalo-personal/data/qr.png` (PNG 399×399), trạng thái `cho_quet`. Chi tiết + thời gian tạo: xem `QR_TRANG_THAI.md`.
- Giới hạn thật đã quan sát: QR **hết hạn rất nhanh** nếu không quét — lần thử đầu (không ai quét) kết thúc bằng lỗi thật của zca-js "Cannot get scan result" và trạng thái chuyển `mat_ket_noi`. Cần người dùng quét ngay khi QR được gửi; nếu hết hạn, chỉ cần gọi lại `POST /dang-nhap-qr`. Chưa kiểm thử được bước quét + xác nhận + gửi/nhận tin trên tài khoản thật (cần người dùng thao tác trên điện thoại).

### Docker Compose
- Đã rà soát bằng mắt: đủ dịch vụ `db` (pgvector/pgvector:pg16 + healthcheck + volume pgdata), `redis` (redis:7 + healthcheck), `backend` (build ./backend, depends_on healthy, volume backups), `zalo-personal` (profile `zalo`, volume data), `frontend` (build ./frontend, cổng 5173). Máy này không có Docker nên **chưa chạy `docker compose up` thật**.

### Quét bí mật
- Đã grep toàn repo (ngoài node_modules/.venv/.git) theo `sk-`, `ghp_`: chỉ còn các chuỗi kiểm thử giả trong test (`sk-secret-khong-that`, `khoa-test-khong-that`...) và khóa mẫu đã redact trong `.env.example` — không có khóa thật nào trong mã nguồn.

## Cập nhật Giai đoạn mở rộng 1 (22/10/2026) — Thu thập thông tin + Xuất Excel + Thông báo admin

Tổng kiểm thử sau đợt này: **40 passed** (32 cũ + 8 mới test_33 → test_40). Frontend build thành công (dist JS ~260,7 kB, gzip ~74,4 kB).

### 1. Bot tự thu thập thông tin khách hàng
- Bảng mới `thong_tin_thu_thap` (model `CollectedInfo`): customer_id, field (ho_ten / so_dien_thoai / email / nhu_cau / dich_vu_quan_tam / ngan_sach / thoi_gian_mong_muon / dia_chi / ghi_chu), value, source_message_id, confidence, verified, mốc thời gian. Thêm cột `email` vào `customers` (create_all + ALTER TABLE nhẹ trong seed cho DB cũ, cùng mẫu với cột channel).
- `app/services/extraction_service.py`: (a) quy tắc — SĐT di động VN (chấp nhận +84, dấu chấm/khoảng trắng/gạch ngang, chuẩn hóa về 0xxxxxxxxx, kiểm tra đầu số 03/05/07/08/09, tin cậy 0.95) + email; (b) AI — chỉ khi provider mặc định là provider thật: gọi chat/completions yêu cầu JSON thuần theo schema 6 trường, parse an toàn (lấy khối {...}, lọc đúng khóa, cắt 500 ký tự), lỗi thì bỏ qua, ghi AIUsage như gateway; Mock thì chỉ chạy quy tắc. Tin cậy AI: 0.7.
- Lưu vết đầy đủ nhưng chống trùng liên tiếp (cùng khách + trường + giá trị với bản ghi gần nhất thì bỏ qua). Chỉ điền vào trường hồ sơ Customer đang trống (phone/email/display_name), không ghi đè.
- Gắn vào orchestrator ngay sau khi lưu tin khách (chạy cả khi bot tạm dừng; lỗi chỉ ghi SystemLog module `thu_thap`, không chặn trả lời). Cập nhật luôn `last_interaction_at` của khách theo tin mới nhất.
- Hỏi bổ sung SĐT: khách chưa có SĐT + intent báo giá/tư vấn → tối đa 1 lần/hội thoại (đánh dấu bằng SystemLog). Provider thật: gợi ý trong prompt qua tham số `goi_y_hoi_sdt` của gateway; Mock: nối đúng 1 hậu tố câu hỏi vào câu trả lời (không gửi 2 tin).
- API: `GET/POST /api/khach-hang/{id}/thong-tin-thu-thap`, `PUT/DELETE /api/khach-hang/{id}/thong-tin-thu-thap/{tid}` (sửa giá trị, xác minh; trường lạ → 400).
- Frontend Khách hàng: nút **Thông tin thu thập** mở panel — bảng giá trị/độ tin cậy/nguồn tin nhắn/trạng thái xác minh + Xác minh/Sửa/Xóa + form thêm tay.

### 2. Xuất Excel (openpyxl 3.1.5, đã thêm vào requirements.txt)
- `GET /api/khach-hang/xuat-excel`: cột Họ tên, Số điện thoại, Email, Nhãn, Nhóm, Dịch vụ quan tâm, Nhu cầu, Ngân sách (lấy từ thông tin thu thập mới nhất), Lần tương tác cuối, Số hội thoại; lọc `tu_khoa`/`nhan`/`tu_ngay`/`den_ngay`; tên file không dấu `danh-sach-khach-hang-<timestamp>.xlsx`, đúng content-type xlsx.
- `GET /api/phan-tich/xuat-excel`: sheet "Số liệu" (chỉ số tiếng Việt từ `tinh_phan_tich`) + sheet "Lượt gọi AI" (tối đa 500 lượt gần nhất).
- Frontend: nút **Xuất Excel** ở trang Khách hàng (dùng lại `apiTaiFile`/`taiBlobXuong` của api.ts).

### 3. Thông báo cho admin
- Bảng mới `thong_bao` (model `Notification`): type (khach_moi / co_so_dien_thoai / du_thong_tin / gap_nhan_vien / khieu_nai / bot_khong_tra_loi_duoc / loi_he_thong), title, content, conversation_id, customer_id, level, is_read, sent_via_zalo.
- `app/services/notification_service.py`: chống trùng cùng loại + cùng khách trong 10 phút (gap_nhan_vien được miễn); `notify()` không bao giờ ném lỗi ra pipeline. Điểm gắn trong orchestrator: khách mới tạo, lần đầu có SĐT, vừa đủ bộ thông tin tối thiểu (SĐT + nhu cầu/dịch vụ quan tâm), intent gặp nhân viên/khiếu nại (kể cả quy tắc chuyển nhân viên), lỗi provider AI, lỗi gửi tin qua connector.
- Cài đặt trong `/api/cai-dat` (system_settings): `thong_bao_admin_zalo_thread_id` + 7 cờ bật/tắt theo loại (mặc định bật hết, thread để trống). Gửi Zalo cho admin chỉ khi có thread + sự kiện thuộc kênh `ca_nhan`, giới hạn tối thiểu 60 giây/lần gửi (kiểm tra bản ghi `sent_via_zalo` gần nhất), lỗi gửi chỉ ghi log.
- API: `GET /api/thong-bao` (lọc `chua_doc`, `loai`), `GET /api/thong-bao/dem-chua-doc`, `POST /api/thong-bao/{id}/da-doc`, `POST /api/thong-bao/danh-dau-tat-ca-da-doc`.
- Frontend: trang **Thông báo** mới (lọc theo loại/chưa đọc, mức độ màu, đánh dấu đã đọc) + mục menu 🔔 Thông báo + chuông ở header hiện số chưa đọc thật (polling 30 giây qua `/api/thong-bao/dem-chua-doc`); trang Cài đặt thêm mục "Thông báo cho quản trị viên" (thread admin + 7 công tắc theo loại).

### Kiểm thử mới (test_33 → test_40)
- test_33: tin chứa SĐT dạng chấm + email → CollectedInfo lưu đúng (chuẩn hóa 0901234567, confidence 0.95, có source_message_id) + hồ sơ khách được điền phone/email.
- test_34: gửi lại cùng SĐT → không lưu trùng; CRUD thủ công thêm/sửa/xác minh/xóa; trường không hợp lệ → 400.
- test_35: Mock hỏi xin SĐT đúng 1 lần qua 2 tin báo giá liên tiếp (tin 2 không còn hậu tố).
- test_36: xuất Excel khách hàng — content-type xlsx, mở lại bằng openpyxl, header tiếng Việt đúng, có dòng khách kèm SĐT; chưa đăng nhập bị chặn; Excel phân tích có sheet "Số liệu".
- test_37: thông báo khach_moi + co_so_dien_thoai được tạo cho khách mới có SĐT; đếm chưa đọc/đánh dấu đã đọc/lọc chưa đọc + lọc theo loại.
- test_38: chống trùng 10 phút ở tầng service (khach_moi lần 2 → None) và gap_nhan_vien được miễn chống trùng.
- test_39: gửi Zalo cho admin — mặc định không gọi connector (monkeypatch đếm 0), cấu hình thread admin → gọi đúng 1 lần + sent_via_zalo=True, lần kế tiếp < 60 giây vẫn tạo bản ghi nhưng không gửi nữa; dọn cấu hình về mặc định sau test.
- test_40: trích xuất AI (monkeypatch tầng AI) cho nhu_cau/dich_vu_quan_tam với confidence 0.7, SĐT có khoảng trắng vẫn chuẩn hóa được, thông báo du_thong_tin sinh khi đủ bộ tối thiểu; đánh dấu tất cả đã đọc đưa bộ đếm về 0.

### Chưa làm / giới hạn trung thực của đợt này
- Trích xuất AI chưa chạy thử với provider thật trong pytest (chỉ qua monkeypatch + code dùng chung parser/http_client đã kiểm chứng ở test_21/22); lần gọi AI trích xuất là 1 lượt gọi thêm cho mỗi tin khách khi dùng provider thật.
- Lọc khách "đã đủ/thiếu thông tin" dạng bộ lọc riêng trên trang Khách hàng: chưa làm (đã xem được đủ/thiếu qua panel thu thập + thông báo du_thong_tin).
- Thông báo qua email: chưa có (đúng lộ trình — mới có trong ứng dụng + Zalo admin).
- Chưa deploy lên server, chưa commit git (main agent thực hiện).

## Cập nhật đợt 3 (kiểm chứng bởi main agent, 22/10/2026)
- Sửa 2 lỗi môi trường thật trong AI Gateway: httpx lỗi "Invalid port" do NO_PROXY chứa IPv6 [::1] và lỗi xác minh chứng chỉ khi có proxy MITM. Gateway nay dùng `http_client()` (proxy tường minh, tôn trọng SSL_CERT_FILE, dịch vụ nội bộ đi trực tiếp) + test hồi quy test_30. Tổng test: **30 passed**.
- Smoke test provider THẬT qua chính API của Hub (DB tạm, không lưu key): đăng nhập 200 → tạo provider model `code` (key chỉ hiện masked) → `kiem-tra` = **da_ket_noi / Kết nối thành công** → Trung tâm kiểm thử AI trả lời đúng danh tính đã khóa ("em là trợ lý hỗ trợ khách hàng của doanh nghiệp"), model thực tế phía provider được ghi nhận tự động.
- Đã đẩy lên GitHub: https://github.com/iplam24/botzalovip (nhánh main). Remote không chứa token, repo không chứa secret (đã quét).

## Cập nhật Đợt nâng cấp 2 (22/10/2026) — Đăng nhập username, Font Awesome, quản trị sâu, thả tim, chia tin, định dạng Zalo, nhóm tag, UI mới + mục 9–11

Tổng kiểm thử sau đợt này: **55 passed** (40 cũ giữ nguyên + 15 mới test_41 → test_55). Frontend `npm run build` thành công và đã bật tách mã (code-splitting): chunk chính ~165 kB, mỗi trang một chunk riêng 3,5–13,4 kB (trước đây là 1 bundle ~261 kB).

### 1. Đăng nhập CHỈ bằng username (bỏ mật khẩu)
- `users` thêm cột `username` (duy nhất) + `last_login_at`; migration nhẹ trong seed (ALTER TABLE + backfill: admin → `admin`, người dùng cũ lấy phần trước @ của email, trùng thì thêm hậu tố số). Cột khẩu vẫn giữ trong DB nhưng không còn dùng để đăng nhập (mật khẩu tạo user mới không cần nhập nữa — hệ thống tự sinh mật khẩu không dùng).
- `POST /api/auth/dang-nhap` nhận đúng `{username}`; sai tên → 401, tài khoản bị khóa → 403; đăng nhập thành công ghi `last_login_at`. Trang đăng nhập còn 1 ô "Tên đăng nhập" (mặc định `admin`) kèm ghi chú rõ đây là đăng nhập nội bộ đơn giản cho vận hành tin cậy.
- Trang **Người dùng** mới: bảng username / họ tên / email / vai trò (đổi trực tiếp) / trạng thái khóa / lần đăng nhập gần nhất / số khách phụ trách / số bạn bè Zalo phụ trách + form thêm người dùng không cần mật khẩu.

### 2. Font Awesome toàn giao diện
- Cài `@fortawesome/fontawesome-free` (CSS + webfont đóng gói trong bundle, không phụ thuộc CDN); menu sidebar dùng icon FA cho mọi mục, nút bấm chính có icon đi kèm, bỏ toàn bộ emoji ở menu và các nhãn giao diện (emoji chỉ còn trong nội dung nghiệp vụ nếu người dùng tự nhập).

### 3 + 11. Trung tâm cấu hình toàn diện theo registry (mục 3 và 11 hợp nhất)
- Backend khai báo registry `DANG_KY_CAI_DAT` (53 khóa) trong `app/routers/cai_dat.py`: mỗi khóa có nhóm, nhãn, mô tả, kiểu (đúng/sai, số, giờ, đoạn văn, văn dài, lựa chọn, màu), giá trị mặc định và ràng buộc min/max/lựa chọn. `GET /api/cai-dat/dang-ky` trả registry + giá trị hiện tại + giờ đã lưu; `PUT /api/cai-dat` kiểm tra giá trị theo registry (sai kiểu/vượt giới hạn → 400); `POST /api/cai-dat/khoi-phuc-mac-dinh` theo nhóm hoặc toàn bộ.
- 7 nhóm: Hành vi bot, Phong cách trả lời (mục 10), Thông tin doanh nghiệp, Thu thập thông tin, Thông báo cho quản trị viên, Nhóm Zalo & gửi tin, Hệ thống & mô-đun.
- Các hằng số cứng trước đây nay đều là cài đặt có mặc định = giá trị hiện tại: số tin lịch sử AI (10), độ dài tối đa + độ trễ chia tin (350 ký tự / 700 ms), cửa sổ chống trùng thông báo (10 phút), giãn cách gửi Zalo cho admin (60 giây), câu hỏi xin SĐT, trường bắt buộc thu thập, ngưỡng chuyển nhân viên, giờ hoạt động + câu trả lời ngoài giờ, tin chào khách mới, câu khi bot không trả lời được, thông tin doanh nghiệp đưa vào ngữ cảnh AI, hiệu ứng "đang soạn tin", chế độ duyệt trước khi gửi, và công tắc bật/tắt từng mô-đun (thu thập, bộ nhớ, tự động hóa, thông báo, trả lời toàn cục). Tất cả đọc runtime mỗi request — đổi qua API là request kế tiếp đổi hành vi (có test test_54 chứng minh với tu_khoa_cam).
- Trang Cài đặt viết lại: menu nhóm có icon FA + mô tả + đếm số khóa, ô tìm kiếm cài đặt, control tự sinh đúng kiểu từ registry (gạt bật/tắt, số, chọn, màu, textarea...), lưu theo nhóm + khôi phục mặc định theo nhóm, thông báo toast. Khóa bí mật (API key...) KHÔNG nằm trong registry.

### 4. Thả tim tin nhắn khách đến — zca-js CÓ hỗ trợ thật
- Kiểm tra mã nguồn thư viện zca-js (đã cài trong sidecar): có `api.addReaction(icon, dest)`, icon trái tim = giá trị `"/-heart"` của enum Reactions (lưu ý: code sidecar cũ truyền chuỗi "HEART" là SAI — đã sửa mapping tên → giá trị enum ở endpoint /tha-cam-xuc).
- Sidecar thêm `POST /tha-tim` {thread_id, message_id (msgId), cli_msg_id, loai_thread} gọi `addReaction("/-heart", ...)`. Backend `ZaloPersonalConnector.tha_tim()`; orchestrator thả tim đúng 1 lần cho tin khách hợp lệ khi cài đặt `bot_tha_tim` bật (mặc định TẮT theo đúng yêu cầu), chỉ kênh Zalo cá nhân; lỗi thả tim chỉ ghi log, không chặn trả lời. Mock connector ghi nhận reaction để test (test_46: tắt = 0 lần, bật = đúng 1 lần).

### 5. Chia nhỏ tin nhắn dài khi gửi
- `chia_tin_nhan()` ở `app/services/dinh_dang.py`: ưu tiên cắt theo đoạn, dài hơn nữa cắt theo câu, cuối cùng cắt cứng theo ranh giới từ; tối đa `do_dai_toi_da_moi_tin` ký tự/phần (mặc định 350). Orchestrator gửi từng phần lần lượt qua connector với độ trễ `do_tre_giua_cac_tin_ms` (mặc định 700 ms; trong test đặt 0), lưu MỖI PHẦN là 1 bản ghi Message (trạng thái gửi riêng từng phần, hội thoại xem trước phần cuối); lỗi từng phần được ghi "Phần i/n" và nếu mọi phần đều lỗi vẫn phát thông báo lỗi hệ thống như trước. Cài đặt `gui_tin_chia_nho` tắt → gửi 1 tin nguyên văn.

### 6. Chuẩn hóa định dạng cho Zalo — `dinh_dang_tin_zalo()`
- `app/services/dinh_dang.py`: bỏ tiêu đề ##, in đậm **, in nghiêng *, gạch ngang trong **, code `; bảng Markdown → dòng "• Cột: giá trị; Cột: giá trị"; danh sách -/*/+ → "• "; link [chữ](url) → "chữ (url)"; giữ nguyên đoạn văn và xuống dòng đơn. Áp dụng TRƯỚC khi gửi qua connector mọi kênh VÀ trước khi lưu Message hiển thị (test_42 bao phủ đủ các case trong spec).

### 7. Bot trong nhóm Zalo: chỉ trả lời khi được tag đích danh
- Đã kiểm tra cấu trúc thật của sự kiện tin nhắn zca-js: `msg.type` (ThreadType), `msg.data.mentions = [{uid, pos, len, type}]`, `msg.data.uidFrom`, `msgId`/`cliMsgId`. Sidecar đính kèm vào webhook: `la_nhom`, `mentions`, `nguoi_gui_id`, `cli_msg_id`, `bot_uid`; bỏ qua tin do chính bot gửi (isSelf). UID bot lấy từ `api.getOwnId()`, tên/avatar từ `api.fetchAccountInfo()` (trạng thái sidecar mở rộng: `tai_khoan_id`, `ten_tai_khoan`, `avatar_url`, `phien_bat_dau_luc`).
- Orchestrator: tin nhóm chỉ được trả lời khi có mention chứa đúng UID bot; mention @all có uid `-1` không tính; tin vẫn được lưu + trích xuất thông tin, chỉ dừng trả lời và ghi SystemLog `bo_qua_nhom_khong_tag`. Cài đặt `bot_nhom_chi_khi_duoc_tag` mặc định BẬT (test_44 bao phủ: tag đúng / @all / không tag / tag người khác / chat 1-1 / tắt cài đặt).

### 8. Giao diện mới + Responsive toàn diện (mục 8 + 11.1)
- Font Be Vietnam Pro đóng gói qua `@fontsource/be-vietnam-pro` (400/500/600/700); màu chủ đạo Zalo #0068FF thành biến giao diện (đổi được qua cài đặt `mau_chu_dao_giao_dien`), bo góc + đổ bóng thẻ thống nhất, hiệu ứng chuyển trang 180 ms, skeleton khi tải danh sách.
- Toast tự viết (context + component) thay `window.alert` ở các thao tác chính của Hội thoại, Khách hàng, Cài đặt, Nhà cung cấp, Tài khoản Zalo, Người dùng, Bạn bè Zalo.
- Tất cả trang dùng `React.lazy()` + Suspense. Sidebar: desktop cố định có thu gọn; mobile thành ngăn kéo trượt + lớp phủ + nút hamburger ở header. Bảng dữ liệu cuộn ngang có kiểm soát (min-width + overflow-x-auto), lưới thống kê 1/2/4 cột theo mốc, form trong hộp thoại 1 cột trên mobile, lề trang co lại trên màn nhỏ. Đã rà theo mốc 375/768/1280 px bằng lớp chuẩn Tailwind (chưa chụp ảnh kiểm chứng trực tiếp từng trang).

### 9. Bổ sung theo yêu cầu LAM
- **9.1 Bật/tắt nhà cung cấp AI:** endpoint `PATCH /api/ai-providers/{id}/bat-tat`; nút gạt ngay trong thẻ nhà cung cấp ở danh sách + nhãn "Đang tắt"; tắt nhà cung cấp ĐANG LÀ MẶC ĐỊNH → 400 yêu cầu chọn mặc định khác trước (cả qua PATCH lẫn PUT); provider đang tắt bị loại khỏi lựa chọn khi gửi (đã có sẵn logic lọc is_active, nay thêm đường bật/tắt nhanh). Test_47.
- **9.2 Hội thoại đã nhắn tin:** tham số `loc_tin` (da_nhan_tin / chua_nhan_tin) ở API + 3 nút lọc Tất cả / Đã nhắn tin / Chưa nhắn trên trang; mỗi dòng hiện số tin nhắn + tin cuối + thời gian + kênh + người phụ trách; danh sách sắp theo hoạt động gần nhất. Test_48.
- **9.3 Xem người dùng:** trang Người dùng hiển thị đủ username, vai trò, trạng thái, `last_login_at`, số khách phụ trách (theo tên phân công hiện có trong dữ liệu khách) và số bạn bè Zalo được phân bổ.
- **9.4 Tài khoản đang liên kết:** mục "Tài khoản đang liên kết" ở trang Tài khoản Zalo lấy dữ liệu thật từ trạng thái sidecar (tên/ID/trạng thái/thời điểm bắt đầu phiên), cấu trúc danh sách sẵn cho nhiều tài khoản. Nút **Ngắt liên kết**: zca-js không có API đăng xuất phía máy chủ Zalo; sidecar hỗ trợ thật ở mức dừng lắng nghe + XÓA dữ liệu phiên đã lưu (credentials.json) — endpoint `POST /api/zalo/ca-nhan/ngat-lien-ket` đã làm đúng như vậy và giao diện ghi rõ khác biệt với "Ngắt kết nối" tạm thời.
- **9.5 Phân bổ admin cho bạn bè Zalo:** zca-js có `api.getAllFriends()` thật → sidecar `GET /ban-be`. Backend bảng `phan_bo_ban_be` (zalo_friend_id duy nhất, tên, avatar, admin_user_id, ghi chú) + API: danh sách (tìm kiếm/lọc theo admin gồm cả "chưa phân bổ"), thống kê, `POST /dong-bo` (upsert — bạn cũ giữ nguyên phân bổ, chỉ cập nhật tên/avatar; bạn mới vào trạng thái chưa phân bổ), gán 1 bạn và gán hàng loạt. Khi bạn trong danh sách nhắn tin, khách + hội thoại tự gắn admin phụ trách NẾU chưa có người phụ trách (không ghi đè phân công tay). Trang **Bạn bè Zalo**: thống kê, nút Đồng bộ từ Zalo (lỗi/thiếu kết nối hiển thị lý do thật, không bịa dữ liệu), chọn nhiều + gán hàng loạt, dropdown admin từng dòng. Test_49 (monkeypatch connector giả lập sidecar).

### 10. ƯU TIÊN CAO — chống trả lời "một motip" (đã chẩn đoán + sửa gốc rễ)
- **Lịch sử đa lượt:** trước đây `generate_reply` chỉ gửi 1 tin user duy nhất. Nay orchestrator lấy N tin gần nhất (cài đặt `so_tin_nhan_ngu_canh`, mặc định 10) dựng thành messages user/assistant đúng thứ tự và truyền cho provider; ngữ cảnh tri thức + bộ nhớ đưa vào SYSTEM prompt (không còn dán vào câu hỏi).
- **System prompt viết lại** theo persona cấu hình được: tên hiển thị, cách xưng hô (mặc định em/bạn), 3 giọng điệu (tự nhiên thân thiện / chuyên nghiệp / hài hước nhẹ — mỗi giọng một đoạn hướng dẫn riêng), luật chống motip ghi rõ: không chào lại giữa cuộc trò chuyện, không mở đầu bằng câu mẫu, cấm các câu kết sáo rỗng ("nếu cần thêm thông tin cứ nhắn em nhé"...), bắt nhịp giọng khách (khách nhắn cụt thì trả lời gọn), hỏi ngược theo đúng ngữ cảnh, ưu tiên thông tin doanh nghiệp trong ngữ cảnh. Vẫn khóa danh tính: không tự nhận là mô hình AI/Gemini. Độ dài theo cài đặt (ngan_gon/can_bang/chi_tiet) + `prompt_bo_sung` của doanh nghiệp.
- **Temperature/độ dài:** payload nay gửi `temperature` (cài đặt `ai_temperature`, mặc định 0.85) và `max_tokens` theo cấu hình nhà cung cấp cho provider thật.
- **Mock provider** có 2–3 biến thể diễn đạt cho intent báo giá/chào hỏi/mặc định, chọn luân phiên để môi trường mô phỏng cũng không cứng nhắc.
- Test_50 bắt payload thật (monkeypatch httpx): có đủ tin lịch sử, system chứa persona + ngữ cảnh tri thức (không nằm ở tin user), temperature = 0.85, max_tokens đúng cấu hình. Test_51 đổi tên/giọng/xưng hô qua API → prompt đổi theo + khôi phục mặc định nhóm đúng. Test_52 Mock luân phiên ≥ 2 biến thể.

### Kiểm thử mới (test_41 → test_55) trong `backend/tests/test_nang_cap_2.py`
- test_41 đăng nhập chỉ username + last_login_at + khóa tài khoản bị chặn; test_42 định dạng Zalo đủ case + chia tin; test_43 chia tin thật qua pipeline (3 phần → 3 Message) và tắt chia → 1 tin; test_44 logic nhóm tag; test_45 bot bị "bí" dùng câu dự phòng đã cấu hình; test_46 thả tim 0/1 lần; test_47 gạt tắt provider + chặn tắt mặc định; test_48 lọc hội thoại theo tin nhắn; test_49 đồng bộ bạn bè upsert giữ phân bổ + gán hàng loạt + bạn nhắn tin gắn đúng admin; test_50 payload AI (lịch sử + temperature + max_tokens + system); test_51 prompt đổi theo cài đặt + khôi phục mặc định; test_52 Mock luân phiên; test_53 registry đủ khóa/kiểu + kiểm tra giá trị sai → 400; test_54 đổi cài đặt tu_khoa_cam qua API → hành vi đổi ngay ở tin kế tiếp; test_55 đếm tin lịch sử AI theo cài đặt (3 so với mặc định 10).
- Kiểm chứng tay bổ sung: khởi động backend bằng uvicorn với DB tạm — đăng nhập username 200, `/api/auth/me` có username + last_login_at, registry trả đủ 53 khóa.

### Chưa làm / giới hạn trung thực của đợt này
- Các endpoint sidecar mới (/tha-tim, /ban-be, /ngat-lien-ket, mentions trong webhook, trạng thái tài khoản mở rộng) đã kiểm chứng ở mức MÃ NGUỒN thư viện zca-js + `node --check` + test backend bằng connector giả lập; CHƯA chạy thật với tài khoản Zalo đang đăng nhập trên máy chủ (việc này thuộc bước triển khai của main agent — sidecar trên server cần được cập nhật code mới và khởi động lại).
- Nhánh "giờ hoạt động" và các công tắc mô-đun (trừ tu_khoa_cam đã có test) hiện mới có mặc định cho phép toàn bộ + tôn trọng khi tắt; hành vi ngoài giờ chỉ thay câu trả lời của bot bằng câu đã cấu hình, vẫn lưu tin và xử lý trích xuất/thông báo như bình thường.
- Chế độ "duyệt trước khi gửi": tin bot được lưu trạng thái chờ duyệt và KHÔNG gửi; chưa có giao diện duyệt/gửi lại (nút gửi tay trong trang Hội thoại vẫn dùng được như đường gửi thay thế).
- Responsive đã rà bằng lớp chuẩn + build, chưa chụp ảnh kiểm chứng trực tiếp ở 3 mốc màn hình.
- Chưa deploy lên server, chưa commit git (main agent thực hiện theo phân công).

## Cập nhật bổ sung (22/10/2026) — Chế độ trò chuyện tự do + ĐÍNH CHÍNH đăng nhập username & mật khẩu + Nút Lưu nổi bật + PR chủ động & Bộ nhớ dài hạn

Tổng kiểm thử sau đợt bổ sung này: **62 passed** (55 cũ giữ nguyên + 7 mới test_56 → test_62). Registry cài đặt nay có **59 khóa / 8 nhóm**. Frontend `npm run build` thành công (chunk chính ~166 kB).

### A. ĐÍNH CHÍNH đăng nhập: USERNAME + MẬT KHẨU (thay thế mục 1 của Đợt nâng cấp 2 ở trên)
- Mục 1 của Đợt nâng cấp 2 ("đăng nhập CHỈ bằng username, bỏ mật khẩu") là HIỂU NHẦM yêu cầu và đã bị thay thế hoàn toàn theo đính chính của LAM: ý gốc là dùng username thay cho email, mật khẩu vẫn bắt buộc.
- `POST /api/auth/login` nay nhận `{username, password}`: tra user theo username (không phân biệt hoa thường) → tài khoản bị khóa 403 → kiểm tra mật khẩu bằng `verify_password` (PBKDF2 như cũ): sai mật khẩu → 401 "Mật khẩu không đúng", user không tồn tại → 401, thiếu trường → 422. Đúng mật khẩu vẫn ghi `last_login_at` và trả token như trước. Tài khoản admin giữ nguyên: username `admin` + mật khẩu theo `ADMIN_PASSWORD` (seed không đổi; hash đang lưu trên server là của chính mật khẩu đó nên đăng nhập lại bình thường sau khi triển khai bản này).
- Trang đăng nhập: 2 ô "Tên đăng nhập" + "Mật khẩu" (type password), bỏ ghi chú "chỉ cần username". Trang Người dùng: tạo mới BẮT BUỘC đặt mật khẩu (API trả 400 nếu trống); thêm form Sửa người dùng có ô "Mật khẩu mới (để trống = giữ nguyên)" — mật khẩu mới được hash khi lưu, không bao giờ xuất hiện trong phản hồi API.
- Test_41 đã viết lại toàn bộ cho hành vi mới: đúng pass 200, sai pass 401, thiếu pass 422, bị khóa + đúng pass 403, đổi mật khẩu qua API → mật khẩu mới đăng nhập được, mật khẩu cũ bị từ chối, sửa không gửi mật khẩu thì giữ nguyên.

### B. Nút LƯU nổi bật, khó quên
- **Trang Cài đặt:** theo dõi trạng thái "bẩn" theo từng khóa (so giá trị đang sửa với bản đã lưu gần nhất). Ngay khi có bất kỳ thay đổi chưa lưu nào, một thanh dính (fixed) nổi lên ở đáy màn hình: nền màu chủ đạo, chữ "Có N thay đổi chưa lưu ở M nhóm — chưa lưu là chưa có hiệu lực đâu nhé" + nút **"Lưu thay đổi"** lớn, trắng, in đậm, có icon Font Awesome — bấm là lưu TẤT CẢ nhóm đang bẩn một lần. Lưu xong thanh chuyển xanh lá "Đã lưu ✓ lúc HH:MM" vài giây rồi tự ẩn. Nút lưu theo từng nhóm vẫn giữ nguyên.
- **Mọi form trong HopBieuMau (modal dùng chung):** modal đổi cấu trúc — tiêu đề cố định, thân cuộn riêng; hàng nút cuối của form (Lưu/Hủy) được CSS ghim dính ở đáy vùng cuộn nên form dài đến đâu nút Lưu vẫn luôn nhìn thấy, áp dụng tự động cho mọi trang đang dùng component này.
- Kiểm chứng: build frontend pass + rà soát code (không có test tự động cho dirty-state của giao diện; hành vi lưu vẫn được bao phủ bởi test API cài đặt phía backend).

### C. Chế độ TRÒ CHUYỆN TỰ DO — bot nghỉ bán hàng, chat như bạn bè
- 3 khóa mới trong registry, nhóm riêng "Chế độ trò chuyện tự do" (icon fa-face-laugh-wink): `che_do_tro_chuyen_tu_do` (bool, mặc định TẮT), `prompt_tro_chuyen_tu_do` (textarea — persona mặc định viết sẵn: bạn bè thân thiết, nói chuyện tự nhiên kiểu Gen Z, xưng hô linh hoạt theo đối phương, cà khịa thông minh, được phép tiếng lóng/chửi thề qua lại kiểu bạn bè khi đối phương đùa theo hướng đó, không tự nhận là AI/trợ lý, không lôi sản phẩm/giá cả vào trừ khi đối phương tự hỏi mua bán, trả lời ngắn kiểu chat; admin sửa được toàn văn trên UI), `nhiet_do_tu_do` (số 0–2, mặc định 1.1).
- Khi BẬT (ở `ai_gateway.generate_reply` + orchestrator): system prompt CHỈ gồm persona tự do — không chèn ngữ cảnh kho tri thức, không thông tin doanh nghiệp, không danh sách dịch vụ PR, không hồ sơ bán hàng, không luật tư vấn, không gợi ý hỏi SĐT; temperature dùng `nhiet_do_tu_do`. Vẫn truyền lịch sử hội thoại đa lượt, vẫn qua chuẩn hoá định dạng Zalo + chia tin + thả tim theo cài đặt, vẫn tôn trọng luật nhóm (chỉ rep khi được tag đích danh), từ khóa cấm và chuyển nhân viên ở mức hệ thống, quy tắc tự động hóa có câu trả lời cố định vẫn chạy (do admin chủ động cấu hình).
- Thông báo lead: khi đang bật, KHÔNG tạo thông báo `co_so_dien_thoai` và `du_thong_tin`, KHÔNG hỏi xin SĐT (kể cả đường Mock nối câu hỏi); việc trích xuất thông tin vẫn chạy lặng lẽ để không mất dữ liệu. Tắt chế độ là mọi hành vi tư vấn/lead quay lại như cũ.
- Giao diện: công tắc + persona trong nhóm cài đặt riêng kèm mô tả rõ; nút gạt nhanh ngay trên trang Tổng quan; khi đang bật, header mọi trang hiện huy hiệu màu hổ phách "Đang ở chế độ trò chuyện tự do" (bấm vào để tới Cài đặt), kiểm tra lại mỗi 30 giây cùng nhịp chuông thông báo.
- Với nhà cung cấp Mock (mô phỏng), bot cũng đáp theo biến thể bạn bè luân phiên thay cho mẫu tư vấn — chỉ để demo, trải nghiệm đầy đủ cần nhà cung cấp AI thật.
- Test_56 registry nhóm tự do + ràng buộc nhiệt độ; test_57 payload khi bật (có prompt tự do, KHÔNG có tri thức/luật tư vấn/hồ sơ, temperature = 1.3, không gợi ý SĐT, vẫn có lịch sử) và khi tắt (hành vi cũ nguyên vẹn); test_58 tắt thông báo lead nhưng vẫn thu thập SĐT lặng lẽ; test_59 Mock không hỏi SĐT khi tự do, hỏi lại khi tắt chế độ.

### D. PR chủ động + tiêm dịch vụ vào prompt (chế độ tư vấn)
- Mỗi lượt trả lời tư vấn, hệ thống tiêm vào system prompt danh sách dịch vụ đang `is_active` (tối đa `so_dich_vu_pr`, mặc định 5, theo thứ tự tạo): tên + giá (giá chữ nếu có, không thì định dạng VNĐ từ giá số; giá 0 thì bỏ phần giá) + mô tả rút gọn 200 ký tự.
- Luật PR ghi thẳng trong prompt: khách chào hỏi/mơ hồ/chưa rõ nhu cầu → giới thiệu NGẮN GỌN 1–2 dịch vụ nổi bật và gợi mở theo nhu cầu, TUYỆT ĐỐI tránh câu hỏi trống kiểu "anh/chị đang cần hỗ trợ về sản phẩm hay dịch vụ nào ạ?"; đã có ngữ cảnh → tư vấn bám sát + gợi ý dịch vụ liên quan tự nhiên; không PR dồn dập mọi lượt.
- Cài đặt: `bot_chu_dong_pr` (bool, mặc định bật), `so_dich_vu_pr` (số 1–20). Test_60 kiểm chứng payload có dịch vụ + giá định dạng "150.000đ" + luật PR, và tắt cài đặt thì không tiêm nữa.
- Lưu ý trung thực: bot chỉ PR hay khi dữ liệu dịch vụ/kho tri thức được nhập tử tế — chẩn đoán trên server cho thấy dữ liệu thật còn rất trống (1 dịch vụ giá 0 không mô tả, kho tri thức 1 đoạn), đó là giới hạn dữ liệu, không phải giới hạn cơ chế.

### E. Bộ nhớ dài hạn theo khách — "nhớ cực lâu"
- `customers` thêm cột `memory_summary` (TEXT; migration nhẹ trong seed theo đúng mẫu an toàn Postgres — TEXT/VARCHAR thường, không DATETIME).
- `memory_service.cap_nhat_tom_tat_bo_nho`: sau mỗi `bo_nho_tom_tat_sau_bao_nhieu_tin` tin nhắn của khách (cài đặt mới, mặc định 6; mốc đã tóm tắt lưu bằng SystemLog module `bo_nho` kèm ID tin nhắn cuối đã gộp) → tóm tắt gộp hồ sơ cũ + tin mới thành hồ sơ ngắn (định danh/tên, nhu cầu & sở thích, đã hỏi/mua gì, điểm cần lưu ý, việc đang dang dở). Provider thật: gọi AI tóm tắt (temperature 0.3, có ghi AIUsage), lỗi AI thì bỏ qua lần đó, không chặn pipeline, mốc giữ nguyên để lần sau thử lại. Provider Mock: tóm tắt bằng quy tắc từ thông tin đã thu thập + vài tin gần nhất (không để trống khi kiểm thử).
- Tiêm vào MỌI lượt trả lời tư vấn: mục "HỒ SƠ KHÁCH (bot nhớ lâu dài)" kèm luật dùng tự nhiên (gọi đúng tên khách nếu biết, nhắc nhu cầu cũ khi liên quan, không đọc thuộc lòng hồ sơ), cùng với các ký ức liên quan như trước.
- API: `GET /api/khach-hang/{id}` và danh sách đều trả thêm `memory_summary`; `POST /api/khach-hang/{id}/tom-tat-bo-nho` tóm tắt lại ngay (kể cả chưa đủ tin); `PUT /api/khach-hang/{id}` cho phép admin sửa `memory_summary`.
- UI: trong chi tiết khách (modal Thông tin thu thập) có thẻ "Bot nhớ về khách này" hiển thị hồ sơ + nút "Tóm tắt lại ngay" + "Sửa tay" với nút Lưu chính rõ ràng.
- Test_61: ngưỡng 3 tin → hồ sơ tự hình thành (đường Mock) và chứa nội dung đã trao đổi; mới 1 tin thêm thì KHÔNG tóm tắt lại quá sớm; payload lượt sau chứa mục HỒ SƠ KHÁCH + nội dung hồ sơ. Test_62: tóm tắt tay qua API + sửa tay lưu được.
- Chế độ trò chuyện tự do KHÔNG tiêm PR/dịch vụ/hồ sơ bán hàng và không tự tóm tắt hồ sơ bán hàng (chỉ giữ trí nhớ hội thoại ngắn trong phiên như thiết kế tự do đã chốt).

### Chưa làm / giới hạn trung thực của đợt bổ sung này
- Chưa deploy lên server, chưa commit git (main agent thực hiện theo phân công) — sau khi deploy, đăng nhập admin dùng username `admin` + mật khẩu đã cấp trước đây (không phải chỉ gõ username như bản đợt 2 đã live tạm thời).
- Dirty-state của trang Cài đặt và chân modal dính được kiểm chứng bằng build + đọc code, chưa có test giao diện tự động (chụp ảnh/e2e).
- Tóm tắt bộ nhớ bằng AI thật chưa chạy thử với provider thật trong pytest (đường đi đã test bằng Mock + bắt payload; lỗi AI được xử lý bỏ qua an toàn).

## Đợt nâng cấp 3 (22/10/2026) — Phân trang + Cấu hình qua chat + Vector DB + Design pass + Đổi mật khẩu tự phục vụ

Trạng thái chung của đợt: **69 test pass** (62 test cũ giữ nguyên toàn bộ + 7 test mới `test_71`→`test_77` trong `backend/tests/test_nang_cap_3.py`), frontend build thành công. **Chưa deploy, chưa commit** (main agent thực hiện theo phân công).

### Mục nhỏ — Đổi mật khẩu TỰ PHỤC VỤ
- Backend: `POST /api/auth/doi-mat-khau` (bắt buộc đăng nhập) nhận `{mat_khau_cu, mat_khau_moi}`: kiểm tra mật khẩu hiện tại bằng `verify_password` — sai → 400 "Mật khẩu hiện tại không đúng"; mật khẩu mới < 6 ký tự → 400; đúng → lưu hash mới (PBKDF2 như mọi mật khẩu khác) và ghi `SystemLog` module `auth` (chỉ ghi sự kiện + username/id, TUYỆT ĐỐI không ghi giá trị mật khẩu). JWT hiện tại giữ nguyên hiệu lực (không bắt đăng nhập lại).
- Frontend: khu vực tài khoản ở chân sidebar thành menu thả xuống (username + "Đổi mật khẩu" / "Đăng xuất"); form `HopBieuMau` 3 ô (hiện tại / mới / nhập lại), kiểm tra khớp + độ dài ngay trong form và báo lỗi rõ trong form; thành công → toast "Đã đổi mật khẩu".
- Test_71: tạo nhân viên riêng → chưa đăng nhập 401; sai mật khẩu cũ 400; mật khẩu mới ngắn 400; đổi đúng 200 và đăng nhập bằng mật khẩu mới được, mật khẩu cũ bị từ chối; nhật ký `auth` có sự kiện và không chứa giá trị mật khẩu nào.

### Mục 1 — Phân trang phía máy chủ cho mọi danh sách dài
- Chuẩn chung (`app/services/phan_trang.py`): tham số `trang` (từ 1) + `kich_thuoc_trang` (chỉ nhận 10/20/50/100, mặc định 20; ngoài danh sách → rơi về 20). Trang vượt quá tổng số trang được kẹp về trang cuối.
- Áp dụng cho: Hội thoại, Khách hàng, Thông tin thu thập theo khách, Bạn bè Zalo, Thông báo, Nhật ký hệ thống, Bộ nhớ AI, Tài liệu kho tri thức.
- **Tương thích ngược có chủ đích**: chỉ khi client truyền `trang >= 1` endpoint mới trả dạng `{"muc": [...], "tong": n, "trang": t, "tong_trang": tt, "kich_thuoc_trang": k}`; không truyền → trả list thuần y như cũ. Nhờ vậy không phá vỡ bất kỳ nơi nào đang dùng list thuần (dropdown khách hàng ở Bộ nhớ AI, kiểm thử cũ, tích hợp ngoài) — đã kiểm chứng bằng test: cả 6 endpoint đều đúng cả hai dạng.
- Frontend: component `PhanTrang` dùng chung (nút Trước/Sau, số trang rút gọn, chọn 10/20/50/100, dòng "Hiển thị x–y / tổng z mục", tự ẩn khi ≤ 1 trang) gắn vào cả 7 trang/panel trên; mọi bộ lọc (từ khóa, trạng thái, loại...) được giữ nguyên khi chuyển trang và tự về trang 1 khi đổi lọc.
- Test_72: tạo 27 khách đánh dấu → trang 1/2/3 đủ 10/10/7 mục rời nhau, tổng/tổng trang đúng, kích thước lạ rơi về 20, lọc hẹp giữ đúng khi phân trang.

### Mục 2 — Cấu hình qua đoạn chat ("Trợ lý cấu hình")
- Trang mới trong menu (icon `fa-terminal`, ngay sau Cài đặt): khung chat; admin gõ lệnh tự nhiên → thẻ xác nhận từng thay đổi (nhãn cài đặt, khóa, giá trị **cũ → mới**, nút "Áp dụng các thay đổi này" / "Bỏ qua"); lệnh mẫu dạng chip bấm được; lịch sử giữ trong phiên làm việc.
- Backend: `POST /api/cau-hinh-chat/phan-tich` — CHỈ phân tích, không đổi gì. Hai đường: (a) provider mặc định là AI thật → gửi kèm danh sách khóa rút gọn của registry (61 khóa: khóa/nhãn/kiểu/lựa chọn/min-max), yêu cầu JSON thuần; (b) provider Mock → bộ phân tích quy tắc tối thiểu cho mẫu "bật/tắt <tên gần đúng>" (kèm bảng bí danh: "chế độ trò chuyện tự do", "thả tim", "nhiệt độ ai", "giọng bot"...) và "đặt/đổi <khóa> thành|sang|= <giá trị>" (số, đúng/sai, lựa chọn theo nhãn). **Mọi kết quả đều bị lọc lại bằng registry ở server**: khóa không có thật (AI bịa) hoặc giá trị sai kiểu/ràng buộc → loại bỏ; không hiểu lệnh → trả lời rõ + gợi ý lệnh mẫu.
- `POST /api/cau-hinh-chat/ap-dung` (chỉ quản trị viên): nhận các thay đổi ĐÃ DUYỆT, kiểm tra lại toàn bộ (có khóa lạ → 400, không áp dụng một phần) rồi áp dụng qua đúng hàm dùng chung với PUT `/api/cai-dat` (`ap_dung_thay_doi` — registry giờ 61 khóa) và ghi `SystemLog` module `cau_hinh_qua_chat` kèm người thực hiện + từng thay đổi cũ → mới.
- Test_73 (đường quy tắc, ép Mock cho tất định): "Bật chế độ trò chuyện tự do" → phân tích đúng khóa/giá trị cũ–mới, **chưa duyệt thì cài đặt thật chưa đổi**, áp dụng → `GET /api/cai-dat` đổi thật + có nhật ký; lệnh đặt số (nhiệt độ AI 0.7) và lệnh đổi select (giọng bot → ngắn gọn) đều map đúng. Test_74 (đường AI bằng monkeypatch): AI trả thêm khóa bịa → bị loại, chỉ khóa thật còn lại; áp dụng thẳng khóa bịa → 400.

### Mục 3 — Vector DB / tìm kiếm ngữ nghĩa
- **Cơ chế đã chọn (ghi rõ, trung thực)**: vector lưu dạng **JSON text** (list float) trong cột `embedding` mới trên `knowledge_chunks` và `memories`; độ tương đồng tính bằng **cosine trong Python**. Lý do: tương thích cả SQLite (bản kiểm thử/demo) lẫn PostgreSQL (bản thật) với cùng một mã nguồn, không cần kiểu dữ liệu riêng của pgvector ở tầng ORM; quy mô hiện tại (nghìn–chục nghìn đoạn) hiệu năng vẫn ổn. Trên Postgres, lúc khởi động hệ thống **có thử** `CREATE EXTENSION IF NOT EXISTS vector` (best-effort, lỗi thì bỏ qua) để sẵn sàng cho nâng cấp dùng cột vector thật + index HNSW/IVFFlat sau này — nhưng bản đợt này **chưa** dùng cột vector của pgvector cho truy hồi; giới hạn cần biết: cosine tính trong Python sẽ chậm dần khi số đoạn lên tới hàng trăm nghìn, khi đó nên chuyển sang pgvector thật.
- `embedding_service` — thứ tự nguồn nhúng: (1) biến môi trường `EMBEDDING_FAKE=1` → vector deterministic từ hash bag-of-words (CHỈ cho kiểm thử/demo); (2) provider AI mặc định có `embedding_model` + `base_url` + khóa → gọi `POST /embeddings` tương thích OpenAI; (3) gói `fastembed` local (đã thêm vào requirements, model `paraphrase-multilingual-MiniLM-L12-v2`) — import an toàn, chưa cài/chưa tải được model thì coi như chưa sẵn sàng. Không có nguồn nào → trả None, **hệ thống rơi về tìm từ khóa như cũ, không sập, không giả vờ đã nhúng**; trạng thái nguồn luôn hiển thị trung thực (`chua_san_sang` khi chưa có).
- Nhúng tự động khi tạo/cập nhật tài liệu tri thức (mỗi đoạn) và khi tạo ký ức mới (kể cả khi sửa tay nội dung ký ức → nhúng lại). Endpoint: `POST /api/tri-thuc/nhung-lai-tat-ca` và `POST /api/bo-nho/nhung-lai-tat-ca` (quản trị viên); `GET /api/tri-thuc/trang-thai-vector` + `GET /api/bo-nho/trang-thai-vector` trả `{da_nhung/tong, nguon, san_sang, mo_ta}`.
- Truy hồi hợp nhất: `knowledge_service.retrieve` và `memory_service.retrieve_memories` cộng thêm kết quả khớp ngữ nghĩa (cosine ≥ 0,3) vào kết quả từ khóa; kết quả tri thức có thêm trường `diem_ngu_nghia`. Hai cài đặt mới trong registry (nhóm Hệ thống): `tim_kiem_ngu_nghia` (bool, mặc định BẬT) và `so_ket_qua_ngu_nghia` (số 1–20, mặc định 4). Tắt cài đặt → truy hồi y hệt trước đợt này.
- UI: Kho tri thức có thẻ trạng thái Vector DB (đã nhúng x/y đoạn + mô tả nguồn + cảnh báo khi chưa sẵn sàng) và nút "Nhúng lại toàn bộ"; ô "Kiểm tra truy xuất" (chính là ô test tìm ngữ nghĩa) hiển thị thêm điểm ngữ nghĩa bên cạnh điểm từ khóa. Bộ nhớ AI hiển thị dòng trạng thái đã nhúng x/y ký ức.
- Test_75 (`EMBEDDING_FAKE=1`): tạo tài liệu → đoạn có embedding thật trong DB; tạo ký ức → có embedding; trạng thái báo nguồn `fake`/sẵn sàng; nhúng lại → đã nhúng = tổng. Test_76 (cơ chế xếp hạng): gán tay vector trực giao cho 2 đoạn + monkeypatch vector truy vấn → đoạn trùng hướng lọt kết quả với cosine ≈ 1,0 dù KHÔNG trùng từ khóa nào, đoạn trực giao bị loại; tắt `tim_kiem_ngu_nghia` → kết quả rỗng như đường từ khóa cũ. **Giới hạn trung thực**: kiểm thử dùng vector giả định hướng nên chỉ chứng minh được CƠ CHẾ (nhúng → lưu → cosine → xếp hạng → tắt/bật), chưa chứng minh chất lượng ngữ nghĩa thật — chất lượng thật phụ thuộc model embedding sẽ dùng trên server (LAM cần đặt `embedding_model` cho provider hoặc cho phép tải model local ở lần deploy sau).

### Mục 4 — Design pass giao diện (không đổi hành vi/route/nhãn)
- `index.css`: bổ sung hệ biến thiết kế dùng chung (`--nen-trang/--nen-phu/--vien-nhe/--chu-chinh/--chu-phu/--bo-goc-the/--bo-goc-nut/--bong-the/--bong-nhe` + biến thể dark), class bảng dùng chung `.bang-du-lieu` (hàng zebra + hover nổi, cả chế độ tối), skeleton tối trầm hơn ở dark mode, chip logo sidebar chuyển gradient xanh (`logo-thuong-hieu`), class ô icon thẻ thống kê.
- Tổng quan: 8 thẻ thống kê có icon Font Awesome trong ô bo góc theo màu riêng; thêm **mini bar chart 7 ngày** (cột chồng Khách/Bot/Nhân viên) từ trường mới `hoat_dong_7_ngay` của `GET /api/tong-quan` (chỉ THÊM trường, không đổi trường cũ) kèm chú giải màu + tooltip số liệu từng ngày.
- Bảng zebra/hover áp dụng: Khách hàng (+ bảng thông tin thu thập), Bạn bè Zalo, Nhật ký, Bộ nhớ AI, Kho tri thức.
- Hội thoại: bong bóng chat có avatar tròn theo người gửi (khách/bot/nhân viên) và ký hiệu trạng thái ngay trong bong bóng (✓✓ đã gửi màu xanh, ⚠ "Gửi lỗi" màu đỏ) — logic gửi/nhận không đổi.
- Trạng thái rỗng: `ChuaCoDuLieu` nhận thêm icon tùy chọn + dòng hướng dẫn phụ. Sidebar giữ nguyên cấu trúc; dark mode đã rà các class mới đều có biến thể tối; các mốc responsive giữ nguyên.

### Chưa làm / giới hạn trung thực của đợt 3
- Chưa deploy lên server, chưa commit git (main agent thực hiện theo phân công).
- Vector DB: dùng JSON + cosine Python như đã ghi ở mục 3 — chưa dùng cột vector/index của pgvector cho truy hồi; fastembed mới chỉ khai báo trong requirements + import an toàn, **chưa cài thật vào môi trường này** nên đường local chưa được chạy thử end-to-end (đường provider /embeddings và đường fake đã có kiểm chứng cơ chế).
- Design pass được kiểm chứng bằng build TypeScript/Vite thành công + rà soát class; chưa có test giao diện tự động (e2e/chụp ảnh) — cần kiểm tra bằng mắt sau khi deploy, nhất là dark mode và chart 7 ngày trên dữ liệu thật.

## Bổ sung (23/10/2026) — Trang Prompt tổng quát + Bot xem được ảnh khách gửi

Trạng thái chung: **74 test pass** (69 test cũ giữ nguyên toàn bộ + 5 test mới `test_78`→`test_82` trong `backend/tests/test_tinh_nang_moi.py`), frontend `npm run build` thành công (có chunk riêng `PromptTongQuat`), sidecar `node --check` đạt. **Chưa deploy, chưa commit** (main agent thực hiện theo phân công).

### Tính năng 1 — Trang "Prompt tổng quát"
- Cài đặt mới `prompt_tong_quat` (registry giờ **62 khóa**, kiểu textarea, nhóm "Phong cách trả lời", mặc định trống). Cơ chế ghi rõ ngay trong mô tả khóa: khi có nội dung, đoạn đó **THAY phần lõi mặc định** của prompt hệ thống (danh tính bot + xưng hô + hướng dẫn giọng điệu/độ dài + luật chống một motip + khóa danh tính); các phần dữ liệu động vẫn tự chắp phía sau như cũ (thông tin doanh nghiệp, danh sách dịch vụ PR, hồ sơ khách, ngữ cảnh tri thức/bộ nhớ, Hướng dẫn bổ sung). Khi trống → hành vi y hệt trước (toàn bộ test cũ pass nguyên vẹn).
- Kỹ thuật: `tao_system_prompt()` được tách thành `tao_cac_phan_prompt()` trả danh sách phần `{ten, noi_dung, nguon: co_dinh|cai_dat|du_lieu_dong}`; toàn văn nối lại **không đổi một ký tự** so với cách ghép cũ (đã chứng minh bằng 69 test cũ + test_78 so payload).
- API `GET /api/cai-dat/xem-prompt-tong-quat` (chỉ quản trị viên): ghép bằng đúng hàm trên với cài đặt hiện tại; dịch vụ dùng **dịch vụ thật đang mở bán** nếu có (không có thì dòng mẫu ghi rõ), hồ sơ khách/đoạn tri thức/ký ức dùng dữ liệu mẫu đánh dấu **[DỮ LIỆU MẪU]** để admin thấy đúng vị trí chúng sẽ xuất hiện khi trả lời thật.
- Frontend: trang mới trong menu (icon `fa-scroll`, ngay sau Cài đặt) — cột trái: textarea lớn sửa `prompt_tong_quat` + nút **Lưu** nổi bật (có trạng thái "chưa lưu"/trạng thái lõi đang dùng) + nút "Xóa để về mặc định"; cột phải: danh sách các phần kèm nhãn nguồn + khung `<pre>` toàn văn đã ghép, nút "Tải lại bản ghép" và "Sao chép". Xếp chồng trên mobile. Lưu qua `PUT /api/cai-dat` hiện có — hiệu lực ngay.
- Test_78: đặt `prompt_tong_quat` → payload provider chứa đúng đoạn đó và **không** chứa câu danh tính mặc định cũ, phần động (dịch vụ/hồ sơ) vẫn còn; để trống → lõi mặc định trở lại. Test_79: endpoint xem trước trả đủ phần + toàn văn chứa cả phần cài đặt lẫn phần động `[DỮ LIỆU MẪU]`, chưa đăng nhập bị chặn, xóa về trống thì phần lõi quay về nguồn `co_dinh`.

### Tính năng 2 — Bot XEM ĐƯỢC ẢNH khách gửi
- **Sidecar** (`connectors/zalo-personal/src/index.js`): hàm `trichDinhKemAnh()` trích đính kèm từ cấu trúc thật của zca-js (đã kiểm chứng trong `node_modules/zca-js/dist/models/Message.d.ts`: tin đính kèm có `msg.data.content` là object `TAttachmentContent` với `href` = URL ảnh đầy đủ, `thumb` = URL thu nhỏ, `msg.data.msgType` vd `chat.photo`; cũng quét thêm `msg.data.attachments` nếu có). Payload webhook thêm `dinh_kem: [{loai: "anh", url, url_thumb}]` — tương thích ngược (payload cũ không đổi, chỉ thêm trường khi có ảnh). Tin **chỉ có ảnh, không chữ** trước đây bị sidecar bỏ qua, nay được chuyển về backend. Sticker không tính là ảnh.
- **Backend nhận + lưu**: webhook `/api/zalo/webhook/ca-nhan` và endpoint mô phỏng đều nhận `dinh_kem`; webhook không còn bắt buộc có chữ khi có ảnh (rỗng cả hai vẫn 400 như cũ). Model `Message` thêm cột `attachment_url` + `attachment_type` (migration ALTER an toàn trong `seed()`, kiểu TEXT/VARCHAR chạy cả Postgres lẫn SQLite, mỗi cột một giao dịch). Khi có ảnh: backend tải về thư mục `backend/uploads` qua `services/anh_service.py` — tên file là **hash SHA-256 của nội dung**, chỉ http/https, chỉ content-type ảnh, giới hạn ~10MB đọc theo luồng; tải lỗi → lưu URL gốc của Zalo thay thế. Ảnh local được phục vụ qua `GET /api/tep/{ten_file}` **bắt buộc đăng nhập**, chống path traversal (tên thuần basename + kiểm tra đường dẫn nằm trong uploads).
- **Bot trả lời có nhìn ảnh**: orchestrator đọc file local thành data URI base64 và truyền vào `generate_reply(..., anh_data_uri=...)`; payload OpenAI-compatible của lượt hiện tại dùng content dạng mảng `[{type:"text"}, {type:"image_url", image_url:{url: data URI}}]`; system prompt (cả chế độ tư vấn lẫn chế độ tự do — persona tự do vẫn giữ nguyên) được cộng hướng dẫn: khách vừa gửi ảnh, hãy mô tả/nhận xét theo ngữ cảnh và liên hệ nhu cầu/dịch vụ nếu hợp.
- **Model không hỗ trợ ảnh**: provider trả lỗi 4xx có dấu hiệu vision (nội dung lỗi nhắc image/image_url/vision/multimodal/unsupported...) → `ai_gateway` ném lỗi riêng `LoiVision`; orchestrator bắt riêng: ghi `SystemLog` **`provider_khong_ho_tro_anh`**, đánh dấu `error = "provider_khong_ho_tro_anh"` lên tin của khách (giao diện Hội thoại hiển thị ghi chú riêng "Bot chưa xem được ảnh này"), và gửi câu dự phòng lịch sự mở đầu "Dạ em đã nhận được ảnh của anh/chị rồi ạ..." — pipeline **không sập**, khách không bị im lặng.
- **Frontend Hội thoại**: bong bóng có `attachment_type = "anh"` hiển thị thẻ `<img>` thật (ảnh local tải qua `apiTaiFile` kèm token → object URL; ảnh URL gốc dùng trực tiếp), bấm vào mở tab xem lớn; tải lỗi có dòng báo thay thế, không vỡ layout.
- Test_80 (không chạm mạng/Zalo thật — monkeypatch hàm tải ảnh trả PNG 1x1 hợp lệ + monkeypatch httpx bắt payload): message lưu đúng đính kèm, file được tạo, payload provider chứa `image_url` data URI, `/api/tep` tải đúng bytes khi có token, 401 khi không đăng nhập, chặn `../` và 404 file không tồn tại. Test_81: provider báo lỗi vision → có câu dự phòng + nhật ký + dấu trên message. Test_82: webhook kênh cá nhân nhận tin chỉ-có-ảnh; tải ảnh lỗi → giữ URL gốc.
- **Giới hạn trung thực (quan trọng)**: bot "nhìn" được ảnh hay không **phụ thuộc model thật phía sau provider đang dùng** — họ model Gemini thường có vision; các model dạng DeepSeek flash có thể **không** hỗ trợ ảnh. Hệ thống không cam kết thay model: nó chỉ gửi ảnh đúng chuẩn và **tự nhận biết qua lỗi thật của provider** để chuyển sang câu dự phòng + ghi dấu cho admin như trên. Provider Mock (mô phỏng) bỏ qua ảnh và trả lời như tin thường. Ảnh chỉ được gửi kèm ở **lượt tin hiện tại** (không nhồi lại ảnh cũ vào mọi lượt sau để tránh tốn token); tin ảnh trong NHÓM vẫn chịu luật chỉ trả lời khi được tag đích danh như tin chữ. Chưa kiểm chứng end-to-end với Zalo thật + model có vision thật trong đợt này (đường ống đã kiểm chứng bằng mô phỏng sát cấu trúc zca-js thật).
