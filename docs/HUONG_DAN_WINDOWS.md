# Hướng dẫn triển khai trên Windows

1. Cài Python 3.12, Node.js 20, Git. Kiểm tra: `python --version`, `node --version`.
2. Mở PowerShell tại thư mục dự án.
3. Backend:
   ```powershell
   cd backend; python -m venv .venv; .venv\Scripts\Activate.ps1; pip install -r requirements.txt
   Copy-Item ..\.env.example .env  # sửa SECRET_KEY, ADMIN_PASSWORD
   uvicorn app.main:app --reload --port 8000
   ```
4. Frontend (cửa sổ mới): `cd frontend; npm install; npm run dev` rồi mở http://localhost:5173
5. Lỗi thường gặp: cổng 8000/5173 bị chiếm (đổi `--port`), PowerShell chặn script (`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`), thiếu module (chạy lại `pip install -r requirements.txt` trong venv đã kích hoạt).
6. Kiểm tra sức khỏe: http://localhost:8000/api/suc-khoe
