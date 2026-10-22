# Hướng dẫn triển khai trên Linux / VPS

1. Cài Docker + Docker Compose (khuyến nghị) hoặc Python 3.12 + Node 20 + PostgreSQL 16.
2. Docker: `cp .env.example backend/.env` (sửa secret), `docker compose up -d --build`, kiểm tra `docker compose ps` và `curl http://localhost:8000/api/suc-khoe`.
3. Không dùng Docker: tạo venv, `pip install -r backend/requirements.txt`, đặt `DATABASE_URL=postgresql://...`, chạy migration bằng Alembic (`cd backend && alembic upgrade head` - MVP cũng tự tạo bảng khi khởi động để chạy local), chạy `uvicorn app.main:app --host 0.0.0.0 --port 8000` dưới systemd.
4. Reverse proxy: dùng Nginx/Caddy trỏ `/api` tới :8000, frontend tới :5173 (hoặc bản build tĩnh), bật HTTPS bằng Let's Encrypt khi triển khai qua mạng.
5. Sao lưu: dùng phân hệ Sao lưu và khôi phục trong giao diện + sao lưu volume `pgdata` định kỳ. Kiểm tra log: `docker compose logs -f backend`.
6. Nâng cấp: `git pull`, `docker compose up -d --build`, chạy lại pytest trước khi đưa vào vận hành.
