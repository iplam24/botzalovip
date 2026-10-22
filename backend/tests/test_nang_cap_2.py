"""Kiểm thử Đợt nâng cấp 2 — dùng chung DB test + TestClient của test_mvp.

Thứ tự file: pytest chạy test_mvp.py trước (theo tên file), file này import
client/headers từ test_mvp nên dùng chung trạng thái (quy tắc, khách...) đã seed.
"""
import os, sys
os.chdir(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DATABASE_URL"] = "sqlite:///./test_zalo.db"

from test_mvp import client, headers  # noqa: E402,F401


def _dat_cai_dat(**kw):
    r = client.put("/api/cai-dat", json=kw, headers=headers())
    assert r.status_code == 200, r.text
    return r.json()


# ---- Mục 1 + 9.3: đăng nhập chỉ username, tài khoản bị khóa, trang người dùng ----
def test_41_dang_nhap_chi_username():
    r_ok = client.post("/api/auth/login", json={"username": "admin"})
    assert r_ok.status_code == 200 and r_ok.json()["username"] == "admin"
    # Sai username -> 401
    assert client.post("/api/auth/login", json={"username": "khong-ton-tai"}).status_code == 401
    # Đăng nhập kiểu cũ email/mật khẩu bị loại bỏ: thiếu username -> 422 (schema chỉ nhận username)
    assert client.post("/api/auth/login", json={"email": "admin@local", "password": "Admin@12345"}).status_code == 422
    # Tạo người dùng có username riêng rồi đăng nhập được; ghi last_login_at
    r = client.post("/api/auth/nguoi-dung", json={"username": "nhanvien1", "email": "nv1@test.local", "full_name": "Nhân Viên Một", "role": "NhanVien"}, headers=headers())
    assert r.status_code == 200 and r.json()["username"] == "nhanvien1", r.text
    uid = r.json()["id"]
    lg = client.post("/api/auth/login", json={"username": "nhanvien1"})
    assert lg.status_code == 200
    ds = client.get("/api/auth/nguoi-dung", headers=headers()).json()
    nv = [u for u in ds if u["id"] == uid][0]
    assert nv["last_login_at"] and nv["is_active"] is True
    assert "so_khach_phu_trach" in nv and "so_ban_be_phu_trach" in nv
    # Trùng username -> 400
    assert client.post("/api/auth/nguoi-dung", json={"username": "nhanvien1"}, headers=headers()).status_code == 400
    # Khóa tài khoản -> đăng nhập 403; mở lại -> đăng nhập được
    r2 = client.put(f"/api/auth/nguoi-dung/{uid}", json={"is_active": False}, headers=headers())
    assert r2.json()["is_active"] is False
    assert client.post("/api/auth/login", json={"username": "nhanvien1"}).status_code == 403
    client.put(f"/api/auth/nguoi-dung/{uid}", json={"is_active": True}, headers=headers())
    assert client.post("/api/auth/login", json={"username": "nhanvien1"}).status_code == 200


# ---- Mục 6: hàm chuẩn hoá định dạng Zalo ----
def test_42_dinh_dang_tin_zalo():
    from app.services.dinh_dang import dinh_dang_tin_zalo as f
    assert f("## Bảng giá dịch vụ") == "Bảng giá dịch vụ"
    assert f("# Xin chào") == "Xin chào"
    assert f("### Chi tiết gói") == "Chi tiết gói"
    assert f("Giá **500.000 đồng** một tháng") == "Giá 500.000 đồng một tháng"
    assert f("Giá *chỉ* áp dụng _hôm nay_") == "Giá chỉ áp dụng hôm nay"
    assert f("Xem [bảng giá](https://example.com/gia) tại đây") == "Xem bảng giá (https://example.com/gia) tại đây"
    assert f("- Mục một\n- Mục hai") == "• Mục một\n• Mục hai"
    assert f("* Mục sao") == "• Mục sao"
    bang = "| Dịch vụ | Giá |\n|---|---|\n| Gói A | 500.000 |\n| Gói B | 900.000 |"
    kq = f(bang)
    assert "|" not in kq and "Dịch vụ: Gói A" in kq and "Giá: 500.000" in kq and "Gói B" in kq
    assert f("Dùng lệnh `npm start` ngay") == "Dùng lệnh npm start ngay"
    assert "```" not in f("```python\nprint(1)\n```")
    assert f("") == "" and f(None) == ""


# ---- Mục 5: chia tin ----
def test_43_chia_tin_nhan_don_vi():
    from app.services.dinh_dang import chia_tin_nhan
    assert chia_tin_nhan("ngắn", 350) == ["ngắn"]
    dai = ("Câu thứ nhất để kiểm tra chia tin. Câu thứ hai cũng khá dài để kiểm tra. "
           "Câu thứ ba nối tiếp câu chuyện. Câu thứ tư kết thúc đoạn văn bản này.")
    phan = chia_tin_nhan(dai, 80)
    assert len(phan) >= 2 and all(len(p) <= 80 for p in phan)
    # Giữ thứ tự: ghép lại theo thứ tự vẫn chứa các câu theo đúng trình tự
    assert phan[0].startswith("Câu thứ nhất") and "thứ tư" in phan[-1]
    doan = "Đoạn một ngắn.\n\nĐoạn hai cũng ngắn."
    assert chia_tin_nhan(doan, 350) == [doan]
    # Một câu cực dài không có dấu câu -> cắt cứng vẫn không vượt giới hạn
    phan2 = chia_tin_nhan("từ " * 100, 50)
    assert all(len(p) <= 50 for p in phan2) and len(phan2) >= 4


def test_44_chia_tin_tich_hop_va_tat_thi_gui_mot_tin(monkeypatch):
    from app.services import orchestrator
    gui = []
    class FakePersonal:
        def send_text(self, thread_id, text):
            gui.append(text); return {"thanh_cong": True}
        def tha_tim(self, *a, **k): return {"thanh_cong": True}
    monkeypatch.setattr(orchestrator, "ZaloPersonalConnector", lambda: FakePersonal())
    # Quy tắc trả lời bằng một đoạn văn dài cố định cho từ khóa riêng
    van_dai = " ".join([f"Câu số {i} mô tả chi tiết dịch vụ rất đầy đủ cho khách hàng tham khảo." for i in range(1, 9)])
    r = client.post("/api/quy-tac", json={"name": "Chia tin test", "condition_type": "chua_tu_khoa",
                                          "condition_value": "kiem tra chia tin", "action_type": "tra_loi",
                                          "action_value": van_dai}, headers=headers())
    assert r.status_code == 200
    _dat_cai_dat(gui_tin_chia_nho=True, do_dai_toi_da_moi_tin=200, do_tre_giua_cac_tin_ms=0)
    r2 = client.post("/api/zalo/webhook/ca-nhan", json={
        "external_id": "wh-chia-1", "customer_external_id": "khach-chia-1",
        "customer_name": "Khách Chia Tin", "content": "cho em kiem tra chia tin với"})
    assert r2.status_code == 200 and r2.json()["tra_loi"]
    assert len(gui) >= 3 and all(len(p) <= 200 for p in gui)
    assert gui[0].startswith("Câu số 1") and "Câu số 8" in gui[-1]
    # Tắt chia nhỏ -> gửi đúng 1 tin đầy đủ
    gui.clear()
    _dat_cai_dat(gui_tin_chia_nho=False)
    r3 = client.post("/api/zalo/webhook/ca-nhan", json={
        "external_id": "wh-chia-2", "customer_external_id": "khach-chia-1",
        "customer_name": "Khách Chia Tin", "content": "kiem tra chia tin lần hai"})
    assert r3.status_code == 200 and len(gui) == 1 and "Câu số 8" in gui[0]
    _dat_cai_dat(gui_tin_chia_nho=True, do_dai_toi_da_moi_tin=350, do_tre_giua_cac_tin_ms=700)


# ---- Mục 7: logic nhóm Zalo ----
def _gui_nhom(mid, **kw):
    payload = {"external_id": mid, "customer_external_id": "nhom-test-1",
               "customer_name": "Thành viên nhóm", "content": kw.pop("content", "shop ơi cho hỏi giá với"),
               "la_nhom": True}
    payload.update(kw)
    return client.post("/api/zalo/webhook/ca-nhan", json=payload)


def test_45_logic_nhom_tag_dich_danh(monkeypatch):
    from app.services import orchestrator
    gui = []
    class FakePersonal:
        def send_text(self, thread_id, text):
            gui.append((thread_id, text)); return {"thanh_cong": True}
        def tha_tim(self, *a, **k): return {"thanh_cong": True}
        def status(self): return {"tai_khoan_id": "bot-uid-1"}
    monkeypatch.setattr(orchestrator, "ZaloPersonalConnector", lambda: FakePersonal())
    # Mention đúng UID của bot -> trả lời, gửi về thread nhóm
    r1 = _gui_nhom("grp-1", bot_uid="bot-uid-1", mentions=[{"uid": "bot-uid-1", "pos": 0, "len": 5}])
    assert r1.status_code == 200 and r1.json()["tra_loi"], r1.text
    assert gui and gui[0][0] == "nhom-test-1"
    # Mention @all (uid -1) -> im lặng, không gửi gì thêm
    gui.clear()
    r2 = _gui_nhom("grp-2", bot_uid="bot-uid-1", mentions=[{"uid": "-1", "pos": 0, "len": 4}], content="@all mọi người ơi giá sao")
    assert r2.json()["tra_loi"] is None and r2.json()["ly_do"] == "bo_qua_nhom_khong_tag" and gui == []
    # Không mention ai -> im lặng
    r3 = _gui_nhom("grp-3", bot_uid="bot-uid-1", mentions=[])
    assert r3.json()["tra_loi"] is None and r3.json()["ly_do"] == "bo_qua_nhom_khong_tag"
    # Mention người khác, không phải bot -> im lặng
    r4 = _gui_nhom("grp-4", bot_uid="bot-uid-1", mentions=[{"uid": "nguoi-khac", "pos": 0, "len": 5}])
    assert r4.json()["tra_loi"] is None
    # Tin 1-1 (không phải nhóm) -> hành vi không đổi, vẫn trả lời
    r5 = client.post("/api/zalo/webhook/ca-nhan", json={
        "external_id": "grp-5", "customer_external_id": "khach-11-1",
        "customer_name": "Khách 1-1", "content": "xin chào shop"})
    assert r5.json()["tra_loi"]
    # Tắt cài đặt "chỉ khi được tag" -> tin nhóm không tag cũng được trả lời
    _dat_cai_dat(bot_nhom_chi_khi_duoc_tag=False)
    r6 = _gui_nhom("grp-6", bot_uid="bot-uid-1", mentions=[], content="không tag ai cả")
    assert r6.json()["tra_loi"]
    _dat_cai_dat(bot_nhom_chi_khi_duoc_tag=True)


# ---- Mục 4: thả tim bật/tắt ----
def test_46_tha_tim_bat_tat(monkeypatch):
    from app.services import orchestrator
    tim = []
    class FakePersonal:
        def send_text(self, thread_id, text): return {"thanh_cong": True}
        def tha_tim(self, thread_id, message_id, loai_thread=0, cli_msg_id=""):
            tim.append((thread_id, message_id, loai_thread)); return {"thanh_cong": True}
    monkeypatch.setattr(orchestrator, "ZaloPersonalConnector", lambda: FakePersonal())
    _dat_cai_dat(bot_tha_tim=False)
    r1 = client.post("/api/zalo/webhook/ca-nhan", json={
        "external_id": "tim-1", "customer_external_id": "khach-tim-1",
        "customer_name": "Khách Tim", "content": "xin chào shop"})
    assert r1.json()["tra_loi"] and tim == []  # tắt -> không gọi reaction
    _dat_cai_dat(bot_tha_tim=True)
    r2 = client.post("/api/zalo/webhook/ca-nhan", json={
        "external_id": "tim-2", "customer_external_id": "khach-tim-1",
        "customer_name": "Khách Tim", "content": "shop còn mở cửa không"})
    assert r2.json()["tra_loi"]
    assert len(tim) == 1 and tim[0][0] == "khach-tim-1" and tim[0][1] == "tim-2" and tim[0][2] == 0
    _dat_cai_dat(bot_tha_tim=False)


# ---- Mục 9.1: bật/tắt provider ----
def test_47_bat_tat_provider():
    r = client.post("/api/ai-providers", json={"name": "Provider bat tat", "provider": "mock", "model": "m-bat-tat", "is_default": True}, headers=headers())
    pid = r.json()["id"]
    assert r.json()["is_default"] is True
    # Tắt provider ĐANG mặc định -> bị chặn 400, yêu cầu chọn mặc định khác
    r2 = client.patch(f"/api/ai-providers/{pid}/bat-tat", json={"is_active": False}, headers=headers())
    assert r2.status_code == 400 and "mặc định" in r2.json()["detail"]
    # Chọn provider khác làm mặc định, sau đó tắt được
    lst = client.get("/api/ai-providers", headers=headers()).json()
    khac = [p for p in lst if p["id"] != pid and p["provider"] == "mock"][0]
    client.put(f"/api/ai-providers/{khac['id']}", json={"is_default": True}, headers=headers())
    r3 = client.patch(f"/api/ai-providers/{pid}/bat-tat", json={"is_active": False}, headers=headers())
    assert r3.status_code == 200 and r3.json()["is_active"] is False
    # Provider đã tắt không được chọn làm mặc định khi sinh câu trả lời
    from app.database import SessionLocal
    from app.services.ai_gateway import get_default_provider
    db = SessionLocal()
    mac_dinh = get_default_provider(db)
    assert mac_dinh is not None and mac_dinh.id != pid and mac_dinh.is_active is True
    db.close()
    # Bật lại bình thường
    r4 = client.patch(f"/api/ai-providers/{pid}/bat-tat", json={"is_active": True}, headers=headers())
    assert r4.json()["is_active"] is True
    client.put(f"/api/ai-providers/{pid}", json={"is_default": False}, headers=headers())


# ---- Mục 9.2: lọc hội thoại đã/chưa nhắn ----
def test_48_loc_hoi_thoai_da_nhan_tin():
    from app.database import SessionLocal
    from app.models import Conversation
    kh = client.get("/api/khach-hang?tu_khoa=Lê Văn C", headers=headers()).json()[0]
    db = SessionLocal()
    conv_trong = Conversation(customer_id=kh["id"], channel="mo_phong", status="dang_xu_ly")
    db.add(conv_trong); db.commit(); cid_trong = conv_trong.id; db.close()
    ds_da = client.get("/api/hoi-thoai?loc_tin=da_nhan_tin", headers=headers()).json()
    assert all((c["message_count"] or 0) >= 1 for c in ds_da)
    assert all(c["id"] != cid_trong for c in ds_da)
    assert all("last_message" in c and "last_message_at" in c for c in ds_da)
    ds_chua = client.get("/api/hoi-thoai?loc_tin=chua_nhan_tin", headers=headers()).json()
    assert any(c["id"] == cid_trong for c in ds_chua)
    assert all((c["message_count"] or 0) == 0 for c in ds_chua)
    # Tất cả: sắp xếp theo hoạt động gần nhất — hội thoại có tin mới nhất không nằm cuối
    ds_all = client.get("/api/hoi-thoai", headers=headers()).json()
    assert len(ds_all) >= len(ds_da) + len(ds_chua) - 1


# ---- Mục 9.5: bạn bè Zalo + phân bổ admin ----
class _FakeBanBeConnector:
    du_lieu = [
        {"id": "ban-001", "ten_hien_thi": "Bạn Một", "avatar_url": "https://example.com/a1.png"},
        {"id": "ban-002", "ten_hien_thi": "Bạn Hai", "avatar_url": ""},
        {"id": "ban-003", "ten_hien_thi": "Bạn Ba", "avatar_url": ""},
    ]
    def danh_sach_ban_be(self):
        return [dict(b) for b in self.du_lieu]


def test_49_dong_bo_ban_be_upsert_giu_phan_bo(monkeypatch):
    from app.routers import ban_be as ban_be_router
    monkeypatch.setattr(ban_be_router, "ZaloPersonalConnector", lambda: _FakeBanBeConnector())
    r = client.post("/api/ban-be-zalo/dong-bo", headers=headers())
    assert r.status_code == 200 and r.json()["moi"] == 3 and r.json()["tong_trong_he_thong"] >= 3, r.text
    ds = client.get("/api/ban-be-zalo", headers=headers()).json()
    assert len(ds) == 3 and ds[0]["admin_user_id"] is None
    # Gán admin (user "admin") cho ban-001
    admin = [u for u in client.get("/api/auth/nguoi-dung", headers=headers()).json() if u["username"] == "admin"][0]
    b1 = [b for b in ds if b["zalo_friend_id"] == "ban-001"][0]
    r2 = client.put(f"/api/ban-be-zalo/{b1['id']}/phan-bo", json={"admin_user_id": admin["id"], "ghi_chu": "Khách VIP"}, headers=headers())
    assert r2.json()["admin_user_id"] == admin["id"] and r2.json()["admin_username"] == "admin"
    # Đồng bộ lại với tên bạn đã đổi ở phía Zalo -> phân bổ + ghi chú được giữ, tên cập nhật
    _FakeBanBeConnector.du_lieu[0]["ten_hien_thi"] = "Bạn Một (đổi tên)"
    r3 = client.post("/api/ban-be-zalo/dong-bo", headers=headers())
    assert r3.json()["moi"] == 0 and r3.json()["cap_nhat"] == 3
    b1_moi = [b for b in client.get("/api/ban-be-zalo", headers=headers()).json() if b["zalo_friend_id"] == "ban-001"][0]
    assert b1_moi["ten_hien_thi"] == "Bạn Một (đổi tên)" and b1_moi["admin_user_id"] == admin["id"] and b1_moi["ghi_chu"] == "Khách VIP"
    # Lọc theo trạng thái + thống kê
    chua = client.get("/api/ban-be-zalo?admin_id=chua_phan_bo", headers=headers()).json()
    assert len(chua) == 2
    tk = client.get("/api/ban-be-zalo/thong-ke", headers=headers()).json()
    assert tk["tong_ban"] == 3 and tk["chua_phan_bo"] == 2 and tk["da_phan_bo"] == 1
    theo = {t["username"]: t["so_ban"] for t in tk["theo_admin"]}
    assert theo["admin"] == 1


def test_50_gan_admin_hang_loat_va_ban_nhan_tin():
    admin = [u for u in client.get("/api/auth/nguoi-dung", headers=headers()).json() if u["username"] == "admin"][0]
    ds = client.get("/api/ban-be-zalo?admin_id=chua_phan_bo", headers=headers()).json()
    ids = [b["id"] for b in ds]
    r = client.put("/api/ban-be-zalo/phan-bo-hang-loat", json={"ids": ids, "admin_user_id": admin["id"]}, headers=headers())
    assert r.status_code == 200 and r.json()["da_cap_nhat"] == 2
    # ban-002 nhắn tin tới -> khách + hội thoại được gắn admin phụ trách "admin"
    r2 = client.post("/api/zalo/mock/nhan-tin-nhan", json={
        "external_id": "msg-ban-002", "customer_external_id": "ban-002",
        "customer_name": "Bạn Hai", "content": "Chào shop, mình là bạn hai"}, headers=headers())
    assert r2.status_code == 200, r2.text
    kh = [c for c in client.get("/api/khach-hang", headers=headers()).json() if c["external_id"] == "ban-002"][0]
    assert kh["assignee"] == "admin"
    convs = client.get("/api/hoi-thoai", headers=headers()).json()
    conv = [c for c in convs if c["customer_id"] == kh["id"]][0]
    assert conv["assignee"] == "admin"
    # Bỏ phân bổ hàng loạt (admin_user_id = null)
    r3 = client.put("/api/ban-be-zalo/phan-bo-hang-loat", json={"ids": ids, "admin_user_id": None}, headers=headers())
    assert r3.json()["da_cap_nhat"] == 2 and r3.json()["admin_user_id"] is None


# ---- Mục 10: AI hội thoại tự nhiên (lịch sử + temperature + max_tokens + prompt theo cài đặt) ----
def test_51_ai_payload_co_lich_su_temperature_max_tokens(monkeypatch):
    import json as _json
    import httpx as _httpx
    from app.services import ai_gateway
    from app.database import SessionLocal
    from app.models import AIProviderConfig
    lst = client.get("/api/ai-providers", headers=headers()).json()
    pid = [p for p in lst if p["name"] == "Provider stream test"][0]["id"]
    captured = {}
    class FakeResp:
        status_code = 200; headers = {"content-type": "application/json"}
        text = _json.dumps({"model": "m-that", "choices": [{"message": {"content": "Dạ em đây ạ"}}], "usage": {"prompt_tokens": 10, "completion_tokens": 3}})
    class FakeClient:
        def __init__(self, timeout=None, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, url, headers=None, json=None):
            captured.update(json or {}); return FakeResp()
    orig = _httpx.Client
    _httpx.Client = FakeClient
    try:
        db = SessionLocal(); prov = db.get(AIProviderConfig, pid)
        cai_dat_test = {
            "bot_ten_hien_thi": "An Nhiên", "bot_cach_xung_ho": "em/bạn",
            "bot_giong_dieu": "ngan_gon_thang_than", "ai_do_dai_tra_loi": "ngan",
            "ai_temperature": 0.7, "prompt_bo_sung": "Luôn nhắc khách về chương trình tri ân tháng này.",
            "doanh_nghiep_ten": "Công ty Kiểm Thử ABC",
        }
        lich_su = [
            {"role": "user", "content": "LỊCH SỬ: khách hỏi lần một"},
            {"role": "assistant", "content": "LỊCH SỬ: bot trả lời lần một"},
        ]
        chunks = [{"document_id": 1, "title": "T", "content": "NGU_CANH_DAC_TRUNG_XYZ: giá 123.456", "score": 9}]
        text, model = ai_gateway.generate_reply(db, prov, "Câu hỏi hiện tại của khách", chunks, [],
                                                lich_su=lich_su, cai_dat=cai_dat_test)
        assert text == "Dạ em đây ạ"
        msgs = captured["messages"]
        # System chứa: tên bot theo cài đặt, giọng điệu đã chọn, luật chống motip,
        # hướng dẫn bổ sung, thông tin doanh nghiệp và NGỮ CẢNH TRI THỨC
        he_thong = msgs[0]["content"]
        assert msgs[0]["role"] == "system"
        assert "An Nhiên" in he_thong and "ngắn gọn, thẳng thắn" in he_thong.lower()
        assert "không chào lại" in he_thong and "Luật trò chuyện tự nhiên" in he_thong
        assert "chương trình tri ân" in he_thong and "Công ty Kiểm Thử ABC" in he_thong
        assert "NGU_CANH_DAC_TRUNG_XYZ" in he_thong
        # Lịch sử nằm giữa system và câu hỏi, đúng thứ tự; câu hỏi KHÔNG bị dán ngữ cảnh
        assert msgs[1] == {"role": "user", "content": "LỊCH SỬ: khách hỏi lần một"}
        assert msgs[2] == {"role": "assistant", "content": "LỊCH SỬ: bot trả lời lần một"}
        assert msgs[-1] == {"role": "user", "content": "Câu hỏi hiện tại của khách"}
        # temperature từ cài đặt + max_tokens từ cấu hình provider
        assert captured["temperature"] == 0.7
        assert captured["max_tokens"] == prov.max_tokens and captured["max_tokens"] > 0
        db.close()
    finally:
        _httpx.Client = orig


def test_52_doi_giong_dieu_trong_cai_dat_doi_prompt():
    from app.services.ai_gateway import tao_system_prompt, HUONG_DAN_GIONG_DIEU
    p1 = tao_system_prompt({"bot_giong_dieu": "tu_nhien_than_thien"})
    p2 = tao_system_prompt({"bot_giong_dieu": "lich_su_trang_trong"})
    assert HUONG_DAN_GIONG_DIEU["tu_nhien_than_thien"].split(":")[1][:20] in p1
    assert HUONG_DAN_GIONG_DIEU["lich_su_trang_trong"].split(":")[1][:20] in p2
    assert p1 != p2
    # Đổi qua API cài đặt -> doc_cai_dat thấy ngay (runtime, không restart)
    _dat_cai_dat(bot_giong_dieu="lich_su_trang_trong", ai_temperature=1.2)
    from app.database import SessionLocal
    from app.routers.cai_dat import doc_cai_dat
    db = SessionLocal(); cd = doc_cai_dat(db); db.close()
    assert cd["bot_giong_dieu"] == "lich_su_trang_trong" and cd["ai_temperature"] == 1.2
    p3 = tao_system_prompt(cd)
    assert HUONG_DAN_GIONG_DIEU["lich_su_trang_trong"].split(":")[1][:20] in p3
    client.post("/api/cai-dat/khoi-phuc-mac-dinh", json={"nhom": "phong_cach"}, headers=headers())
    db = SessionLocal(); cd2 = doc_cai_dat(db); db.close()
    assert cd2["bot_giong_dieu"] == "tu_nhien_than_thien" and cd2["ai_temperature"] == 0.85


def test_53_mock_da_bien_the_luan_phien():
    from app.services.ai_gateway import MockAIProvider
    tra_loi = {MockAIProvider().generate("câu hỏi lạ không có ngữ cảnh", [], []) for _ in range(6)}
    assert len(tra_loi) >= 2  # luân phiên nhiều biến thể, không một motip


# ---- Mục 11.2: registry cài đặt + hiệu lực runtime ----
def test_54_registry_day_du_va_khoi_phuc_mac_dinh():
    r = client.get("/api/cai-dat/dang-ky", headers=headers())
    assert r.status_code == 200
    d = r.json()
    nhom = {n["khoa_nhom"] for n in d["nhom"]}
    assert {"hanh_vi_bot", "phong_cach", "thu_thap", "thong_bao", "nhom_gui_tin", "he_thong", "doanh_nghiep"} <= nhom
    theo_khoa = {c["khoa"]: c for c in d["cai_dat"]}
    for khoa in ["bot_tha_tim", "gui_tin_chia_nho", "do_tre_giua_cac_tin_ms", "do_dai_toi_da_moi_tin",
                 "thong_bao_cua_so_chong_trung_phut", "thong_bao_gian_cach_gui_zalo_giay",
                 "ai_temperature", "bot_giong_dieu", "so_tin_nhan_ngu_canh", "mau_chu_dao_giao_dien"]:
        assert khoa in theo_khoa, khoa
        assert theo_khoa[khoa]["kieu"] in ("bool", "so", "text", "textarea", "select", "mau", "gio")
        assert "nhan" in theo_khoa[khoa] and "gia_tri" in theo_khoa[khoa] and "mac_dinh" in theo_khoa[khoa]
    assert theo_khoa["bot_tha_tim"]["kieu"] == "bool" and theo_khoa["bot_tha_tim"]["mac_dinh"] is False
    assert theo_khoa["ai_temperature"]["mac_dinh"] == 0.85
    assert theo_khoa["mau_chu_dao_giao_dien"]["kieu"] == "mau"
    # Giá trị sai ràng buộc bị từ chối
    assert client.put("/api/cai-dat", json={"ai_temperature": 9}, headers=headers()).status_code == 400
    assert client.put("/api/cai-dat", json={"bot_giong_dieu": "giong_la"}, headers=headers()).status_code == 400
    # Khôi phục mặc định theo nhóm: đặt thử rồi khôi phục nhóm nhom_gui_tin
    _dat_cai_dat(do_tre_giua_cac_tin_ms=1234)
    client.post("/api/cai-dat/khoi-phuc-mac-dinh", json={"nhom": "nhom_gui_tin"}, headers=headers())
    cd = client.get("/api/cai-dat", headers=headers()).json()
    assert cd["do_tre_giua_cac_tin_ms"] == 700 and cd["gui_tin_chia_nho"] is True


def test_55_cai_dat_co_hieu_luc_ngay_tu_khoa_cam():
    # Đổi 1 cài đặt qua API -> hành vi đổi ngay ở request kế tiếp (không restart)
    _dat_cai_dat(tu_khoa_cam="tu-cam-kiem-thu")
    r = client.post("/api/zalo/mock/nhan-tin-nhan", json={
        "external_id": "msg-cam-1", "customer_external_id": "khach-cam-1",
        "customer_name": "Khách Cấm", "content": "tin này chứa tu-cam-kiem-thu ở giữa"}, headers=headers())
    assert r.json()["tra_loi"] is None and r.json()["ly_do"] == "chua_tu_khoa_cam"
    _dat_cai_dat(tu_khoa_cam="")
    r2 = client.post("/api/zalo/mock/nhan-tin-nhan", json={
        "external_id": "msg-cam-2", "customer_external_id": "khach-cam-1",
        "customer_name": "Khách Cấm", "content": "tin bình thường không chứa từ cấm"}, headers=headers())
    assert r2.json()["tra_loi"]
