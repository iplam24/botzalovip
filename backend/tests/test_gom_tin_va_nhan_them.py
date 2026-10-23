"""Kiểm thử đợt bổ sung 23/10/2026 — nhắn như người thật (LAM yêu cầu):

A) Chia tin TỰ NHIÊN theo ngưỡng mềm do_dai_muc_tieu_moi_tin: reply dưới
   ngưỡng cứng vẫn tách thành nhiều bong bóng theo câu; muc_tieu=0 giữ
   nguyên hành vi cũ.
B) GOM tin khách gửi liên tiếp ở chat 1-1: tiep_nhan_tin_den đệm payload,
   xu_ly_hang_gom xả 1 lượt — connector chỉ nhận ĐÚNG 1 lượt trả lời, cả
   hai tin khách đều được lưu. Gom tắt -> xử lý từng tin như cũ.
C) Bot TỰ NHẮN THÊM (follow-up): sau 1 lượt rep, thuc_hien_tin_nhan_them
   gửi thêm đúng 1 tin; AI trả [BO_QUA] / khách đã nhắn mới / nhân viên
   tiếp quản -> không gửi; tin nhắn thêm không tự sinh follow-up tiếp.

Không phụ thuộc Zalo/AI thật: connector cá nhân thay bằng Fake ghi lại
cuộc gọi, ai_gateway.generate_reply thay bằng hàm giả, bộ lên lịch
_len_lich_tin_nhan_them thay bằng bản ghi lại (test gọi thuc_hien_*
đồng bộ, không chờ Timer thật, không để suite chậm thêm).
File này chạy TRƯỚC các file test cũ (thứ tự alphabet) nên test cuối
khôi phục toàn bộ cài đặt đã đụng về mặc định.
"""
from test_mvp import client, headers


def _dat_cai_dat(**kw):
    r = client.put("/api/cai-dat", json=kw, headers=headers())
    assert r.status_code == 200, r.text
    return r.json()


def _cai_dat_nen():
    """Nền chung cho các test đợt này: gửi ngay không độ trễ, không sticker/tim."""
    _dat_cai_dat(che_do_toc_do_tra_loi="ngay", do_tre_giua_cac_tin_ms=0,
                 bot_gui_sticker=False, bot_tha_tim=False,
                 che_do_duyet_truoc_khi_gui=False)


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
        "customer_name": "Khách Test Gom Tin", "content": noi_dung})
    assert r.status_code == 200, r.text
    return r.json()


class _FakePersonal:
    """Connector cá nhân giả: ghi lại mọi cuộc gọi (kèm thread đích)."""

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


def _cac_tin_gui(ghi, thread_id=None):
    return [g for g in ghi if g[0] == "send_text" and (thread_id is None or g[1] == thread_id)]


def _hoi_thoai_cua(khach_external_id):
    from app.database import SessionLocal
    from app.models import Customer, Conversation
    db = SessionLocal()
    try:
        cust = db.query(Customer).filter(Customer.external_id == khach_external_id).first()
        assert cust is not None, f"Không thấy khách {khach_external_id}"
        conv = (db.query(Conversation).filter(Conversation.customer_id == cust.id)
                .order_by(Conversation.id.desc()).first())
        return cust.id, conv.id
    finally:
        db.close()


# ---- PHẦN A1: hàm chia_tin_nhan thuần với ngưỡng mềm ----
def test_90_chia_tin_nhan_theo_muc_tieu():
    from app.services.dinh_dang import chia_tin_nhan
    c1 = "Cau mot " + "a" * 52 + "."
    c2 = "Cau hai " + "b" * 52 + "."
    c3 = "Cau ba " + "c" * 53 + "."
    van = c1 + " " + c2 + " " + c3  # 185 ký tự, 3 câu x 61 ký tự
    assert len(van) == 185
    # muc_tieu=120: hai câu bất kỳ gộp lại = 123 > 120 -> 3 bong bóng riêng
    phan = chia_tin_nhan(van, 350, 120)
    assert phan == [c1, c2, c3], phan
    assert all(len(p) <= 350 for p in phan)
    # muc_tieu=0: hành vi cũ 100% — dưới ngưỡng cứng thì đúng 1 phần nguyên văn
    assert chia_tin_nhan(van, 350, 0) == [van]
    assert chia_tin_nhan(van, 350) == [van]
    # 1 câu dài hơn ngưỡng mềm (250) nhưng dưới ngưỡng cứng -> giữ nguyên 1 bong bóng
    cau_dai = "y" * 249 + "."
    assert chia_tin_nhan(cau_dai, 350, 120) == [cau_dai]
    # Vượt ngưỡng cứng: vẫn cắt cứng, không phần nào quá 350 ở cả hai chế độ
    for mt in (0, 120):
        phan_cung = chia_tin_nhan("z" * 500, 350, mt)
        assert len(phan_cung) >= 2 and all(len(p) <= 350 for p in phan_cung), (mt, phan_cung)


# ---- PHẦN A2: tích hợp — _send_reply dùng ngưỡng mềm từ Cài đặt ----
def test_91_send_reply_chia_tu_nhien_qua_webhook(monkeypatch):
    ghi = []
    _lap_fake(monkeypatch, ghi)
    _cai_dat_nen()
    _dat_cai_dat(gui_tin_chia_nho=True, do_dai_toi_da_moi_tin=350,
                 do_dai_muc_tieu_moi_tin=120, gom_tin_lien_tiep=False,
                 bot_tu_nhan_them=False)
    cau = lambda n, k: f"Câu số {n} " + k * 55 + "."  # mỗi câu 65 ký tự
    van = cau(1, "a") + " " + cau(2, "b") + " " + cau(3, "c")  # 197 ký tự < 350
    _tao_quy_tac("kiem tra muc tieu", van)
    kq = _webhook_ca_nhan("wh-muctieu-1", "khach-muctieu-1", "cho em kiem tra muc tieu với")
    assert kq["tra_loi"]
    gui = _cac_tin_gui(ghi, "khach-muctieu-1")
    # Trước đợt này reply 197 ký tự chỉ là 1 tin; nay tách thành 3 bong bóng
    assert len(gui) == 3, gui
    assert "Câu số 1" in gui[0][2] and "Câu số 3" in gui[-1][2]
    assert all(len(g[2]) <= 350 for g in gui)


# ---- PHẦN B1: gom 2 tin liên tiếp -> đúng 1 lượt trả lời ----
def test_92_gom_tin_hai_tin_mot_luot(monkeypatch):
    ghi = []
    _lap_fake(monkeypatch, ghi)
    _cai_dat_nen()
    _dat_cai_dat(gom_tin_lien_tiep=True, thoi_gian_gom_tin_giay=0,
                 bot_tu_nhan_them=False)
    _tao_quy_tac("gom tin mot luot", "Dạ em đã nhận đủ hai ý của anh rồi ạ.")
    from app.database import SessionLocal
    from app.services.orchestrator import tiep_nhan_tin_den, xu_ly_hang_gom
    db = SessionLocal()
    try:
        r1 = tiep_nhan_tin_den(db, "gom-001", "khach-gom-001", "Khách Gom",
                               "shop ơi cho em hỏi giá với", channel="ca_nhan")
        r2 = tiep_nhan_tin_den(db, "gom-002", "khach-gom-001", "Khách Gom",
                               "gom tin mot luot giúp em nhé", channel="ca_nhan")
    finally:
        db.close()
    assert r1["ly_do"] == "dang_gom_tin" and r2["ly_do"] == "dang_gom_tin"
    assert _cac_tin_gui(ghi) == []  # chưa xả -> chưa gửi gì cả
    kq = xu_ly_hang_gom("khach-gom-001")
    assert kq and kq["tra_loi"], kq
    gui = _cac_tin_gui(ghi, "khach-gom-001")
    assert len(gui) == 1, gui  # ĐÚNG 1 lượt gửi, không phải 2
    # Cả hai tin khách đều có trong DB
    from app.models import Message, Conversation
    _, conv_id = _hoi_thoai_cua("khach-gom-001")
    db = SessionLocal()
    try:
        tin_khach = (db.query(Message).filter(Message.conversation_id == conv_id,
                                              Message.sender_type == "khach")
                     .order_by(Message.id).all())
        assert [m.external_id for m in tin_khach] == ["gom-001", "gom-002"], tin_khach
        tin_bot = db.query(Message).filter(Message.conversation_id == conv_id,
                                           Message.sender_type == "bot",
                                           Message.status == "da_gui").all()
        assert len(tin_bot) == 1
    finally:
        db.close()


# ---- PHẦN B2: gom tắt -> xử lý từng tin như cũ ----
def test_93_gom_tat_thi_tra_loi_tung_tin(monkeypatch):
    ghi = []
    _lap_fake(monkeypatch, ghi)
    _cai_dat_nen()
    _dat_cai_dat(gom_tin_lien_tiep=False, bot_tu_nhan_them=False)
    _tao_quy_tac("gom tat thi tach", "Dạ em rep từng tin đây ạ.")
    from app.database import SessionLocal
    from app.services.orchestrator import tiep_nhan_tin_den
    db = SessionLocal()
    try:
        tiep_nhan_tin_den(db, "gom-tat-001", "khach-gom-002", "Khách Gom Tắt",
                          "gom tat thi tach tin một", channel="ca_nhan")
        tiep_nhan_tin_den(db, "gom-tat-002", "khach-gom-002", "Khách Gom Tắt",
                          "gom tat thi tach tin hai", channel="ca_nhan")
    finally:
        db.close()
    gui = _cac_tin_gui(ghi, "khach-gom-002")
    assert len(gui) == 2, gui  # mỗi tin 1 lượt trả lời như hành vi cũ


# ---- PHẦN C: hạ tầng giả cho follow-up ----
def _lap_ai_gia(monkeypatch, cau_phu):
    from app.services import ai_gateway

    def fake_generate(db, provider, question, chunks, memories, **kw):
        if "nhắn thêm" in (question or ""):
            return cau_phu, "fake-model"
        return "Dạ em trả lời chính đây ạ.", "fake-model"

    monkeypatch.setattr(ai_gateway, "generate_reply", fake_generate)


def _lap_ghi_lich(monkeypatch):
    from app.services import orchestrator
    lich = []
    monkeypatch.setattr(orchestrator, "_len_lich_tin_nhan_them",
                        lambda db, conv, cd, tin_bot_id, trace="": lich.append((conv.id, tin_bot_id)))
    return lich


def _mot_luot_rep(monkeypatch, ghi, khach_id, ext_id):
    """Cho khách nhắn 1 tin qua webhook (AI giả rep), trả (conv_id, tin_bot_id)
    từ bản ghi lịch follow-up."""
    lich = _lap_ghi_lich(monkeypatch)
    _webhook_ca_nhan(ext_id, khach_id, "shop ơi tư vấn em với")
    gui = _cac_tin_gui(ghi, khach_id)
    assert len(gui) == 1, gui  # lượt chính gửi đúng 1 tin
    assert len(lich) == 1 and lich[0][1], lich  # đã lên lịch follow-up đúng 1 lần
    return lich[0]


# ---- PHẦN C1: follow-up gửi đúng 1 tin, không đệ quy, không gửi lần 2 ----
def test_94_nhan_them_gui_dung_mot_tin(monkeypatch):
    ghi = []
    _lap_fake(monkeypatch, ghi)
    _cai_dat_nen()
    _dat_cai_dat(gom_tin_lien_tiep=False, bot_tu_nhan_them=True)
    cau_phu = "À mà anh nhớ giữ lại hóa đơn để được bảo hành đầy đủ nhé."
    _lap_ai_gia(monkeypatch, cau_phu)
    from app.services.orchestrator import thuc_hien_tin_nhan_them
    conv_id, tin_bot_id = _mot_luot_rep(monkeypatch, ghi, "khach-nt-001", "nt-001")
    lich_sau_luot_chinh = 1
    kq = thuc_hien_tin_nhan_them(conv_id, tin_bot_id)
    assert kq["gui"] is True, kq
    gui = _cac_tin_gui(ghi, "khach-nt-001")
    assert len(gui) == 2 and gui[-1][2] == cau_phu, gui
    # Gọi lại lần nữa với cùng lượt bot -> đã có tin thêm rồi -> hủy, không gửi thêm
    kq2 = thuc_hien_tin_nhan_them(conv_id, tin_bot_id)
    assert kq2["gui"] is False and kq2["ly_do"] == "da_co_tin_nhan_them", kq2
    assert len(_cac_tin_gui(ghi, "khach-nt-001")) == 2
    assert lich_sau_luot_chinh == 1  # tin nhắn thêm KHÔNG tự lên lịch follow-up tiếp
    from app.database import SessionLocal
    from app.models import Message
    db = SessionLocal()
    try:
        tin_bot = (db.query(Message).filter(Message.conversation_id == conv_id,
                                            Message.sender_type == "bot",
                                            Message.status == "da_gui")
                   .order_by(Message.id).all())
        assert len(tin_bot) == 2 and tin_bot[-1].content == cau_phu
    finally:
        db.close()


# ---- PHẦN C2: các điều kiện hủy — [BO_QUA] / khách nhắn mới / tiếp quản ----
def test_95_nhan_them_cac_dieu_kien_huy(monkeypatch):
    ghi = []
    _lap_fake(monkeypatch, ghi)
    _cai_dat_nen()
    _dat_cai_dat(gom_tin_lien_tiep=False, bot_tu_nhan_them=True)
    from app.database import SessionLocal
    from app.models import Message, Conversation
    from app.services.orchestrator import thuc_hien_tin_nhan_them

    # (a) AI trả [BO_QUA] -> không gửi
    _lap_ai_gia(monkeypatch, "[BO_QUA]")
    conv_id, tin_bot_id = _mot_luot_rep(monkeypatch, ghi, "khach-nt-002", "nt-002")
    kq = thuc_hien_tin_nhan_them(conv_id, tin_bot_id)
    assert kq["gui"] is False and kq["ly_do"] == "ai_bo_qua", kq
    assert len(_cac_tin_gui(ghi, "khach-nt-002")) == 1

    # (b) Khách đã nhắn tin MỚI trước giờ cháy -> không gửi
    _lap_ai_gia(monkeypatch, "À em bổ sung thêm ý này nữa ạ.")
    conv_id, tin_bot_id = _mot_luot_rep(monkeypatch, ghi, "khach-nt-003", "nt-003")
    db = SessionLocal()
    try:
        db.add(Message(conversation_id=conv_id, external_id="nt-003b",
                       sender_type="khach", content="em nhắn thêm nè", status="da_nhan"))
        db.commit()
    finally:
        db.close()
    kq = thuc_hien_tin_nhan_them(conv_id, tin_bot_id)
    assert kq["gui"] is False and kq["ly_do"] == "khach_da_nhan_tin_moi", kq
    assert len(_cac_tin_gui(ghi, "khach-nt-003")) == 1

    # (c) Nhân viên đã tiếp quản hội thoại -> không gửi
    conv_id, tin_bot_id = _mot_luot_rep(monkeypatch, ghi, "khach-nt-004", "nt-004")
    db = SessionLocal()
    try:
        conv = db.get(Conversation, conv_id)
        conv.human_takeover = True
        db.commit()
    finally:
        db.close()
    kq = thuc_hien_tin_nhan_them(conv_id, tin_bot_id)
    assert kq["gui"] is False and kq["ly_do"] == "nhan_vien_tiep_quan_hoac_bot_tam_dung", kq
    assert len(_cac_tin_gui(ghi, "khach-nt-004")) == 1


# ---- Dọn dẹp: khôi phục cài đặt cho các file test chạy sau ----
def test_96_khoi_phuc_cai_dat():
    _dat_cai_dat(gom_tin_lien_tiep=True, thoi_gian_gom_tin_giay=5,
                 tin_nhan_them_sau_giay_min=30, tin_nhan_them_sau_giay_max=90,
                 do_dai_muc_tieu_moi_tin=120, gui_tin_chia_nho=True,
                 do_dai_toi_da_moi_tin=350, che_do_toc_do_tra_loi="tu_nhien",
                 toc_do_go_ms_moi_ky_tu=30, do_tre_tra_loi_toi_thieu_ms=800,
                 do_tre_tra_loi_toi_da_ms=6000, do_tre_giua_cac_tin_ms=700,
                 bot_gui_sticker=False, bot_tha_tim=False,
                 che_do_duyet_truoc_khi_gui=False,
                 # LƯU Ý SUITE: để bot_tu_nhan_them=False trong DB test.
                 # Mặc định registry vẫn là BẬT (True) cho vận hành thật;
                 # ở đây tắt để các Timer nền của tính năng này không bắn
                 # tin follow-up vào Fake connector của các test cũ chạy
                 # sau (tránh nhiễu chéo giữa các test trong cùng suite).
                 bot_tu_nhan_them=False)
