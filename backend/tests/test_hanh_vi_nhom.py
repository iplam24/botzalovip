"""Kiểm thử đợt HÀNH VI NHÓM (23/10/2026) — F1 + F2 + F3.

F1 — Cổng chống rep VỚ VẨN trong nhóm: lượt nhóm truyền luat_nhom cho AI;
AI trả đúng "[BO_QUA]" (tin tag chỉ để chửi/bả/spam) thì orchestrator im
lặng hẳn (không gửi, không sticker), ly_do="bo_qua_nhom_vo_van". Chat 1-1
KHÔNG áp chốt này.

F2 — Ngữ cảnh nhóm RIÊNG, chỉ nhớ cốt lõi: lượt nhóm bỏ qua trích xuất
thông tin cá nhân + thông báo lead + hỏi SĐT; tóm tắt bộ nhớ nhóm dùng
chỉ dẫn cốt lõi cấp nhóm; _send_reply không remember() sự kiện cho nhóm;
lịch sử nhóm ghi nhãn tên người nói (cột messages.sender_name mới).

F3 — Bộ lọc CHỐNG LẶP CÂU xác thực: reply AI (provider thật, kênh cá
nhân) trùng/gần trùng với 20 câu bot đã gửi gần nhất toàn hệ thống thì
sinh lại 1 lần; vẫn trùng -> nhóm bỏ qua (ly_do="bo_qua_trung_cau"),
1-1 vẫn gửi kèm log cảnh báo module "chong_lap_cau".

Mọi test tự chụp + khôi phục cài đặt và provider mặc định mình đụng vào.
"""
import json

from test_mvp import client, headers

_KHOA_DUNG = ("che_do_tro_chuyen_tu_do", "che_do_toc_do_tra_loi", "bot_gui_sticker",
              "bot_nhom_chi_khi_duoc_tag", "danh_sach_nhom_bi_chan", "gom_tin_lien_tiep",
              "bot_tu_nhan_them", "thu_thap_tu_hoi_sdt", "thu_thap_intent_hoi_sdt",
              "thu_thap_tu_khoa_hoi_sdt", "tin_chao_khach_moi",
              "bo_nho_tom_tat_sau_bao_nhieu_tin", "module_thu_thap_thong_tin",
              "nhom_chong_rep_vo_van")

BOT_UID = "bot-uid-hv"


def _dat_cai_dat(**kw):
    r = client.put("/api/cai-dat", json=kw, headers=headers())
    assert r.status_code == 200, r.text
    return r.json()


def _chup_cai_dat():
    cd = client.get("/api/cai-dat", headers=headers()).json()
    return {k: cd.get(k) for k in _KHOA_DUNG}


def _phuc_hoi(chup):
    _dat_cai_dat(**{k: v for k, v in chup.items() if v is not None})


def _cai_dat_nen():
    """Cài đặt nền xác định cho các test của file này (gửi ngay, không
    sticker, không gom, không nhắn thêm, không chế độ tự do)."""
    _dat_cai_dat(che_do_toc_do_tra_loi="ngay", bot_gui_sticker=False,
                 bot_nhom_chi_khi_duoc_tag=True, danh_sach_nhom_bi_chan="",
                 gom_tin_lien_tiep=False, bot_tu_nhan_them=False,
                 che_do_tro_chuyen_tu_do=False, tin_chao_khach_moi="")


class _FakePersonal:
    """Connector cá nhân giả: ghi lại mọi lần gửi kèm loai_thread."""

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
        return {"tai_khoan_id": BOT_UID}


def _lap_fake(monkeypatch, ghi):
    from app.services import orchestrator
    monkeypatch.setattr(orchestrator, "ZaloPersonalConnector", lambda: _FakePersonal(ghi))


def _lap_ai_kich_ban(monkeypatch, cac_cau, bat=None):
    """Thay ai_gateway.generate_reply bằng bản giả theo kịch bản: lần gọi
    thứ i trả cac_cau[i] (hết kịch bản thì lặp câu cuối). bat (dict) nếu
    truyền vào sẽ nhận {"so_lan": n, "kwargs": kwargs của lần gọi cuối}."""
    from app.services import ai_gateway
    trang_thai = {"n": 0}

    def fake(db, provider, question, chunks, memories, **kw):
        i = min(trang_thai["n"], len(cac_cau) - 1)
        trang_thai["n"] += 1
        if bat is not None:
            bat.update({"so_lan": trang_thai["n"], "kwargs": kw, "question": question})
        return cac_cau[i], "model-gia-hv"

    monkeypatch.setattr(ai_gateway, "generate_reply", fake)
    return trang_thai


def _gui_nhom(mid, nhom_id, ten_nguoi_gui, content, tag=True):
    payload = {"external_id": mid, "customer_external_id": nhom_id,
               "customer_name": ten_nguoi_gui, "content": content,
               "la_nhom": True, "bot_uid": BOT_UID,
               "mentions": [{"uid": BOT_UID, "pos": 0, "len": 9}] if tag else []}
    return client.post("/api/zalo/webhook/ca-nhan", json=payload)


def _gui_1_1(mid, khach_id, noi_dung):
    return client.post("/api/zalo/webhook/ca-nhan", json={
        "external_id": mid, "customer_external_id": khach_id,
        "customer_name": "Khách HV", "content": noi_dung})


def _cac_lan_gui(ghi):
    return [g for g in ghi if g[0] == "send_text"]


def _db():
    from app.database import SessionLocal
    return SessionLocal()


def _khach(external_id):
    from app.models import Customer
    db = _db()
    try:
        return db.query(Customer).filter(Customer.external_id == external_id).first()
    finally:
        db.close()


def _co_log(module, doan):
    from app.models import SystemLog
    db = _db()
    try:
        return db.query(SystemLog).filter(
            SystemLog.module == module, SystemLog.message.like(f"%{doan}%")).first() is not None
    finally:
        db.close()


def _dat_provider_mac_dinh_theo_ten(ten):
    ds = client.get("/api/ai-providers", headers=headers()).json()
    p = [x for x in ds if x["name"] == ten][0]
    r = client.put(f"/api/ai-providers/{p['id']}", json={"is_default": True}, headers=headers())
    assert r.status_code == 200, r.text
    return p["id"]


# ================= F1 — cổng chống rep vớ vẩn trong nhóm =================

def test_98_f1_nhom_ai_bo_qua_thi_bot_im_lang(monkeypatch):
    _lap_fake(monkeypatch, ghi := [])
    bat = {}
    _lap_ai_kich_ban(monkeypatch, ["[BO_QUA]"], bat)
    chup = _chup_cai_dat(); _cai_dat_nen()
    _dat_cai_dat(nhom_chong_rep_vo_van=True)  # cổng là tùy chọn — test này bật cổng
    try:
        r = _gui_nhom("hv-f1-1", "nhom-hv-f1", "Huy", "@Quỳnh Hoa cc ngu")
        j = r.json()
        assert r.status_code == 200, r.text
        assert j["tra_loi"] is None and j["ly_do"] == "bo_qua_nhom_vo_van", j
        assert _cac_lan_gui(ghi) == [], ghi  # không gửi tin nào
        assert not [g for g in ghi if g[0] == "send_sticker"], ghi  # không sticker
        assert bat["kwargs"].get("luat_nhom") is True  # lượt nhóm có truyền luật nhóm
        assert _co_log("orchestrator", "bo_qua_nhom_vo_van conv=")
    finally:
        _phuc_hoi(chup)


def test_99_f1_nhom_ai_tra_loi_thuong_thi_van_rep(monkeypatch):
    _lap_fake(monkeypatch, ghi := [])
    _lap_ai_kich_ban(monkeypatch, ["Chào bạn, nhóm mình cần hỗ trợ gì vậy ạ?"])
    chup = _chup_cai_dat(); _cai_dat_nen()
    try:
        r = _gui_nhom("hv-f1-2", "nhom-hv-f1", "Lan", "@Quỳnh Hoa cho mình hỏi lịch sinh hoạt nhóm")
        j = r.json()
        assert j["tra_loi"] and "hỗ trợ" in j["tra_loi"], j
        gui = _cac_lan_gui(ghi)
        assert gui and all(g[3] == 1 for g in gui), gui  # gửi vào nhóm (loai_thread=1)
    finally:
        _phuc_hoi(chup)


def test_100_f1_chat_1_1_khong_ap_chot_bo_qua(monkeypatch):
    _lap_fake(monkeypatch, ghi := [])
    bat = {}
    _lap_ai_kich_ban(monkeypatch, ["[BO_QUA]"], bat)
    chup = _chup_cai_dat(); _cai_dat_nen()
    try:
        r = _gui_1_1("hv-f1-3", "khach-hv-f1", "alo shop")
        j = r.json()
        # 1-1 KHÔNG áp chốt: [BO_QUA] được xử như hiện tại (gửi nguyên văn)
        assert j["tra_loi"] == "[BO_QUA]", j
        assert bat["kwargs"].get("luat_nhom") is False
        gui = _cac_lan_gui(ghi)
        assert gui and gui[0][3] == 0, gui
    finally:
        _phuc_hoi(chup)


def test_115_f1_cong_tat_mac_dinh_tag_chui_van_rep(monkeypatch):
    """Chốt của LAM 23/10/2026: cổng chống vớ vẩn trong nhóm MẶC ĐỊNH TẮT —
    tag chửi trong nhóm vẫn được rep như thường, luật nhóm không được truyền."""
    _lap_fake(monkeypatch, ghi := [])
    bat = {}
    _lap_ai_kich_ban(monkeypatch, ["Ê chửi gì chửi, vào đây nói chuyện đàng hoàng nè =))"], bat)
    chup = _chup_cai_dat(); _cai_dat_nen()
    _dat_cai_dat(nhom_chong_rep_vo_van=False)  # chốt mới: cổng TẮT
    try:
        r = _gui_nhom("hv-f1-4", "nhom-hv-f1", "Huy", "@Quỳnh Hoa con chó")
        j = r.json()
        assert r.status_code == 200, r.text
        assert j["tra_loi"] and "đàng hoàng" in j["tra_loi"], j
        assert bat["kwargs"].get("luat_nhom") is False  # cổng tắt → không truyền luật nhóm
        gui = _cac_lan_gui(ghi)
        assert gui and all(g[3] == 1 for g in gui), gui  # vẫn gửi vào nhóm
    finally:
        _phuc_hoi(chup)


# ================= F2 — ngữ cảnh nhóm riêng, chỉ nhớ cốt lõi =================

def test_101_f2_nhom_khong_thu_thap_khong_bao_lead(monkeypatch):
    _lap_fake(monkeypatch, ghi := [])
    _lap_ai_kich_ban(monkeypatch, ["Dạ em chào nhóm mình ạ, cần gì cứ hỏi em nhé."])
    chup = _chup_cai_dat(); _cai_dat_nen()
    _dat_cai_dat(module_thu_thap_thong_tin=True)
    try:
        r = _gui_nhom("hv-f2-1", "nhom-hv-f2", "Huy",
                      "@Quỳnh Hoa ơi số của mình là 0901234567, hỏi giá dịch vụ với")
        assert r.json()["tra_loi"], r.text
        from app.models import CollectedInfo, MemoryItem, Notification
        khach_nhom = _khach("nhom-hv-f2")
        assert khach_nhom is not None
        assert not (khach_nhom.phone or "").strip(), khach_nhom.phone  # không thu SĐT từ nhóm
        db = _db()
        try:
            thu_thap = db.query(CollectedInfo).filter(CollectedInfo.customer_id == khach_nhom.id).all()
            assert thu_thap == [], [(t.field, t.value) for t in thu_thap]
            bao_lead = (db.query(Notification)
                        .filter(Notification.type.in_(("khach_moi", "co_so_dien_thoai", "du_thong_tin")))
                        .all())
            # Không có thông báo lead nào trỏ về khách nhóm này
            from app.models import Conversation
            conv_nhom = (db.query(Conversation).filter(Conversation.customer_id == khach_nhom.id)
                         .order_by(Conversation.id.desc()).first())
            bao_cua_nhom = [b for b in bao_lead if b.conversation_id == conv_nhom.id]
            assert bao_cua_nhom == [], [(b.type, b.title) for b in bao_cua_nhom]
            su_kien = (db.query(MemoryItem)
                       .filter(MemoryItem.customer_id == khach_nhom.id,
                               MemoryItem.source == "orchestrator").all())
            assert su_kien == [], [m.content for m in su_kien]  # không remember() sự kiện cho nhóm
        finally:
            db.close()
        # Đối chứng 1-1: cùng nội dung có SĐT -> VẪN thu thập như cũ
        r2 = client.post("/api/zalo/mock/nhan-tin-nhan", json={
            "external_id": "hv-f2-1b", "customer_external_id": "khach-hv-f2-ctrl",
            "customer_name": "Khách Đối Chứng", "content": "Số của em là 0901234567, tư vấn em với"},
            headers=headers())
        assert r2.status_code == 200, r2.text
        khach_ctrl = _khach("khach-hv-f2-ctrl")
        assert (khach_ctrl.phone or "").strip() == "0901234567", khach_ctrl.phone
    finally:
        _phuc_hoi(chup)


def test_102_f2_nhom_khong_hoi_sdt(monkeypatch):
    _lap_fake(monkeypatch, ghi := [])
    _lap_ai_kich_ban(monkeypatch, ["Dạ em tư vấn ngay đây ạ."])
    chup = _chup_cai_dat(); _cai_dat_nen()
    # Để trống intent/từ khóa kích hoạt -> mọi lượt đều đủ điều kiện hỏi SĐT ở 1-1
    _dat_cai_dat(thu_thap_tu_hoi_sdt=True, thu_thap_intent_hoi_sdt="", thu_thap_tu_khoa_hoi_sdt="")
    try:
        r = _gui_nhom("hv-f2-2", "nhom-hv-f2b", "Huy", "@Quỳnh Hoa tư vấn giúp mình với")
        assert r.json()["tra_loi"], r.text
        from app.models import Conversation, Customer
        db = _db()
        try:
            cust = db.query(Customer).filter(Customer.external_id == "nhom-hv-f2b").first()
            conv_nhom = (db.query(Conversation).filter(Conversation.customer_id == cust.id)
                         .order_by(Conversation.id.desc()).first())
        finally:
            db.close()
        assert not _co_log("thu_thap", f"da_hoi_sdt conv={conv_nhom.id}")
        # Đối chứng 1-1: cùng điều kiện -> CÓ ghi đã hỏi SĐT
        r2 = _gui_1_1("hv-f2-2b", "khach-hv-f2b", "tư vấn giúp mình với")
        assert r2.json()["tra_loi"], r2.text
        db = _db()
        try:
            cust2 = db.query(Customer).filter(Customer.external_id == "khach-hv-f2b").first()
            conv_11 = (db.query(Conversation).filter(Conversation.customer_id == cust2.id)
                       .order_by(Conversation.id.desc()).first())
        finally:
            db.close()
        assert _co_log("thu_thap", f"da_hoi_sdt conv={conv_11.id}")
    finally:
        _phuc_hoi(chup)


def _bat_payload_tom_tat(monkeypatch, noi_dung_tra_loi="Bản tóm tắt giả lập F2"):
    """Chặn httpx.Client để bắt payload gửi provider (mẫu test_nang_cap_2)."""
    import httpx as _httpx
    captured = {}

    class FakeResp:
        status_code = 200
        headers = {"content-type": "application/json"}
        text = json.dumps({"model": "m-gia-lap", "choices": [{"message": {"content": noi_dung_tra_loi}}],
                           "usage": {"prompt_tokens": 5, "completion_tokens": 2}})

    class FakeClient:
        def __init__(self, timeout=None, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, headers=None, json=None):
            captured.clear(); captured.update(json or {})
            return FakeResp()

    monkeypatch.setattr(_httpx, "Client", FakeClient)
    return captured


def test_103_f2_prompt_tom_tat_nhom_chi_cot_loi(monkeypatch):
    # Provider thật (openai_compatible) làm mặc định để đi đường _tom_tat_bang_ai
    r = client.post("/api/ai-providers", json={
        "name": "Provider tom tat F2", "provider": "openai_compatible",
        "base_url": "http://gia-lap-f2.local/v1", "api_key": "k-gia-f2", "model": "m-f2"},
        headers=headers())
    assert r.status_code == 200, r.text
    _dat_provider_mac_dinh_theo_ten("Provider tom tat F2")
    captured = _bat_payload_tom_tat(monkeypatch)
    try:
        from app.models import Conversation, Customer, Message
        from app.services import memory_service
        db = _db()
        try:
            # --- Khách NHÓM: tóm tắt phải dùng chỉ dẫn cốt lõi cấp nhóm ---
            cust_nhom = Customer(external_id="nhom-f2-103", display_name="Nhóm Test F2")
            db.add(cust_nhom); db.commit(); db.refresh(cust_nhom)
            conv_nhom = Conversation(customer_id=cust_nhom.id, channel="ca_nhan")
            db.add(conv_nhom); db.commit(); db.refresh(conv_nhom)
            for ten, nd in [("Huy", "nhóm mình chốt lịch đá bóng tối thứ 7 nhé"),
                            ("Lan", "số mình 0901234567 nè, mà luật nhóm là không spam quảng cáo"),
                            ("Huy", "ok chốt, ai đi trễ phạt 50k vào quỹ")]:
                db.add(Message(conversation_id=conv_nhom.id, sender_type="khach",
                               content=nd, status="da_nhan", sender_name=ten))
            db.commit()
            kq = memory_service.cap_nhat_tom_tat_bo_nho(
                db, cust_nhom, {"bo_nho_tom_tat_sau_bao_nhieu_tin": 6}, force=True, la_nhom=True)
            assert kq, "Tóm tắt nhóm phải trả về bản tóm tắt"
            msgs = captured["messages"]
            he_thong, nguoi_dung = msgs[0]["content"], msgs[-1]["content"]
            assert "nhóm chat" in he_thong and "thông tin cá nhân" in he_thong, he_thong
            assert "CỐT LÕI" in nguoi_dung and "TUYỆT ĐỐI KHÔNG" in nguoi_dung, nguoi_dung
            assert "Huy: " in nguoi_dung and "Lan: " in nguoi_dung  # transcript ghi tên người nói
            # --- Khách 1-1: giữ prompt hồ sơ cũ ---
            cust_11 = Customer(external_id="khach-f2-103", display_name="Khách F2 103")
            db.add(cust_11); db.commit(); db.refresh(cust_11)
            conv_11 = Conversation(customer_id=cust_11.id, channel="ca_nhan")
            db.add(conv_11); db.commit(); db.refresh(conv_11)
            db.add(Message(conversation_id=conv_11.id, sender_type="khach",
                           content="mình muốn hỏi giá dịch vụ", status="da_nhan"))
            db.commit()
            kq2 = memory_service.cap_nhat_tom_tat_bo_nho(
                db, cust_11, {"bo_nho_tom_tat_sau_bao_nhieu_tin": 6}, force=True, la_nhom=False)
            assert kq2
            nguoi_dung_11 = captured["messages"][-1]["content"]
            assert "HỒ SƠ TÓM TẮT MỚI" in nguoi_dung_11 and "nhu cầu và sở thích" in nguoi_dung_11, nguoi_dung_11
            assert "CỐT LÕI CẤP NHÓM" not in nguoi_dung_11, nguoi_dung_11
        finally:
            db.close()
    finally:
        _dat_provider_mac_dinh_theo_ten("Mock AI (mô phỏng)")


def test_104_f2_lich_su_nhom_ghi_nhan_nguoi_noi(monkeypatch):
    _lap_fake(monkeypatch, ghi := [])
    bat = {}
    _lap_ai_kich_ban(monkeypatch, ["Dạ, 19h tập trung ở sân nhé mọi người."], bat)
    chup = _chup_cai_dat(); _cai_dat_nen()
    try:
        # 2 tin KHÔNG tag (bị cổng tag bỏ qua nhưng vẫn lưu + có tên người gửi)
        _gui_nhom("hv-f2-4a", "nhom-hv-f2c", "Huy Quốc", "tối nay ai đi đá bóng không", tag=False)
        _gui_nhom("hv-f2-4b", "nhom-hv-f2c", "Lan Anh", "mình đi được nhé", tag=False)
        # Tin thứ 3 có tag -> AI sinh trả lời với lịch sử đã ghi nhãn
        r = _gui_nhom("hv-f2-4c", "nhom-hv-f2c", "Huy Quốc", "@Quỳnh Hoa mấy giờ tập trung vậy")
        assert r.json()["tra_loi"], r.text
        lich_su = bat["kwargs"].get("lich_su") or []
        noi_dung_ls = [m["content"] for m in lich_su]
        assert "Huy Quốc: tối nay ai đi đá bóng không" in noi_dung_ls, noi_dung_ls
        assert "Lan Anh: mình đi được nhé" in noi_dung_ls, noi_dung_ls
        # DB: cột sender_name đã lưu đúng từng người
        from app.models import Message
        db = _db()
        try:
            dong = (db.query(Message).filter(Message.external_id.in_(("hv-f2-4a", "hv-f2-4b")))
                    .order_by(Message.id).all())
            assert [m.sender_name for m in dong] == ["Huy Quốc", "Lan Anh"], [m.sender_name for m in dong]
        finally:
            db.close()
    finally:
        _phuc_hoi(chup)


# ================= F3 — bộ lọc chống lặp câu =================

CAU_BANTER_TRUNG = "Ừa ừa, rồi sao nữa, hóng ghê"


def _tao_provider_f3():
    ds = client.get("/api/ai-providers", headers=headers()).json()
    if not [x for x in ds if x["name"] == "Provider chong lap F3"]:
        r = client.post("/api/ai-providers", json={
            "name": "Provider chong lap F3", "provider": "openai_compatible",
            "base_url": "http://gia-lap-f3.local/v1", "api_key": "k-gia-f3", "model": "m-f3"},
            headers=headers())
        assert r.status_code == 200, r.text
    _dat_provider_mac_dinh_theo_ten("Provider chong lap F3")


def _gieo_cau_bot_da_gui(noi_dung=CAU_BANTER_TRUNG):
    """Gieo sẵn 1 câu bot da_gui trong một hội thoại kênh cá nhân khác —
    đúng bằng chứng thật: câu banter đã bị dùng gần đây trên hệ thống."""
    from app.models import Conversation, Customer, Message
    db = _db()
    try:
        cust = db.query(Customer).filter(Customer.external_id == "khach-gieo-f3").first()
        if not cust:
            cust = Customer(external_id="khach-gieo-f3", display_name="Khách Gieo F3")
            db.add(cust); db.commit(); db.refresh(cust)
        conv = (db.query(Conversation).filter(Conversation.customer_id == cust.id)
                .order_by(Conversation.id.desc()).first())
        if not conv:
            conv = Conversation(customer_id=cust.id, channel="ca_nhan")
            db.add(conv); db.commit(); db.refresh(conv)
        if not db.query(Message).filter(Message.conversation_id == conv.id,
                                        Message.content == noi_dung).first():
            db.add(Message(conversation_id=conv.id, sender_type="bot",
                           content=noi_dung, status="da_gui"))
            db.commit()
    finally:
        db.close()


def test_105_f3_trung_cau_thi_sinh_lai_cau_khac(monkeypatch):
    _lap_fake(monkeypatch, ghi := [])
    _gieo_cau_bot_da_gui()
    _tao_provider_f3()
    trang_thai = _lap_ai_kich_ban(
        monkeypatch, [CAU_BANTER_TRUNG, "Thật hả, kể tiếp đoạn sau đi bạn ơi"])
    chup = _chup_cai_dat(); _cai_dat_nen()
    try:
        r = _gui_1_1("hv-f3-1", "khach-hv-f3a", "kể nghe chơi đi shop")
        j = r.json()
        assert j["tra_loi"] == "Thật hả, kể tiếp đoạn sau đi bạn ơi", j
        assert trang_thai["n"] == 2, trang_thai  # AI bị gọi đúng 2 lần
        gui = _cac_lan_gui(ghi)
        assert gui and all(g[2] != CAU_BANTER_TRUNG for g in gui), gui
        assert _co_log("chong_lap_cau", "phat_hien_trung_cau conv=")
    finally:
        _phuc_hoi(chup)
        _dat_provider_mac_dinh_theo_ten("Mock AI (mô phỏng)")


def test_106_f3_khong_trung_chi_goi_ai_mot_lan(monkeypatch):
    _lap_fake(monkeypatch, ghi := [])
    _tao_provider_f3()
    cau_moi = "Câu trả lời hoàn toàn mới chưa từng xuất hiện ở bất cứ đâu cả"
    trang_thai = _lap_ai_kich_ban(monkeypatch, [cau_moi])
    chup = _chup_cai_dat(); _cai_dat_nen()
    try:
        r = _gui_1_1("hv-f3-2", "khach-hv-f3b", "hỏi gì đó mới lạ đi")
        j = r.json()
        assert j["tra_loi"] == cau_moi, j
        assert trang_thai["n"] == 1, trang_thai  # không tốn lượt gọi thừa
    finally:
        _phuc_hoi(chup)
        _dat_provider_mac_dinh_theo_ten("Mock AI (mô phỏng)")


def test_107_f3_nhom_trung_ca_hai_lan_thi_bo_qua(monkeypatch):
    _lap_fake(monkeypatch, ghi := [])
    _gieo_cau_bot_da_gui()
    _tao_provider_f3()
    trang_thai = _lap_ai_kich_ban(monkeypatch, [CAU_BANTER_TRUNG])
    chup = _chup_cai_dat(); _cai_dat_nen()
    try:
        r = _gui_nhom("hv-f3-3", "nhom-hv-f3", "Huy", "@Quỳnh Hoa kể nghe chơi")
        j = r.json()
        assert j["tra_loi"] is None and j["ly_do"] == "bo_qua_trung_cau", j
        assert trang_thai["n"] == 2, trang_thai  # đã thử sinh lại đúng 1 lần
        assert _cac_lan_gui(ghi) == [], ghi  # nhóm: vẫn trùng -> im lặng hẳn
        assert _co_log("chong_lap_cau", "bo_qua_trung_cau_nhom conv=")
    finally:
        _phuc_hoi(chup)
        _dat_provider_mac_dinh_theo_ten("Mock AI (mô phỏng)")
