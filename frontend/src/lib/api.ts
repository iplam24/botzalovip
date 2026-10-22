// Lớp gọi API thật qua /api — đính kèm JWT từ localStorage, xử lý lỗi thống nhất.
export async function docLoi(res: Response): Promise<string> {
  try {
    const text = await res.text();
    if (!text) return `Lỗi ${res.status}`;
    try {
      const j = JSON.parse(text);
      return j.detail || j.thong_bao || text;
    } catch {
      return text;
    }
  } catch {
    return `Lỗi ${res.status}`;
  }
}

export async function api<T = any>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("token");
  const res = await fetch(path, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers || {}),
    },
  });
  if (!res.ok) throw new Error(await docLoi(res));
  if (res.status === 204) return null as T;
  return res.json() as Promise<T>;
}

// Tải file (ví dụ xuất CSV) kèm JWT, trả về blob để trình duyệt tải xuống.
export async function apiTaiFile(path: string): Promise<{ blob: Blob; tenFile: string }> {
  const token = localStorage.getItem("token");
  const res = await fetch(path, { headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) } });
  if (!res.ok) throw new Error(await docLoi(res));
  const cd = res.headers.get("content-disposition") || "";
  const m = cd.match(/filename="?([^";]+)"?/);
  return { blob: await res.blob(), tenFile: m ? m[1] : "bao-cao.csv" };
}

export function taiBlobXuong(blob: Blob, tenFile: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = tenFile;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

// Đăng nhập bằng USERNAME + MẬT KHẨU (đính chính: username thay email, vẫn có mật khẩu).
export const dangNhap = async (username: string, password: string) => {
  const r = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!r.ok) {
    let chiTiet = "Tên đăng nhập hoặc mật khẩu không đúng, hoặc tài khoản đã bị khóa";
    try {
      const j = await r.json();
      if (j.detail) chiTiet = j.detail;
    } catch { /* giữ thông báo mặc định */ }
    throw new Error(chiTiet);
  }
  const d = await r.json();
  localStorage.setItem("token", d.access_token);
  return d;
};

// Định dạng ngày giờ ISO (UTC từ backend) sang DD/MM/YYYY HH:mm giờ địa phương.
export function dinhDangThoiGian(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z");
  if (isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function dinhDangSo(n?: number | null): string {
  if (n === null || n === undefined) return "0";
  return new Intl.NumberFormat("vi-VN").format(n);
}
