"""Kiểm thử đợt bổ sung 23/10/2026 (3 phạm vi LAM dặn):

1) Bot gửi sticker sau câu trả lời (kênh cá nhân) — công tắc + xác suất +
   danh sách JSON; lỗi/chặn thì chỉ ghi log, không hỏng câu trả lời.
2) Tốc độ trả lời + hiện "đang soạn tin": hàm tinh_do_tre thuần (clamp/hệ số),
   chế độ ngay -> không typing; tự nhiên -> typing đúng 1 lần TRƯỚC send_text.
3) Ảnh khách không lưu lâu: don_dep_anh_cu theo mtime + hạn cấu hình,
   API /api/tep/thong-ke (đăng nhập) và /api/tep/don-dep (chỉ admin).

Không phụ thuộc Zalo thật: connector cá nhân được thay bằng FakePersonal
ghi lại thứ tự cuộc gọi (theo đúng pattern các file test trước).
Chạy SAU test_mvp / test_nang_cap_2 / test_nang_cap_3 / test_tinh_nang_moi.
"""
import json
import os
import time

from test_mvp import client, headers


def _dat_cai_dat(**kw):
    r = client.put("/api/cai-dat", json=kw, headers=headers())
    assert r.status_code == 200, r.text
    return r.json()


def _khoi_phuc_mac_dinh_gui_tin():
    _dat_cai_dat(bot_gui_sticker=False, xac_suat_gui_sticker=20, danh_sach_sticker="",
                 che_do_toc_do_tra_loi="tu_nhien", toc_do_go_ms_moi_ky_tu=30,
                 do_tre_tra_loi_toi_thieu_ms=800, do_tre_tra_loi_toi_da_ms=6000,
                 do_tre_giua_cac_tin_ms=700, so_ngay_luu_anh_khach=7)


def _tao_quy_tac(tu_khoa, cau_tra_loi):
    r = client.post("/api/quy-tac", json={
        "name": f"Quy tắc test {tu_khoa}", "condition_type": "chua_tu_khoa",
        "condition_value": tu_khoa, "action_type": "tra_loi",
        "action_value": cau_tra_loi}, headers=headers())
    assert r.status_code == 200, r.text
    return r.json()


def _webhook_ca_nhan(ext_id, khach_id, noi_dung):
    r = client.post("/api/zalo/webhook/ca-nhan", json={
        "external_id": ext_id, "customer_external_id": khach_id,
        "customer_name": "Khách Test Đợt Mới", "content": noi_dung})
    assert r.status_code == 200, r.text
    return r.json()


class _FakePersonal:
    """Connector cá nhân giả: ghi THỨ TỰ cuộc gọi để kiểm chứng typing/sticker."""

    def __init__(self, ghi):
        self.ghi = ghi

    def send_text(self, thread_id, text, loai_thread=0):
        self.ghi.append(("send_text", thread_id, text))
        return {"thanh_cong": True}

    def typing(self, thread_id, loai_thread=0):
        self.ghi.append(("typing", thread_id, loai_thread))
        return {"thanh_cong": True}

    def tha_tim(self, *a, **k):
        self.ghi.append(("tha_tim",))
        return {"thanh_cong": True}

    def send_sticker(self, thread_id, sticker, loai_thread=0):
        self.ghi.append(("send_sticker", thread_id, sticker, loai_thread))
        return {"thanh_cong": True}


def _lap_fake(monkeypatch, ghi):
    from app.services import orchestrator
    monkeypatch.setattr(orchestrator, "ZaloPersonalConnector", lambda: _FakePersonal(ghi))


# ---- Phạm vi 2a: hàm tinh_do_tre thuần ----
def test_83_tinh_do_tre_clamp_va_he_so():
    from app.services.orchestrator import tinh_do_tre
    cd = {"che_do_toc_do_tra_loi": "tu_nhien", "toc_do_go_ms_moi_ky_tu": 30,
          "do_tre_tra_loi_toi_thieu_ms": 800, "do_tre_tra_loi_toi_da_ms": 6000}
    # Chế độ ngay -> luôn 0
    assert tinh_do_tre("câu trả lời dài thế nào cũng vậy", {**cd, "che_do_toc_do_tra_loi": "ngay"}) == 0
    # Tự nhiên: 100 ký tự * 30ms = 3000 (trong khoảng) -> đúng 3000
    assert tinh_do_tre("x" * 100, cd) == 3000
    # Ngắn -> kẹp ở sàn 800
    assert tinh_do_tre("ngắn", cd) == 800
    # Rất dài -> kẹp ở trần 6000
    assert tinh_do_tre("x" * 1000, cd) == 6000
    # Chậm: hệ số 2 -> 100 ký tự * 30 * 2 = 6000; 50 ký tự -> 3000
    cd_cham = {**cd, "che_do_toc_do_tra_loi": "cham"}
    assert tinh_do_tre("x" * 50, cd_cham) == 3000
    assert tinh_do_tre("x" * 100, cd_cham) == 6000
    # Thiếu khóa -> dùng mặc định (tu_nhien, 30ms, 800..6000)
    assert tinh_do_tre("x" * 100, {}) == 3000
    # max < min (cấu hình lệch) -> không âm/không lỗi, trả về mức sàn
    assert tinh_do_tre("x" * 10, {"toc_do_go_ms_moi_ky_tu": 0,
                                   "do_tre_tra_loi_toi_thieu_ms": 500,
                                   "do_tre_tra_loi_toi_da_ms": 100}) == 500


# ---- Phạm vi 2b: typing đúng thứ tự + chế độ ngay không typing ----
def test_84_typing_truoc_send_text_va_che_do_ngay(monkeypatch):
    ghi = []
    _lap_fake(monkeypatch, ghi)
    _tao_quy_tac("kiem tra toc do", "Dạ em đây ạ")
    # Tự nhiên, độ trễ ép 0 để test chạy nhanh (vẫn phải có typing)
    _dat_cai_dat(che_do_toc_do_tra_loi="tu_nhien", toc_do_go_ms_moi_ky_tu=0,
                 do_tre_tra_loi_toi_thieu_ms=0, do_tre_giua_cac_tin_ms=0,
                 bot_gui_sticker=False, bot_tha_tim=False)
    kq = _webhook_ca_nhan("wh-tocdo-1", "khach-tocdo-1", "cho em kiem tra toc do với")
    assert kq["tra_loi"]
    ten_goi = [g[0] for g in ghi]
    assert ten_goi == ["typing", "send_text"], ghi  # đúng 1 typing, TRƯỚC send_text
    # Chế độ ngay: không typing, gửi thẳng
    ghi.clear()
    _dat_cai_dat(che_do_toc_do_tra_loi="ngay")
    kq2 = _webhook_ca_nhan("wh-tocdo-2", "khach-tocdo-2", "cho em kiem tra toc do nữa")
    assert kq2["tra_loi"]
    assert [g[0] for g in ghi] == ["send_text"], ghi
    _khoi_phuc_mac_dinh_gui_tin()


# ---- Phạm vi 1a: sticker được gửi sau câu trả lời + có Message sticker ----
def test_85_sticker_gui_sau_tra_loi(monkeypatch):
    ghi = []
    _lap_fake(monkeypatch, ghi)
    _tao_quy_tac("kiem tra sticker", "Dạ vâng ạ")
    _dat_cai_dat(che_do_toc_do_tra_loi="ngay", bot_tha_tim=False,
                 bot_gui_sticker=True, xac_suat_gui_sticker=100,
                 danh_sach_sticker=json.dumps(
                     [{"id": 111, "cate_id": 22, "type": 1, "nhan": "Vui"}]))
    kq = _webhook_ca_nhan("wh-stk-1", "khach-stk-1", "cho em kiem tra sticker với")
    assert kq["tra_loi"]
    ten_goi = [g[0] for g in ghi]
    assert ten_goi == ["send_text", "send_sticker"], ghi  # sticker đi SAU văn bản
    _, thread_id, sticker, loai_thread = [g for g in ghi if g[0] == "send_sticker"][0]
    assert thread_id == "khach-stk-1" and loai_thread == 0
    assert sticker["id"] == 111 and sticker["cate_id"] == 22 and sticker["type"] == 1
    # Có Message row sticker để UI hiển thị
    ct = client.get(f"/api/hoi-thoai/{kq['conversation_id']}", headers=headers()).json()
    tin_stk = [m for m in ct["messages"] if m.get("attachment_type") == "sticker"]
    assert len(tin_stk) == 1 and tin_stk[0]["content"] == "[sticker]"
    assert json.loads(tin_stk[0]["attachment_url"])["id"] == 111
    _khoi_phuc_mac_dinh_gui_tin()


# ---- Phạm vi 1b: tắt / xác suất 0 / JSON hỏng -> không gửi, không sập ----
def test_86_sticker_khong_gui_khi_tat_hoac_json_hong(monkeypatch):
    ghi = []
    _lap_fake(monkeypatch, ghi)
    _tao_quy_tac("kiem tra sticker tat", "Dạ rồi ạ")
    ds_json = json.dumps([{"id": 111, "cate_id": 22, "type": 1}])
    # (a) Tắt công tắc dù xác suất 100 + có danh sách
    _dat_cai_dat(che_do_toc_do_tra_loi="ngay", bot_tha_tim=False,
                 bot_gui_sticker=False, xac_suat_gui_sticker=100, danh_sach_sticker=ds_json)
    _webhook_ca_nhan("wh-stk-2", "khach-stk-2", "kiem tra sticker tat lần một")
    assert not [g for g in ghi if g[0] == "send_sticker"], ghi
    # (b) Bật nhưng xác suất 0
    ghi.clear()
    _dat_cai_dat(bot_gui_sticker=True, xac_suat_gui_sticker=0)
    _webhook_ca_nhan("wh-stk-3", "khach-stk-3", "kiem tra sticker tat lần hai")
    assert not [g for g in ghi if g[0] == "send_sticker"], ghi
    # (c) JSON hỏng ghi thẳng vào DB (bỏ qua validation khi lưu) -> webhook
    # vẫn trả lời bình thường, bỏ qua sticker, không sập.
    ghi.clear()
    from app.database import SessionLocal
    from app.models import SystemSetting
    db = SessionLocal()
    try:
        dong = db.get(SystemSetting, "danh_sach_sticker")
        gia_tri_cu = dong.value if dong else None
        if dong:
            dong.value = "{json hong ne"
        else:
            db.add(SystemSetting(key="danh_sach_sticker", value="{json hong ne"))
        db.commit()
    finally:
        db.close()
    try:
        kq = _webhook_ca_nhan("wh-stk-4", "khach-stk-4", "kiem tra sticker tat lần ba")
        assert kq["tra_loi"]
        assert not [g for g in ghi if g[0] == "send_sticker"], ghi
        ct = client.get(f"/api/hoi-thoai/{kq['conversation_id']}", headers=headers()).json()
        assert not [m for m in ct["messages"] if m.get("attachment_type") == "sticker"]
    finally:
        db = SessionLocal()
        try:
            dong = db.get(SystemSetting, "danh_sach_sticker")
            if dong:
                if gia_tri_cu is None:
                    db.delete(dong)
                else:
                    dong.value = gia_tri_cu
                db.commit()
        finally:
            db.close()
    _khoi_phuc_mac_dinh_gui_tin()


# ---- Phạm vi 1+2: hợp đồng connector -> sidecar (payload đúng spec) ----
def test_87_connector_sticker_va_typing_dung_payload(monkeypatch):
    from app.services.zalo_connector import ZaloPersonalConnector
    bat = []
    conn = ZaloPersonalConnector()

    def _call_gia(method, path, json_data=None):
        bat.append((method, path, json_data))
        return 200, {"thanh_cong": True}

    monkeypatch.setattr(conn, "_call", _call_gia)
    conn.send_sticker("khach-1", {"id": 5, "cate_id": 6, "type": 1}, 1)
    method, path, payload = bat[-1]
    assert method == "POST" and path == "/gui-sticker"
    assert payload == {"thread_id": "khach-1", "loai_thread": 1,
                       "sticker": {"id": 5, "cate_id": 6, "type": 1}}
    conn.typing("khach-1", 0)
    method, path, payload = bat[-1]
    assert path == "/dang-soan" and payload["thread_id"] == "khach-1" and payload["bat"] is True


# ---- Registry: danh_sach_sticker validate JSON ngay khi lưu ----
def test_88_registry_chan_json_sticker_hong():
    r = client.put("/api/cai-dat", json={"danh_sach_sticker": "khong phai json"},
                   headers=headers())
    assert r.status_code == 400, r.text
    r = client.put("/api/cai-dat", json={"danh_sach_sticker": json.dumps([{"nhan": "thieu id"}])},
                   headers=headers())
    assert r.status_code == 400, r.text
    r = client.put("/api/cai-dat", json={
        "danh_sach_sticker": json.dumps([{"id": 1, "cate_id": 2, "type": 1}])},
        headers=headers())
    assert r.status_code == 200, r.text
    _dat_cai_dat(danh_sach_sticker="")


# ---- Phạm vi 3: dọn ảnh cũ theo hạn lưu + API thống kê/dọn dẹp ----
def test_89_don_dep_anh_cu_va_api():
    from app.services import anh_service
    _dat_cai_dat(so_ngay_luu_anh_khach=7)
    thu_muc = anh_service.THU_MUC_UPLOADS
    os.makedirs(thu_muc, exist_ok=True)
    duong_cu = os.path.join(thu_muc, "test-dondep-cu.jpg")
    duong_moi = os.path.join(thu_muc, "test-dondep-moi.jpg")
    with open(duong_cu, "wb") as f:
        f.write(b"x" * 2048)
    with open(duong_moi, "wb") as f:
        f.write(b"y" * 1024)
    cu = time.time() - 10 * 86400  # 10 ngày trước > hạn 7 ngày
    os.utime(duong_cu, (cu, cu))
    try:
        # Thống kê (phải đăng nhập)
        assert client.get("/api/tep/thong-ke").status_code == 401
        tk = client.get("/api/tep/thong-ke", headers=headers())
        assert tk.status_code == 200, tk.text
        assert tk.json()["so_anh"] >= 2 and tk.json()["so_ngay_luu"] == 7
        # Dọn dẹp: chưa đăng nhập -> 401; nhân viên thường -> 403
        assert client.post("/api/tep/don-dep").status_code == 401
        r_nv = client.post("/api/auth/nguoi-dung", json={
            "username": "nv_dondep", "email": "nv_dondep@test.local",
            "full_name": "NV Dọn Dẹp", "role": "NhanVien",
            "password": "NvDonDep@123"}, headers=headers())
        assert r_nv.status_code == 200, r_nv.text
        lg = client.post("/api/auth/login", json={"username": "nv_dondep",
                                                   "password": "NvDonDep@123"})
        assert lg.status_code == 200, lg.text
        h_nv = {"Authorization": f"Bearer {lg.json()['access_token']}"}
        assert client.post("/api/tep/don-dep", headers=h_nv).status_code == 403
        # Admin dọn ngay: file cũ bị xóa, file mới còn nguyên
        kq = client.post("/api/tep/don-dep", headers=headers())
        assert kq.status_code == 200, kq.text
        assert kq.json()["da_xoa"] >= 1 and kq.json()["giai_phong_mb"] > 0
        assert not os.path.exists(duong_cu)
        assert os.path.exists(duong_moi)
        # Hàm service chạy lại lần 2: không còn gì để xóa trong 2 file test
        kq2 = anh_service.don_dep_anh_cu(None, 7)
        assert kq2["da_xoa"] == 0
        # File đã bị dọn -> API tệp trả 404 (UI hiện "Ảnh đã hết hạn lưu trữ")
        assert client.get("/api/tep/test-dondep-cu.jpg", headers=headers()).status_code == 404
    finally:
        for d in (duong_cu, duong_moi):
            if os.path.exists(d):
                os.remove(d)
    _khoi_phuc_mac_dinh_gui_tin()
