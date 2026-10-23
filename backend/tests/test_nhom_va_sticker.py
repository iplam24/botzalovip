"""Kiểm thử đợt D + E (23/10/2026):

D — Lỗi bot không rep được trong NHÓM Zalo: _send_reply trước đây gọi
send_text mà không truyền loại thread, sidecar mặc định ThreadType.User
nên tin gửi vào nhóm "bốc hơi" dù DB ghi da_gui. Nay connector nhận
loai_thread (nhóm = 1, 1-1 = 0) và _send_reply truyền xuống từ tin khách.
Kèm quyết định của chủ hệ thống: BỎ cổng danh_sach_nhom_duoc_phep (tag
đúng = rep mọi nhóm), thay bằng danh_sach_nhom_bi_chan.

E — Lọt chữ "[sticker]" vào tin văn bản: sticker bot gửi được lưu thành
Message content="[sticker]" rồi bị nạp vào lịch sử cho AI -> AI bắt
chước viết "[sticker]" vào câu trả lời. Nay: (1) lịch sử loại hẳn tin
sticker; (2) dinh_dang_tin_zalo cắt token "[sticker]" khỏi văn bản AI.

Mọi test tự chụp + khôi phục các khóa cài đặt mình đụng vào để không ảnh
hưởng các file test chạy sau.
"""
import json

from test_mvp import client, headers

_KHOA_DUNG = ("che_do_toc_do_tra_loi", "bot_nhom_chi_khi_duoc_tag",
              "danh_sach_nhom_bi_chan", "danh_sach_nhom_duoc_phep",
              "thu_thap_tu_hoi_sdt", "bot_gui_sticker", "xac_suat_gui_sticker",
              "danh_sach_sticker", "che_do_tro_chuyen_tu_do", "tin_chao_khach_moi")


def _dat_cai_dat(**kw):
    r = client.put("/api/cai-dat", json=kw, headers=headers())
    assert r.status_code == 200, r.text
    return r.json()


def _chup_cai_dat():
    cd = client.get("/api/cai-dat", headers=headers()).json()
    return {k: cd.get(k) for k in _KHOA_DUNG}


def _phuc_hoi(chup):
    _dat_cai_dat(**{k: v for k, v in chup.items() if v is not None})


class _FakePersonal:
    """Connector cá nhân giả: ghi lại mọi cuộc gọi kèm loai_thread."""

    def __init__(self, ghi):
        self.ghi = ghi

    def send_text(self, thread_id, text, loai_thread=0):
        self.ghi.append(("send_text", str(thread_id), text, loai_thread))
        return {"thanh_cong": True}

    def typing(self, thread_id, loai_thread=0):
        self.ghi.append(("typing", str(thread_id), loai_thread))
        return {"thanh_cong": True}

    def tha_tim(self, *a, **k):
        return {"thanh_cong": True}

    def send_sticker(self, thread_id, sticker, loai_thread=0):
        self.ghi.append(("send_sticker", str(thread_id), sticker, loai_thread))
        return {"thanh_cong": True}

    def status(self):
        return {"tai_khoan_id": "bot-uid-de"}


def _lap_fake(monkeypatch, ghi):
    from app.services import orchestrator
    monkeypatch.setattr(orchestrator, "ZaloPersonalConnector", lambda: _FakePersonal(ghi))


def _gui_nhom(mid, nhom_id, **kw):
    payload = {"external_id": mid, "customer_external_id": nhom_id,
               "customer_name": "Thành viên nhóm D",
               "content": kw.pop("content", "shop ơi cho hỏi giá với"),
               "la_nhom": True, "bot_uid": "bot-uid-de",
               "mentions": [{"uid": "bot-uid-de", "pos": 0, "len": 9}]}
    payload.update(kw)
    return client.post("/api/zalo/webhook/ca-nhan", json=payload)


def _gui_1_1(mid, khach_id, noi_dung):
    return client.post("/api/zalo/webhook/ca-nhan", json={
        "external_id": mid, "customer_external_id": khach_id,
        "customer_name": "Khách Test DE", "content": noi_dung})


def _conv_va_tin_bot(external_id):
    from app.database import SessionLocal
    from app.models import Conversation, Customer, Message
    db = SessionLocal()
    try:
        cust = db.query(Customer).filter(Customer.external_id == external_id).first()
        assert cust is not None, f"Không thấy khách {external_id}"
        conv = (db.query(Conversation).filter(Conversation.customer_id == cust.id)
                .order_by(Conversation.id.desc()).first())
        tin_bot = (db.query(Message)
                   .filter(Message.conversation_id == conv.id, Message.sender_type == "bot")
                   .order_by(Message.id).all())
        return conv.id, [(m.content, m.status, getattr(m, "attachment_type", "") or "") for m in tin_bot]
    finally:
        db.close()


def _cac_lan_gui(ghi):
    return [g for g in ghi if g[0] == "send_text"]


# ---- D(a): rep trong nhóm phải gửi với thread_type = Group (1) ----
def test_90_rep_nhom_gui_dung_loai_thread_group(monkeypatch):
    _lap_fake(monkeypatch, ghi := [])
    chup = _chup_cai_dat()
    _dat_cai_dat(che_do_toc_do_tra_loi="ngay", bot_nhom_chi_khi_duoc_tag=True,
                 danh_sach_nhom_bi_chan="", bot_gui_sticker=False)
    try:
        r = _gui_nhom("de-grp-1", "nhom-de-1")
        assert r.status_code == 200 and r.json()["tra_loi"], r.text
        gui = _cac_lan_gui(ghi)
        assert gui, ghi
        # Đích = ID nhóm và MỌI phần tin đều mang loai_thread = 1 (Group)
        assert all(g[1] == "nhom-de-1" and g[3] == 1 for g in gui), gui
        # Tin bot trong DB của hội thoại nhóm ở trạng thái da_gui
        _, tin_bot = _conv_va_tin_bot("nhom-de-1")
        assert tin_bot and all(t[1] == "da_gui" for t in tin_bot), tin_bot
    finally:
        _phuc_hoi(chup)


# ---- D(b): nhóm trong danh sách chặn -> tag đúng cũng không rep ----
def test_91_nhom_bi_chan_tag_dung_cung_khong_rep(monkeypatch):
    _lap_fake(monkeypatch, ghi := [])
    chup = _chup_cai_dat()
    _dat_cai_dat(che_do_toc_do_tra_loi="ngay", bot_nhom_chi_khi_duoc_tag=True,
                 danh_sach_nhom_bi_chan="nhom-de-bi-chan")
    try:
        r = _gui_nhom("de-grp-2", "nhom-de-bi-chan")
        j = r.json()
        assert j["tra_loi"] is None and j["ly_do"] == "bo_qua_nhom_khong_tag", j
        assert _cac_lan_gui(ghi) == []
    finally:
        _phuc_hoi(chup)


# ---- D(c): bỏ cổng allowlist — nhóm ngoài danh sách cho phép vẫn rep ----
def test_92_bo_cong_danh_sach_nhom_duoc_phep(monkeypatch):
    _lap_fake(monkeypatch, ghi := [])
    chup = _chup_cai_dat()
    # Allowlist cũ chỉ chứa một nhóm KHÁC: theo logic cũ nhóm này bị chặn,
    # theo quyết định mới (đợt D) khóa này không còn tác dụng.
    _dat_cai_dat(che_do_toc_do_tra_loi="ngay", bot_nhom_chi_khi_duoc_tag=True,
                 danh_sach_nhom_duoc_phep="nhom-hoan-toan-khac",
                 danh_sach_nhom_bi_chan="", bot_gui_sticker=False)
    try:
        r = _gui_nhom("de-grp-3", "nhom-de-2")
        assert r.status_code == 200 and r.json()["tra_loi"], r.text
        gui = _cac_lan_gui(ghi)
        assert gui and all(g[1] == "nhom-de-2" and g[3] == 1 for g in gui), gui
    finally:
        _phuc_hoi(chup)


# ---- D(d): chat 1-1 vẫn gửi với loai_thread = 0 (User) ----
def test_93_chat_1_1_loai_thread_0(monkeypatch):
    _lap_fake(monkeypatch, ghi := [])
    chup = _chup_cai_dat()
    _dat_cai_dat(che_do_toc_do_tra_loi="ngay", bot_gui_sticker=False)
    try:
        r = _gui_1_1("de-11-1", "khach-de-11", "xin chào shop, tư vấn em với")
        assert r.status_code == 200 and r.json()["tra_loi"], r.text
        gui = _cac_lan_gui(ghi)
        assert gui and all(g[1] == "khach-de-11" and g[3] == 0 for g in gui), gui
    finally:
        _phuc_hoi(chup)


# ---- D: Mock connector ghi nhận loai_thread (hợp đồng D1) ----
def test_94_mock_connector_ghi_loai_thread():
    from app.services.zalo_connector import MockZaloConnector, ZaloPersonalConnector
    import inspect
    mock = MockZaloConnector()
    mock.send_text("thread-nhom", "chào nhóm", 1)
    mock.send_text("thread-user", "chào bạn")
    assert mock.sent == [("thread-nhom", "chào nhóm", 1), ("thread-user", "chào bạn", 0)]
    # Chữ ký connector thật có tham số loai_thread mặc định 0
    tham_so = inspect.signature(ZaloPersonalConnector.send_text).parameters
    assert "loai_thread" in tham_so and tham_so["loai_thread"].default == 0


# ---- E(a): lịch sử đưa cho AI không chứa tin sticker ----
def test_95_lich_su_khong_nap_tin_sticker(monkeypatch):
    from app.services import ai_gateway
    _lap_fake(monkeypatch, ghi := [])
    chup = _chup_cai_dat()
    _dat_cai_dat(che_do_toc_do_tra_loi="ngay", bot_gui_sticker=False,
                 thu_thap_tu_hoi_sdt=False, che_do_tro_chuyen_tu_do=False)
    bat = {}

    def gen_gia(db, provider, question, chunks, memories, **kw):
        bat["lich_su"] = kw.get("lich_su") or []
        return "Câu trả lời lượt một", "mock-test"

    monkeypatch.setattr(ai_gateway, "generate_reply", gen_gia)
    try:
        r1 = _gui_1_1("de-ls-1", "khach-de-ls", "chào shop, em hỏi câu đầu tiên")
        assert r1.status_code == 200 and r1.json()["tra_loi"], r1.text
        conv_id, _ = _conv_va_tin_bot("khach-de-ls")
        # Chèn trực tiếp: 1 tin sticker đúng chuẩn mới (có attachment_type),
        # 1 tin bot "[sticker]" kiểu dữ liệu cũ (không attachment_type),
        # 1 tin bot thường để đối chứng.
        from app.database import SessionLocal
        from app.models import Message
        db = SessionLocal()
        try:
            db.add(Message(conversation_id=conv_id, sender_type="bot", content="[sticker]",
                           status="da_gui", attachment_type="sticker",
                           attachment_url=json.dumps({"id": 1, "cate_id": 2, "type": 1})))
            db.add(Message(conversation_id=conv_id, sender_type="bot", content="[sticker]",
                           status="da_gui"))
            db.add(Message(conversation_id=conv_id, sender_type="bot",
                           content="Câu bot thường để đối chứng", status="da_gui"))
            db.commit()
        finally:
            db.close()
        r2 = _gui_1_1("de-ls-2", "khach-de-ls", "em hỏi tiếp câu thứ hai")
        assert r2.status_code == 200 and r2.json()["tra_loi"], r2.text
        noi_dung_ls = [m["content"] for m in bat["lich_su"]]
        assert noi_dung_ls, "Lịch sử bắt được rỗng — test chưa chạm generate_reply"
        assert all((c or "").strip() != "[sticker]" for c in noi_dung_ls), noi_dung_ls
        assert "Câu bot thường để đối chứng" in noi_dung_ls, noi_dung_ls
        assert any("câu đầu tiên" in (c or "") for c in noi_dung_ls), noi_dung_ls
    finally:
        _phuc_hoi(chup)


# ---- E(b): marker "[sticker]" trong văn bản AI bị cắt trước khi gửi/lưu ----
def test_96_loc_marker_sticker_khoi_cau_tra_loi(monkeypatch):
    from app.services.dinh_dang import dinh_dang_tin_zalo
    # Đơn vị: các dạng lọt marker
    assert dinh_dang_tin_zalo("abc def\n[sticker]") == "abc def"
    assert dinh_dang_tin_zalo("[sticker]") == ""
    assert dinh_dang_tin_zalo("abc [sticker]") == "abc"
    assert dinh_dang_tin_zalo("abc [sticker] def") == "abc def"
    assert dinh_dang_tin_zalo("dòng một\n[sticker]\ndòng hai") == "dòng một\ndòng hai"
    assert dinh_dang_tin_zalo("câu trả lời bình thường") == "câu trả lời bình thường"
    # Tích hợp: AI giả trả câu có marker -> gửi đi + lưu DB đều sạch
    from app.services import ai_gateway
    _lap_fake(monkeypatch, ghi := [])
    chup = _chup_cai_dat()
    _dat_cai_dat(che_do_toc_do_tra_loi="ngay", bot_gui_sticker=False,
                 thu_thap_tu_hoi_sdt=False, che_do_tro_chuyen_tu_do=False)
    monkeypatch.setattr(ai_gateway, "generate_reply",
                        lambda db, provider, question, chunks, memories, **kw: ("abc def\n[sticker]", "mock-test"))
    try:
        r = _gui_1_1("de-loc-1", "khach-de-loc", "cho em hỏi câu lọc marker")
        assert r.status_code == 200 and r.json()["tra_loi"] == "abc def", r.text
        gui = _cac_lan_gui(ghi)
        assert [g[2] for g in gui] == ["abc def"], gui
        _, tin_bot = _conv_va_tin_bot("khach-de-loc")
        assert [t[0] for t in tin_bot] == ["abc def"], tin_bot
    finally:
        _phuc_hoi(chup)


# ---- E(c): đường gửi sticker THẬT không đổi (vẫn lưu Message sticker) ----
def test_97_duong_gui_sticker_that_khong_doi(monkeypatch):
    _lap_fake(monkeypatch, ghi := [])
    chup = _chup_cai_dat()
    _dat_cai_dat(che_do_toc_do_tra_loi="ngay", bot_gui_sticker=True,
                 xac_suat_gui_sticker=100,
                 danh_sach_sticker=json.dumps([{"id": 111, "cate_id": 222, "type": 1, "nhan": "Test DE"}]),
                 thu_thap_tu_hoi_sdt=False, che_do_tro_chuyen_tu_do=False)
    try:
        r = _gui_1_1("de-stk-1", "khach-de-stk", "chào shop, em hỏi về sticker")
        assert r.status_code == 200 and r.json()["tra_loi"], r.text
        gui_sticker = [g for g in ghi if g[0] == "send_sticker"]
        assert len(gui_sticker) == 1 and gui_sticker[0][1] == "khach-de-stk", ghi
        assert gui_sticker[0][2].get("id") == 111 and gui_sticker[0][3] == 0, gui_sticker
        _, tin_bot = _conv_va_tin_bot("khach-de-stk")
        sticker_luu = [t for t in tin_bot if t[2] == "sticker"]
        assert len(sticker_luu) == 1 and sticker_luu[0][0] == "[sticker]" and sticker_luu[0][1] == "da_gui", tin_bot
    finally:
        _phuc_hoi(chup)
