"""Kiểm thử Đợt nâng cấp 3 + mục nhỏ đổi mật khẩu — dùng chung DB test +
TestClient của test_mvp (pytest chạy theo thứ tự tên file: mvp < 2 < 3)."""
import os, sys
os.chdir(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DATABASE_URL"] = "sqlite:///./test_zalo.db"

from test_mvp import client, headers  # noqa: E402,F401


def _dat_cai_dat(**kw):
    r = client.put("/api/cai-dat", json=kw, headers=headers())
    assert r.status_code == 200, r.text
    return r.json()


# ---- Mục nhỏ: ĐỔI MẬT KHẨU TỰ PHỤC VỤ ----

def test_71_doi_mat_khau_tu_phuc_vu():
    # Tạo một nhân viên riêng để không đụng mật khẩu admin dùng chung
    r = client.post("/api/auth/nguoi-dung", json={
        "username": "nv_dot3", "email": "nv_dot3@local", "password": "MatKhauCu1",
        "full_name": "Nhân viên Đợt 3", "role": "NhanVien",
    }, headers=headers())
    assert r.status_code == 200, r.text

    def dang_nhap(mat_khau):
        return client.post("/api/auth/login", json={"username": "nv_dot3", "password": mat_khau})

    r = dang_nhap("MatKhauCu1")
    assert r.status_code == 200, r.text
    h_nv = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # Chưa đăng nhập -> 401
    r = client.post("/api/auth/doi-mat-khau", json={"mat_khau_cu": "MatKhauCu1", "mat_khau_moi": "MatKhauMoi1"})
    assert r.status_code == 401, r.text

    # Sai mật khẩu hiện tại -> 400 đúng thông điệp
    r = client.post("/api/auth/doi-mat-khau", json={"mat_khau_cu": "SaiMatKhau9", "mat_khau_moi": "MatKhauMoi1"}, headers=h_nv)
    assert r.status_code == 400 and "Mật khẩu hiện tại không đúng" in r.text, r.text

    # Mật khẩu mới quá ngắn -> 400
    r = client.post("/api/auth/doi-mat-khau", json={"mat_khau_cu": "MatKhauCu1", "mat_khau_moi": "abc"}, headers=h_nv)
    assert r.status_code == 400, r.text

    # Đổi đúng -> 200
    r = client.post("/api/auth/doi-mat-khau", json={"mat_khau_cu": "MatKhauCu1", "mat_khau_moi": "MatKhauMoi1"}, headers=h_nv)
    assert r.status_code == 200, r.text

    # Mật khẩu cũ bị từ chối, mật khẩu mới đăng nhập được
    assert dang_nhap("MatKhauCu1").status_code == 401
    assert dang_nhap("MatKhauMoi1").status_code == 200

    # Nhật ký module "auth" có sự kiện đổi mật khẩu, KHÔNG chứa giá trị mật khẩu
    r = client.get("/api/nhat-ky?module=auth", headers=headers())
    assert r.status_code == 200
    noi_dung = r.text
    assert "đổi mật khẩu" in noi_dung
    assert "MatKhauMoi1" not in noi_dung and "MatKhauCu1" not in noi_dung


# ---- Mục 1: PHÂN TRANG phía máy chủ ----

def test_72_phan_trang_khach_hang_va_shape_cac_endpoint():
    for i in range(1, 28):
        r = client.post("/api/khach-hang", json={"display_name": f"TrangKiemTra {i:02d}"}, headers=headers())
        assert r.status_code == 200, r.text

    # Không truyền trang -> giữ nguyên list thuần (không phá vỡ nơi đang dùng)
    r = client.get("/api/khach-hang?tu_khoa=TrangKiemTra", headers=headers())
    assert r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) == 27, r.text

    # Trang 1/2/3 với kích thước 10: tổng + tổng trang + số mục từng trang đúng
    t1 = client.get("/api/khach-hang?tu_khoa=TrangKiemTra&trang=1&kich_thuoc_trang=10", headers=headers()).json()
    assert t1["tong"] == 27 and t1["tong_trang"] == 3 and t1["trang"] == 1 and len(t1["muc"]) == 10, t1
    t2 = client.get("/api/khach-hang?tu_khoa=TrangKiemTra&trang=2&kich_thuoc_trang=10", headers=headers()).json()
    t3 = client.get("/api/khach-hang?tu_khoa=TrangKiemTra&trang=3&kich_thuoc_trang=10", headers=headers()).json()
    assert len(t2["muc"]) == 10 and len(t3["muc"]) == 7
    id_tat_ca = [c["id"] for c in t1["muc"] + t2["muc"] + t3["muc"]]
    assert len(set(id_tat_ca)) == 27  # các trang rời nhau, không trùng/thiếu

    # Kích thước trang ngoài danh sách cho phép -> rơi về mặc định 20
    t = client.get("/api/khach-hang?tu_khoa=TrangKiemTra&trang=1&kich_thuoc_trang=7", headers=headers()).json()
    assert t["kich_thuoc_trang"] == 20 and len(t["muc"]) == 20, t

    # Bộ lọc được GIỮ NGUYÊN khi phân trang: lọc hẹp còn đúng 10 khách (10..19)
    t = client.get("/api/khach-hang?tu_khoa=TrangKiemTra%201&trang=1&kich_thuoc_trang=10", headers=headers()).json()
    assert t["tong"] == 10 and all("TrangKiemTra 1" in c["display_name"] for c in t["muc"]), t

    # Các endpoint danh sách khác: có trang -> đúng shape; không trang -> list thuần
    for duong_dan in ("/api/hoi-thoai", "/api/ban-be-zalo", "/api/thong-bao",
                      "/api/nhat-ky", "/api/bo-nho", "/api/tri-thuc/tai-lieu"):
        r = client.get(f"{duong_dan}?trang=1&kich_thuoc_trang=10", headers=headers())
        assert r.status_code == 200, (duong_dan, r.text)
        d = r.json()
        assert isinstance(d, dict) and "muc" in d and "tong" in d and "tong_trang" in d, (duong_dan, d)
        r2 = client.get(duong_dan, headers=headers())
        assert isinstance(r2.json(), list), (duong_dan, r2.text)


# ---- Mục 2: CẤU HÌNH QUA CHAT ----

def test_73_cau_hinh_qua_chat_quy_tac_va_ap_dung(monkeypatch):
    from app.database import SessionLocal
    from app.models import AIProviderConfig
    from app.services import cau_hinh_chat_service as chs
    # Ép đường phân tích QUY TẮC (provider Mock) cho tất định, dù DB test đang
    # có provider mặc định nào sau các test trước
    db = SessionLocal()
    try:
        mock = db.query(AIProviderConfig).filter(AIProviderConfig.provider == "mock").first()
    finally:
        db.close()
    monkeypatch.setattr(chs.ai_gateway, "get_default_provider", lambda _db: mock)

    _dat_cai_dat(che_do_tro_chuyen_tu_do=False)

    # Phân tích lệnh bật chế độ tự do -> đúng khóa + giá trị cũ/mới
    r = client.post("/api/cau-hinh-chat/phan-tich", json={"cau_lenh": "Bật chế độ trò chuyện tự do"}, headers=headers())
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["nguon"] == "quy_tac", d
    td = [t for t in d["thay_doi"] if t["khoa"] == "che_do_tro_chuyen_tu_do"]
    assert td and td[0]["gia_tri_moi"] is True and td[0]["gia_tri_cu"] is False, d

    # CHƯA duyệt -> cài đặt thật chưa đổi
    assert client.get("/api/cai-dat", headers=headers()).json()["che_do_tro_chuyen_tu_do"] is False

    # Áp dụng -> đổi thật + có nhật ký module cau_hinh_qua_chat
    r = client.post("/api/cau-hinh-chat/ap-dung",
                    json={"thay_doi": [{"khoa": "che_do_tro_chuyen_tu_do", "gia_tri": True}]},
                    headers=headers())
    assert r.status_code == 200 and len(r.json()["da_ap_dung"]) == 1, r.text
    assert client.get("/api/cai-dat", headers=headers()).json()["che_do_tro_chuyen_tu_do"] is True
    r = client.get("/api/nhat-ky?module=cau_hinh_qua_chat", headers=headers())
    assert r.status_code == 200 and len(r.json()) >= 1

    # Lệnh đặt số + lệnh đổi lựa chọn (select) qua bộ quy tắc
    d = client.post("/api/cau-hinh-chat/phan-tich", json={"cau_lenh": "Đặt nhiệt độ AI thành 0.7"}, headers=headers()).json()
    td = [t for t in d["thay_doi"] if t["khoa"] == "ai_temperature"]
    assert td and abs(td[0]["gia_tri_moi"] - 0.7) < 1e-9, d
    d = client.post("/api/cau-hinh-chat/phan-tich", json={"cau_lenh": "Đổi giọng bot sang ngắn gọn"}, headers=headers()).json()
    td = [t for t in d["thay_doi"] if t["khoa"] == "bot_giong_dieu"]
    assert td and td[0]["gia_tri_moi"] == "ngan_gon_thang_than", d

    # Dọn dẹp: tắt lại chế độ tự do
    _dat_cai_dat(che_do_tro_chuyen_tu_do=False)


def test_74_cau_hinh_qua_chat_ai_monkeypatch_khoa_bia_bi_loai(monkeypatch):
    from types import SimpleNamespace
    from app.services import cau_hinh_chat_service as chs
    gia = SimpleNamespace(provider="openai_compatible", model="gia", base_url="http://localhost:9",
                          api_key_encrypted="", timeout=5, id=999)
    monkeypatch.setattr(chs.ai_gateway, "get_default_provider", lambda _db: gia)
    monkeypatch.setattr(chs, "_phan_tich_bang_ai", lambda _db, _p, _lenh: [
        {"khoa": "ai_temperature", "gia_tri": 0.9},
        {"khoa": "khoa_bia_khong_co_that", "gia_tri": 123},
    ])
    r = client.post("/api/cau-hinh-chat/phan-tich", json={"cau_lenh": "giảm nhiệt độ ai và bật khóa bịa"}, headers=headers())
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["nguon"] == "ai"
    khoa = [t["khoa"] for t in d["thay_doi"]]
    assert khoa == ["ai_temperature"], d  # khóa bịa bị loại, chỉ còn khóa thật

    # Áp dụng thẳng khóa bịa -> 400, không áp dụng một phần
    r = client.post("/api/cau-hinh-chat/ap-dung",
                    json={"thay_doi": [{"khoa": "khoa_bia_khong_co_that", "gia_tri": 1}]},
                    headers=headers())
    assert r.status_code == 400, r.text


# ---- Mục 3: VECTOR DB ----

def test_75_vector_nhung_fake_va_trang_thai(monkeypatch):
    monkeypatch.setenv("EMBEDDING_FAKE", "1")
    r = client.post("/api/tri-thuc/tai-lieu", json={
        "title": "VectorKiemTra Dot3",
        "content": "Dich vu giao hang tan noi nhanh chong tien loi cho khach hang o xa, ho tro doi tra trong bay ngay.",
    }, headers=headers())
    assert r.status_code == 200, r.text
    doc_id = r.json()["id"]

    from app.database import SessionLocal
    from app.models import KnowledgeChunk, MemoryItem
    db = SessionLocal()
    try:
        chunk = db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == doc_id).first()
        assert chunk is not None and chunk.embedding, "chunk phải có embedding khi EMBEDDING_FAKE=1"
    finally:
        db.close()

    # Trạng thái vector: nguồn fake, sẵn sàng, đã nhúng >= 1
    r = client.get("/api/tri-thuc/trang-thai-vector", headers=headers())
    assert r.status_code == 200, r.text
    tt = r.json()
    assert tt["nguon"] == "fake" and tt["san_sang"] is True and tt["da_nhung"] >= 1, tt

    # Tạo ký ức -> cũng được nhúng ngay
    r = client.post("/api/bo-nho", json={"content": "Ký ức vector kiểm tra đợt ba", "memory_type": "ngu_nghia"}, headers=headers())
    assert r.status_code == 200, r.text
    mid = r.json()["id"]
    db = SessionLocal()
    try:
        m = db.get(MemoryItem, mid)
        assert m is not None and m.embedding, "ký ức mới phải có embedding khi EMBEDDING_FAKE=1"
    finally:
        db.close()

    # Nhúng lại toàn bộ -> mọi đoạn đều có vector
    r = client.post("/api/tri-thuc/nhung-lai-tat-ca", headers=headers())
    assert r.status_code == 200, r.text
    tt = r.json()
    assert tt["da_nhung"] == tt["tong_chunk"] and tt["tong_chunk"] >= 1, tt


def test_76_vector_xep_hang_cosine_va_tat_cai_dat(monkeypatch):
    import json as _json
    from app.database import SessionLocal
    from app.models import KnowledgeDocument, KnowledgeChunk
    from app.services import embedding_service, knowledge_service

    _dat_cai_dat(tim_kiem_ngu_nghia=True)
    db = SessionLocal()
    try:
        doc = KnowledgeDocument(title="VectorXepHang Dot3", content="noi dung goc", is_active=True)
        db.add(doc); db.flush()
        a = KnowledgeChunk(document_id=doc.id, content="alpha beta gamma", normalized="alpha beta gamma",
                           chunk_index=0, embedding=_json.dumps([1.0, 0.0, 0.0]))
        b = KnowledgeChunk(document_id=doc.id, content="delta epsilon zeta", normalized="delta epsilon zeta",
                           chunk_index=1, embedding=_json.dumps([0.0, 1.0, 0.0]))
        db.add_all([a, b]); db.commit()
        id_a, id_b = a.id, b.id

        # Truy vấn KHÔNG trùng từ khóa nào; vector truy vấn trùng hướng đoạn A
        monkeypatch.setattr(embedding_service, "nhung_mot", lambda _db, _text: [1.0, 0.0, 0.0])
        kq = knowledge_service.retrieve(db, "zzzqqq wwwvvv")
        theo_id = {r["chunk_id"]: r for r in kq}
        assert id_a in theo_id, kq
        assert theo_id[id_a]["diem_ngu_nghia"] is not None and theo_id[id_a]["diem_ngu_nghia"] > 0.99, theo_id[id_a]
        assert id_b not in theo_id  # cosine = 0 < ngưỡng -> không lọt kết quả

        # Tắt cài đặt tìm ngữ nghĩa -> chỉ còn đường từ khóa (truy vấn trên rỗng)
        _dat_cai_dat(tim_kiem_ngu_nghia=False)
        kq2 = knowledge_service.retrieve(db, "zzzqqq wwwvvv")
        assert id_a not in {r["chunk_id"] for r in kq2}
    finally:
        db.close()
        _dat_cai_dat(tim_kiem_ngu_nghia=True)


# ---- Mục 4 (phần dữ liệu): Tổng quan có hoạt động 7 ngày cho mini bar chart ----

def test_77_tong_quan_co_hoat_dong_7_ngay():
    from datetime import date
    r = client.get("/api/tong-quan", headers=headers())
    assert r.status_code == 200, r.text
    hd = r.json()["hoat_dong_7_ngay"]
    assert isinstance(hd, list) and len(hd) == 7, hd
    assert hd[-1]["ngay"] == date.today().isoformat()
    assert all("tong" in d and "tin_khach" in d and "tin_bot" in d for d in hd)
