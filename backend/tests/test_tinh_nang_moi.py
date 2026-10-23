"""Kiểm thử 2 tính năng mới (23/10/2026):
1) Trang Prompt tổng quát — khóa cài đặt `prompt_tong_quat` thay phần lõi
   mặc định trong system prompt + API xem trước bản ghép.
2) Bot xem được ảnh khách gửi — webhook dinh_kem -> tải ảnh về uploads ->
   payload multimodal (image_url data URI) -> dự phòng khi model không
   hỗ trợ ảnh + endpoint /api/tep có khóa đăng nhập & chống path traversal.

Không phụ thuộc mạng/Zalo thật: hàm tải ảnh và httpx.Client đều monkeypatch.
Chạy SAU test_mvp / test_nang_cap_2 / test_nang_cap_3 (dùng chung DB test).
"""
import base64
import json
import os

from test_mvp import client, headers

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII=")


def _dat_provider_mac_dinh_theo_ten(ten):
    ds = client.get("/api/ai-providers", headers=headers()).json()
    p = [x for x in ds if x["name"] == ten][0]
    r = client.put(f"/api/ai-providers/{p['id']}", json={"is_default": True}, headers=headers())
    assert r.status_code == 200, r.text
    return p["id"]


def _bat_httpx(monkeypatch, che_do="ok"):
    """Chặn httpx.Client: bắt payload gửi provider; che_do='loi_vision' thì
    trả 400 có dấu hiệu model không hỗ trợ ảnh."""
    import httpx as _httpx
    captured = {}

    class FakeResp:
        def __init__(self):
            if che_do == "loi_vision":
                self.status_code = 400
                self.text = json.dumps({"error": {"message": "image_url is not supported by this model: vision input unsupported"}})
            else:
                self.status_code = 200
                self.text = json.dumps({"model": "m-gia-lap", "choices": [{"message": {"content": "Em thấy trong ảnh có một chú mèo rất dễ thương ạ."}}],
                                         "usage": {"prompt_tokens": 9, "completion_tokens": 4}})
            self.headers = {"content-type": "application/json"}

    class FakeClient:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, url, headers=None, json=None):
            captured.clear(); captured.update(json or {})
            captured["_url"] = url
            return FakeResp()
        def get(self, url, headers=None):
            return FakeResp()

    monkeypatch.setattr(_httpx, "Client", FakeClient)
    return captured


def _gia_lap_tai_anh(monkeypatch, ten_file="anh-test-1x1.png"):
    """Thay hàm tải ảnh thật bằng bản ghi sẵn PNG 1x1 hợp lệ vào thư mục uploads."""
    from app.services import anh_service
    os.makedirs(anh_service.THU_MUC_UPLOADS, exist_ok=True)
    duong_dan = os.path.join(anh_service.THU_MUC_UPLOADS, ten_file)
    with open(duong_dan, "wb") as f:
        f.write(PNG_1X1)

    def _tai_gia(url):
        return {"ten_file": ten_file, "duong_dan": duong_dan, "mime": "image/png", "kich_thuoc": len(PNG_1X1)}

    monkeypatch.setattr(anh_service, "tai_anh_tu_url", _tai_gia)
    return duong_dan


# ---------- Tính năng 1: Prompt tổng quát ----------

def test_78_prompt_tong_quat_thay_loi_mac_dinh(monkeypatch):
    # Registry có khóa mới đúng khai báo
    d = client.get("/api/cai-dat/dang-ky", headers=headers()).json()
    theo_khoa = {c["khoa"]: c for c in d["cai_dat"]}
    assert "prompt_tong_quat" in theo_khoa
    assert theo_khoa["prompt_tong_quat"]["kieu"] == "textarea"
    assert theo_khoa["prompt_tong_quat"]["nhom"] == "phong_cach"
    assert theo_khoa["prompt_tong_quat"]["mac_dinh"] == ""

    captured = _bat_httpx(monkeypatch)
    from app.database import SessionLocal
    from app.models import AIProviderConfig
    from app.services import ai_gateway
    db = SessionLocal()
    try:
        provider = db.query(AIProviderConfig).filter(AIProviderConfig.name == "Provider stream test").first()
        assert provider is not None
        dau = "PROMPT_TONG_QUAT_TEST_78 ban la tro ly rieng cua shop, chi noi ve hai san."
        # Có prompt_tong_quat: payload chứa đúng đoạn đó, KHÔNG chứa câu danh tính mặc định cũ,
        # nhưng các phần động (dịch vụ, hồ sơ) vẫn được chắp phía sau.
        ai_gateway.generate_reply(
            db, provider, "Chào shop", [{"content": "tri thuc 78"}], [],
            lich_su=[], cai_dat={"prompt_tong_quat": dau},
            dich_vu=[{"ten": "DV78 Hai San", "gia": "", "mo_ta": ""}], ho_so_khach="Ho so khach 78")
        system = captured["messages"][0]["content"]
        assert dau in system
        assert "vai trò của bạn: trợ lý hỗ trợ khách hàng" not in system
        assert "DV78 Hai San" in system and "Ho so khach 78" in system
        # Để trống: phần lõi mặc định trở lại nguyên vẹn
        ai_gateway.generate_reply(
            db, provider, "Chào shop", [], [], lich_su=[], cai_dat={"prompt_tong_quat": ""})
        system2 = captured["messages"][0]["content"]
        assert "vai trò của bạn: trợ lý hỗ trợ khách hàng" in system2
        assert dau not in system2
    finally:
        db.close()


def test_79_xem_prompt_tong_quat_endpoint():
    dau = "PROMPT_XEM_TRUOC_79: loi rieng do admin dat."
    r = client.put("/api/cai-dat", json={"prompt_tong_quat": dau}, headers=headers())
    assert r.status_code == 200, r.text
    try:
        # Không đăng nhập -> bị chặn
        assert client.get("/api/cai-dat/xem-prompt-tong-quat").status_code in (401, 403)
        kq = client.get("/api/cai-dat/xem-prompt-tong-quat", headers=headers()).json()
        assert kq["cac_phan"] and kq["toan_van"]
        # Phần đầu là phần lõi từ CÀI ĐẶT (prompt_tong_quat vừa đặt)
        assert kq["cac_phan"][0]["nguon"] == "cai_dat"
        assert dau in kq["cac_phan"][0]["noi_dung"]
        # Toàn văn chứa cả phần cài đặt lẫn phần dữ liệu động (mẫu)
        assert dau in kq["toan_van"]
        assert "[DỮ LIỆU MẪU]" in kq["toan_van"]
        nguon = {p["nguon"] for p in kq["cac_phan"]}
        assert "du_lieu_dong" in nguon
        for p in kq["cac_phan"]:
            assert p["nguon"] in ("co_dinh", "cai_dat", "du_lieu_dong") and p["ten"] and p["noi_dung"]
    finally:
        # Xóa về trống -> mặc định trở lại ở cả API cài đặt lẫn bản ghép
        r = client.put("/api/cai-dat", json={"prompt_tong_quat": ""}, headers=headers())
        assert r.status_code == 200, r.text
    cd = client.get("/api/cai-dat", headers=headers()).json()
    assert cd["prompt_tong_quat"] == ""
    kq2 = client.get("/api/cai-dat/xem-prompt-tong-quat", headers=headers()).json()
    assert kq2["cac_phan"][0]["nguon"] == "co_dinh"
    assert "trợ lý hỗ trợ khách hàng của doanh nghiệp trên Zalo" in kq2["toan_van"]


# ---------- Tính năng 2: Bot xem được ảnh ----------

def test_80_webhook_anh_luu_file_va_payload_multimodal(monkeypatch):
    duong_dan_file = _gia_lap_tai_anh(monkeypatch)
    _dat_provider_mac_dinh_theo_ten("Provider stream test")
    try:
        captured = _bat_httpx(monkeypatch)
        r = client.post("/api/zalo/mock/nhan-tin-nhan", json={
            "external_id": "anh-80-1", "customer_external_id": "khach-anh-80",
            "customer_name": "Khách Ảnh 80", "content": "Ảnh này đẹp không shop?",
            "dinh_kem": [{"loai": "anh", "url": "https://zalo.example/anh80.jpg",
                          "url_thumb": "https://zalo.example/anh80-thumb.jpg"}]},
            headers=headers())
        assert r.status_code == 200, r.text
        assert r.json().get("tra_loi"), r.text
        # File ảnh đã được tạo trên đĩa
        assert os.path.isfile(duong_dan_file)
        # Tin của khách được lưu kèm đính kèm, trỏ vào /api/tep/<file>
        cid = r.json()["conversation_id"]
        ct = client.get(f"/api/hoi-thoai/{cid}", headers=headers()).json()
        tin_khach = [m for m in ct["messages"] if m["sender_type"] == "khach"][0]
        assert tin_khach["attachment_type"] == "anh"
        assert tin_khach["attachment_url"].startswith("/api/tep/")
        # Payload gửi provider: lượt user hiện tại là mảng multimodal có image_url data URI
        tin_user_cuoi = [m for m in captured["messages"] if m["role"] == "user"][-1]
        assert isinstance(tin_user_cuoi["content"], list), tin_user_cuoi
        loai_phan = [p.get("type") for p in tin_user_cuoi["content"]]
        assert "text" in loai_phan and "image_url" in loai_phan
        phan_anh = [p for p in tin_user_cuoi["content"] if p.get("type") == "image_url"][0]
        assert phan_anh["image_url"]["url"].startswith("data:image/png;base64,")
        # System prompt có hướng dẫn xem ảnh
        assert "ẢNH" in captured["messages"][0]["content"]
        # Endpoint tệp: có đăng nhập thì tải được đúng bytes ảnh
        ten_file = tin_khach["attachment_url"].rsplit("/", 1)[-1]
        rfile = client.get(f"/api/tep/{ten_file}", headers=headers())
        assert rfile.status_code == 200 and rfile.content == PNG_1X1
        # Không đăng nhập -> 401
        assert client.get(f"/api/tep/{ten_file}").status_code == 401
        # Path traversal -> không lọt được file ngoài thư mục uploads
        for ten_xau in ["..%2F..%2Fzalo_ai_hub.db", "..%2Fsecret.txt", "%2e%2e%2fapp.db"]:
            rx = client.get(f"/api/tep/{ten_xau}", headers=headers())
            assert rx.status_code in (400, 404), (ten_xau, rx.status_code)
            assert b"sqlite" not in rx.content.lower()
        # Tên file sạch nhưng không tồn tại -> 404
        assert client.get("/api/tep/khong-ton-tai-80.png", headers=headers()).status_code == 404
    finally:
        _dat_provider_mac_dinh_theo_ten("Mock AI (mô phỏng)")


def test_81_provider_khong_ho_tro_anh_co_cau_du_phong(monkeypatch):
    _gia_lap_tai_anh(monkeypatch, ten_file="anh-test-81.png")
    _dat_provider_mac_dinh_theo_ten("Provider stream test")
    try:
        _bat_httpx(monkeypatch, che_do="loi_vision")
        r = client.post("/api/zalo/mock/nhan-tin-nhan", json={
            "external_id": "anh-81-1", "customer_external_id": "khach-anh-81",
            "customer_name": "Khách Ảnh 81", "content": "Shop xem ảnh này giúp mình",
            "dinh_kem": [{"loai": "anh", "url": "https://zalo.example/anh81.jpg", "url_thumb": ""}]},
            headers=headers())
        assert r.status_code == 200, r.text
        tra_loi = r.json().get("tra_loi") or ""
        # Câu dự phòng lịch sự, pipeline không sập
        assert "đã nhận được ảnh" in tra_loi, tra_loi
        # Có nhật ký provider_khong_ho_tro_anh + tin khách được đánh dấu
        from app.database import SessionLocal
        from app.models import SystemLog, Message
        db = SessionLocal()
        try:
            log = db.query(SystemLog).filter(SystemLog.message.like("%provider_khong_ho_tro_anh%")).first()
            assert log is not None
            tin = db.query(Message).filter(Message.external_id == "anh-81-1").first()
            assert tin is not None and tin.attachment_type == "anh"
            assert tin.error == "provider_khong_ho_tro_anh"
        finally:
            db.close()
    finally:
        _dat_provider_mac_dinh_theo_ten("Mock AI (mô phỏng)")


def test_82_webhook_ca_nhan_nhan_tin_chi_co_anh(monkeypatch):
    # Webhook kênh cá nhân: tin KHÔNG có chữ nhưng có dinh_kem ảnh -> vẫn nhận
    # (trước đây bị 400). Không có chữ và không có ảnh -> vẫn 400 như cũ.
    # Hàm tải ảnh được thay bằng bản LUÔN LỖI để kiểm đường dự phòng lưu URL gốc
    # (và để test không chạm mạng thật).
    from app.services import anh_service
    monkeypatch.setattr(anh_service, "tai_anh_tu_url", lambda url: None)
    r = client.post("/api/zalo/webhook/ca-nhan", json={
        "external_id": "wh-anh-82", "thread_id": "khach-webhook-82",
        "sender_name": "Khách Webhook 82", "content": "",
        "dinh_kem": [{"loai": "anh", "url": "https://zalo.example/wh82.jpg", "url_thumb": ""}]})
    assert r.status_code == 200, r.text
    assert r.json().get("conversation_id")
    from app.database import SessionLocal
    from app.models import Message
    db = SessionLocal()
    try:
        tin = db.query(Message).filter(Message.external_id == "wh-anh-82").first()
        assert tin is not None and tin.attachment_type == "anh"
        # Tải lỗi -> giữ nguyên URL gốc của Zalo
        assert tin.attachment_url == "https://zalo.example/wh82.jpg"
    finally:
        db.close()
    r2 = client.post("/api/zalo/webhook/ca-nhan", json={
        "external_id": "wh-rong-82", "thread_id": "khach-webhook-82", "content": ""})
    assert r2.status_code == 400, r2.text
