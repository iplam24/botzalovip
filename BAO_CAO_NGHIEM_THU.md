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
