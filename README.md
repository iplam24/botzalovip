# botzalovip

**Zalo AI Hub** — Nền tảng AI tự động hóa hội thoại Zalo: quản trị hội thoại, kho tri thức, bộ nhớ dài hạn, quy tắc tự động hóa và kết nối Zalo (OA / cá nhân qua sidecar zca-js / mô phỏng), giao diện tiếng Việt toàn bộ.

Nền tảng AI tự động hóa hội thoại Zalo - MVP chạy thực tế, giao diện tiếng Việt toàn bộ.

> **Giới hạn quan trọng:** Xem `docs/GIOI_HAN_ZALO.md`. Tài khoản Zalo cá nhân **không có API công khai chính thức**. MVP dùng Mock Connector (mô phỏng, ghi rõ) + Zalo OA Stub (chưa hỗ trợ nếu thiếu token OA) + sidecar Zalo cá nhân zca-js tại `connectors/zalo-personal/` (đăng nhập QR do người dùng tự quét, có cảnh báo rủi ro). Không bypass CAPTCHA/OTP, không fake kết nối thật.

## Chạy local - Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate | Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Đăng nhập mặc định (phải đổi ngay): `admin@local` / `Admin@12345` (đọc từ `ADMIN_EMAIL`/`ADMIN_PASSWORD`).
Kiểm tra: http://localhost:8000/api/suc-khoe - Tài liệu API: http://localhost:8000/docs

## Chạy local - Frontend
```bash
cd frontend
npm install
npm run dev
# Mở http://localhost:5173 (Vite proxy /api -> http://localhost:8000)
```
Bản đóng gói production (đã kiểm chứng build thành công — TypeScript + Vite):
```bash
cd frontend
npm run build     # tsc -b && vite build, kết quả trong frontend/dist/
npm run preview   # xem thử bản build
```

## Zalo cá nhân (sidecar zca-js)
```bash
cd connectors/zalo-personal && npm install && npm start   # http://localhost:8791
```
Sau đó vào giao diện → Tài khoản Zalo → Tạo QR mới và quét bằng điện thoại. Backend proxy qua `ZALO_PERSONAL_SERVICE_URL` (mặc định `http://localhost:8791`); sidecar chưa chạy thì trạng thái là “Mất kết nối / Chưa chạy dịch vụ Zalo cá nhân”, không fake kết nối.

## Nhà cung cấp AI “LAM Token - code”
Hệ thống seed sẵn cấu hình mẫu **LAM Token - code** (endpoint tương thích OpenAI, model `code`) với khóa API **rỗng** và trạng thái “Chưa cấu hình”. Đặt khóa thật qua giao diện Nhà cung cấp AI hoặc env `TEST_AI_API_KEY` ở môi trường local — tuyệt đối không ghi khóa vào code/git. Gateway luôn gửi `stream: false` và vẫn parse được SSE dự phòng.

## Docker Compose
```bash
docker compose up --build
# Backend :8000, Frontend :5173, PostgreSQL pgvector:pg16, Redis 7
```

## Kiểm thử
```bash
cd backend && python -m pytest tests/test_mvp.py -v   # 29 passed
cd frontend && npm run build                          # phải build thành công
```
Kết quả nghiệm thu: xem `BAO_CAO_NGHIEM_THU.md`. Trạng thái mã QR Zalo cá nhân mới nhất: xem `QR_TRANG_THAI.md`.

## Cấu trúc
- `backend/app/` - FastAPI modular monolith (routers/, services/, models.py, security.py)
- `frontend/src/` - React + TypeScript + Vite + Tailwind, toàn bộ nhãn tiếng Việt
- `docs/` - Hướng dẫn Windows, Linux/VPS, giới hạn Zalo
