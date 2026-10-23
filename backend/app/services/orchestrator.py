"""Bộ điều phối AI - pipeline rút gọn nhưng thật (19 bước gốc được gom nhóm có log).
1 validate, 2 dedup external_message_id, 3 customer, 4 conversation, 5 automation check (bot paused/human),
6 intent, 7 entities (lấy từ khóa), 8-9 retrieve knowledge+memory+service, 10 policy, 11 chọn model,
12 generate, 13 output check, 14 action check, 15 quyết định gửi/chuyển, 16 send qua connector,
17 lưu, 18 cập nhật memory, 19 log/usage.

Đợt nâng cấp 2 bổ sung (mọi ngưỡng/hành vi đều đọc RUNTIME từ Cài đặt):
- Mục 7: tin NHÓM chỉ được trả lời khi bot được tag đích danh (mention chứa
  UID của bot hoặc tên bot cấu hình); tag @all (uid -1) không tính; bị bỏ qua
  thì ghi log "bo_qua_nhom_khong_tag".
- Mục 10: truyền lịch sử hội thoại đa lượt cho AI + prompt persona theo Cài đặt.
- Mục 5+6: chuẩn hoá định dạng Zalo rồi chia nhỏ tin khi gửi qua kênh cá nhân.
- Mục 4: thả tim tin khách (bot_tha_tim) qua connector cá nhân.
- Mục 9.5: khách là bạn bè Zalo đã phân bổ -> gắn admin phụ trách.
- Gate theo Cài đặt: giờ hoạt động, từ khóa cấm, ngưỡng chuyển nhân viên,
  bật/tắt module (thu thập / tự động hóa / bộ nhớ / trả lời toàn cục).
- Chế độ TRÒ CHUYỆN TỰ DO (che_do_tro_chuyen_tu_do): bỏ qua tri thức/dịch vụ/
  bộ nhớ tư vấn, tắt hỏi SĐT + tắt thông báo lead; luật nhóm, từ khóa cấm,
  chuyển nhân viên, thả tim, chia tin, định dạng Zalo vẫn áp dụng như thường.

Đợt bổ sung 23/10/2026 (yêu cầu của LAM — nhắn như người thật):
- A: chia tin TỰ NHIÊN theo ngưỡng mềm do_dai_muc_tieu_moi_tin (mặc định
  120 ký tự) — reply ngắn vẫn tách thành nhiều bong bóng theo câu.
- B: GOM tin khách gửi liên tiếp ở chat 1-1 (gom_tin_lien_tiep +
  thoi_gian_gom_tin_giay): tiep_nhan_tin_den() đệm payload theo khách,
  các tin trừ tin cuối chạy process_inbound với bo_qua_tra_loi=True (vẫn
  lưu + trích xuất), tin cuối trả lời 1 lượt với đủ ngữ cảnh.
- C: bot TỰ NHẮN THÊM (bot_tu_nhan_them): sau khi trả lời 1-1 thành công,
  lên lịch 1 tin phụ sau khoảng ngẫu nhiên (min–max giây); khi tới giờ,
  thuc_hien_tin_nhan_them() kiểm tra lại các điều kiện hủy (tiếp quản,
  khách đã nhắn tiếp, nhân viên đã nhắn, đã có tin thêm) rồi mới gửi.
"""
import difflib
import json
import os
import random
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..models import Customer, Conversation, Message, SystemLog, ServiceItem, User, PhanBoBanBe
from .text_utils import classify_intent, normalize_vi
from . import knowledge_service, memory_service, ai_gateway, automation_service, extraction_service, notification_service, anh_service
from .zalo_connector import mock_connector, ZaloPersonalConnector
from .dinh_dang import dinh_dang_tin_zalo, chia_tin_nhan

CAU_HOI_SDT_MAC_DINH = "Anh/chị cho em xin số điện thoại để tư vấn viên liên hệ tư vấn chi tiết hơn ạ."


def _doc_cai_dat(db: Session) -> dict:
    try:
        from ..routers.cai_dat import doc_cai_dat
        return doc_cai_dat(db)
    except Exception:
        return {}


def _thong_bao(db, loai, title, content, cust=None, conv=None, level="thong_tin", channel="mo_phong"):
    """Tạo thông báo admin — bọc try/except ở notification_service, không chặn pipeline."""
    try:
        notification_service.notify(db, loai, title, content,
                                    customer_id=cust.id if cust else None,
                                    conversation_id=conv.id if conv else None,
                                    level=level, channel=channel)
    except Exception:
        pass


def _da_hoi_sdt(db, conversation_id) -> bool:
    """Đã hỏi xin SĐT trong hội thoại này chưa (đánh dấu bằng SystemLog module thu_thap)."""
    return db.query(SystemLog).filter(
        SystemLog.module == "thu_thap",
        SystemLog.message == f"da_hoi_sdt conv={conversation_id}",
    ).first() is not None


def _ghi_da_hoi_sdt(db, conversation_id, trace=""):
    db.add(SystemLog(level="info", module="thu_thap", message=f"da_hoi_sdt conv={conversation_id}", trace_id=trace)); db.commit()


def _tach_danh_sach(tho: str):
    if not tho:
        return []
    return [p.strip() for p in str(tho).replace("\n", ",").split(",") if p.strip()]


def _duoc_tra_loi_trong_nhom(cai_dat: dict, content: str, mentions, bot_uid: str, thread_id: str) -> bool:
    """Mục 7: trong nhóm, bot chỉ trả lời khi được tag ĐÍCH DANH.

    - Mention chứa đúng UID của tài khoản bot (bot_uid) -> được trả lời.
    - Mention @all (uid "-1") KHÔNG tính là tag bot.
    - Hoặc nội dung chứa tên bot đã cấu hình (ten_bot_trong_nhom).
    - Chủ hệ thống chốt (đợt D): tag đúng là trả lời ở MỌI nhóm — cổng
      danh_sach_nhom_duoc_phep đã BỎ. Ngược lại, nhóm nằm trong
      danh_sach_nhom_bi_chan thì không trả lời kể cả khi tag đúng.
    """
    chan = _tach_danh_sach(cai_dat.get("danh_sach_nhom_bi_chan"))
    if chan and str(thread_id) in chan:
        return False
    if cai_dat.get("bot_nhom_chi_khi_duoc_tag", True) is False:
        return True
    uids = set()
    for m in (mentions or []):
        if isinstance(m, dict) and m.get("uid") is not None:
            uids.add(str(m["uid"]))
    if bot_uid and str(bot_uid) in uids:
        return True
    ten_bot = str(cai_dat.get("ten_bot_trong_nhom") or "").strip()
    if ten_bot and normalize_vi(ten_bot) in normalize_vi(content or ""):
        return True
    return False


def _trong_gio_lam_viec(cai_dat: dict) -> bool:
    bat = cai_dat.get("gio_hoat_dong_bat_dau", 0)
    ket = cai_dat.get("gio_hoat_dong_ket_thuc", 24)
    try:
        bat = int(bat); ket = int(ket)
    except (TypeError, ValueError):
        return True
    if bat == ket:
        return True
    try:
        from zoneinfo import ZoneInfo
        bay_gio = datetime.now(ZoneInfo(str(cai_dat.get("mui_gio") or "Asia/Ho_Chi_Minh")))
    except Exception:
        bay_gio = datetime.now(timezone.utc)
    gio = bay_gio.hour
    return (bat <= gio < ket) if bat < ket else (gio >= bat or gio < ket)


def _gan_admin_tu_ban_be(db: Session, cust: Customer, conv: Conversation, customer_external_id: str):
    """Mục 9.5: nếu người nhắn là bạn bè Zalo đã được phân bổ admin và
    khách/hội thoại CHƯA có người phụ trách -> gắn admin phụ trách đó."""
    try:
        pb = db.query(PhanBoBanBe).filter(PhanBoBanBe.zalo_friend_id == str(customer_external_id)).first()
        if not pb or not pb.admin_user_id:
            return
        admin_u = db.get(User, pb.admin_user_id)
        if not admin_u:
            return
        ten = admin_u.username or admin_u.full_name or admin_u.email
        thay_doi = False
        if not (cust.assignee or "").strip():
            cust.assignee = ten; thay_doi = True
        if not (conv.assignee or "").strip():
            conv.assignee = ten; thay_doi = True
        if thay_doi:
            db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


# =====================================================================
# PHẦN F3 — BỘ LỌC CHỐNG LẶP CÂU (xác thực/deterministic)
#
# Bằng chứng thật: AI (đặc biệt chế độ tự do) rơi vào "rãnh câu cửa miệng"
# và lặp NGUYÊN VĂN cùng vài câu banter ở mọi hội thoại (kể cả tự bắt
# chước câu cũ của chính nó trong lịch sử). Bộ lọc này không trông chờ AI
# tự giác: so câu sắp gửi với các câu bot ĐÃ GỬI gần đây TRÊN TOÀN HỆ
# THỐNG (mọi hội thoại kênh cá nhân) — trùng/gần trùng thì sinh lại 1 lần
# với chỉ dẫn diễn đạt khác hẳn; vẫn trùng thì nhóm -> im lặng, 1-1 -> vẫn
# gửi kèm log cảnh báo. Chỉ áp cho reply AI sinh qua provider THẬT (kênh
# ca_nhan) — câu mẫu cứng (ngoài giờ, hỏi SĐT...) và provider Mock không áp.
# =====================================================================
_DAU_CAU_CUOI = " .,!?…~\"'”’"


def _chuan_hoa_cau(text) -> str:
    """Chuẩn hoá một câu để so trùng: lowercase, gộp khoảng trắng, bỏ dấu
    câu ở cuối, cắt ngắn. Hai câu chỉ khác dấu câu cuối/viết hoa vẫn tính
    là một."""
    s = str(text or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = s.strip()
    while s and s[-1] in _DAU_CAU_CUOI:
        s = s[:-1].rstrip()
    return s[:200]


def _cac_cau_bot_gan_day(db: Session, gioi_han: int = 20):
    """Các câu bot đã gửi gần nhất trên toàn hệ thống (chỉ hội thoại kênh
    cá nhân, chỉ tin VĂN BẢN đã gửi thành công) — đã chuẩn hoá, tối đa
    `gioi_han` câu. Quét dư một ít để bù các tin sticker/không phải chữ."""
    try:
        rows = (db.query(Message)
                .join(Conversation, Message.conversation_id == Conversation.id)
                .filter(Conversation.channel == "ca_nhan",
                        Message.sender_type == "bot",
                        Message.status == "da_gui")
                .order_by(Message.id.desc()).limit(100).all())
    except Exception:
        return []
    ket_qua = []
    for m in rows:
        if getattr(m, "attachment_type", "") == "sticker":
            continue
        if (m.content or "").strip() == "[sticker]":
            continue
        cau = _chuan_hoa_cau(m.content)
        if cau:
            ket_qua.append(cau)
        if len(ket_qua) >= gioi_han:
            break
    return ket_qua


def _tim_cau_trung(cau_chuan: str, cac_cau_gan):
    """Trả về câu gần đây bị trùng (bằng nhau sau chuẩn hoá, hoặc gần
    trùng với ratio >= 0.92), None nếu không trùng. Câu quá ngắn (< 10 ký
    tự chuẩn hoá) bỏ qua để tránh báo nhầm các câu xã giao cực ngắn."""
    if not cau_chuan or len(cau_chuan) < 10:
        return None
    for cau_cu in cac_cau_gan or []:
        if cau_chuan == cau_cu:
            return cau_cu
        if len(cau_cu) >= 10 and difflib.SequenceMatcher(None, cau_chuan, cau_cu).ratio() >= 0.92:
            return cau_cu
    return None


def process_inbound(db: Session, external_id: str, customer_external_id: str, customer_name: str, content: str,
                    zalo_account_id=None, channel: str = "mo_phong",
                    mentions=None, la_nhom: bool = False, bot_uid: str = "",
                    nguoi_gui_id: str = "", cli_msg_id: str = "", dinh_kem=None,
                    bo_qua_tra_loi: bool = False):
    trace = str(uuid.uuid4())[:8]
    cai_dat = _doc_cai_dat(db)
    # Chế độ trò chuyện tự do: bot nghỉ bán hàng — không hỏi SĐT, không báo
    # lead (co_so_dien_thoai/du_thong_tin), không chèn tri thức/doanh nghiệp.
    tu_do = bool(cai_dat.get("che_do_tro_chuyen_tu_do"))
    # Dedup trước khi tạo
    if external_id and db.query(Message).filter(Message.external_id == external_id).first():
        db.add(SystemLog(level="warning", module="orchestrator", message=f"Tin trùng bị bỏ qua {external_id}", trace_id=trace)); db.commit()
        return {"trung": True, "trace_id": trace, "tra_loi": None}
    cust = db.query(Customer).filter(Customer.external_id == customer_external_id).first()
    khach_moi = False
    if not cust:
        cust = Customer(external_id=customer_external_id, display_name=customer_name); db.add(cust); db.commit(); db.refresh(cust)
        khach_moi = True
    conv = db.query(Conversation).filter(Conversation.customer_id == cust.id).order_by(Conversation.created_at.desc()).first()
    if not conv or conv.status == "da_giai_quyet":
        conv = Conversation(customer_id=cust.id, zalo_account_id=zalo_account_id, channel=channel); db.add(conv); db.commit(); db.refresh(conv)
    elif getattr(conv, "channel", None) != channel:
        # Hội thoại cũ tạo từ kênh khác: cập nhật theo nguồn tin mới nhất
        conv.channel = channel; db.commit()
    _gan_admin_tu_ban_be(db, cust, conv, customer_external_id)
    # Đợt Hành vi nhóm: lưu tên NGƯỜI GỬI của riêng tin này (chỉ nhóm — mỗi
    # thành viên một tên; customer_name của payload nhóm chính là tên người
    # vừa nhắn). Chat 1-1 để trống. Dùng để ghi nhãn người nói trong lịch sử.
    msg = Message(conversation_id=conv.id, external_id=external_id, sender_type="khach", content=content, status="da_nhan",
                  sender_name=(str(customer_name or "") if la_nhom else ""))
    db.add(msg)
    try: db.commit()
    except IntegrityError:
        db.rollback(); return {"trung": True, "trace_id": trace, "tra_loi": None}
    db.refresh(msg)
    db.add(SystemLog(level="info", module="orchestrator", message=f"Nhận tin từ {cust.display_name}: {content[:80]}", trace_id=trace)); db.commit()
    cust.last_interaction_at = msg.created_at or datetime.now(timezone.utc); db.commit()
    # Đính kèm ẢNH khách gửi: tải về máy chủ (thư mục uploads) để bot "nhìn"
    # được ảnh qua payload multimodal + admin xem lại được trong Hội thoại.
    # Tải lỗi → vẫn lưu URL gốc của Zalo; mọi lỗi ở bước này KHÔNG chặn pipeline.
    anh_data_uri = ""
    for dk in (dinh_kem or []):
        if not isinstance(dk, dict) or dk.get("loai") != "anh" or not dk.get("url"):
            continue
        msg.attachment_type = "anh"
        kq_tai = None
        try:
            kq_tai = anh_service.tai_anh_tu_url(str(dk["url"]))
        except Exception:
            kq_tai = None
        if kq_tai:
            msg.attachment_url = f"/api/tep/{kq_tai['ten_file']}"
            try:
                anh_data_uri = anh_service.doc_anh_data_uri(kq_tai["duong_dan"])
            except Exception:
                anh_data_uri = ""
        else:
            msg.attachment_url = str(dk["url"])
        try:
            db.commit()
        except Exception:
            db.rollback()
        break
    # Mục 7: cổng nhóm Zalo — không được tag đích danh thì IM LẶNG (đã lưu tin
    # + ghi log), không thu thập, không thông báo, không trả lời, không thả tim.
    if la_nhom:
        uid_bot = str(bot_uid or "")
        if not uid_bot and channel == "ca_nhan":
            try:
                uid_bot = str(ZaloPersonalConnector().status().get("tai_khoan_id") or "")
            except Exception:
                uid_bot = ""
        if not _duoc_tra_loi_trong_nhom(cai_dat, content, mentions, uid_bot, str(customer_external_id)):
            db.add(SystemLog(level="info", module="orchestrator",
                             message=f"bo_qua_nhom_khong_tag thread={customer_external_id} conv={conv.id}",
                             trace_id=trace)); db.commit()
            return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "bo_qua_nhom_khong_tag",
                    "bo_qua": True, "conversation_id": conv.id, "customer_id": cust.id}
    # GĐ mở rộng 1: thông báo khách mới + tự thu thập thông tin từ tin nhắn.
    # Chạy kể cả khi bot đang tạm dừng (thu thập độc lập với trả lời);
    # mọi lỗi ở bước này chỉ ghi log, không chặn pipeline.
    # Đợt Hành vi nhóm (F2): NHÓM CÓ NGỮ CẢNH RIÊNG — nhóm KHÔNG phải lead
    # bán hàng nên bỏ qua CẢ thông báo khách mới LẪN trích xuất thông tin
    # cá nhân (tránh thu SĐT/chuyện riêng của thành viên vào hồ sơ nhóm và
    # tránh "dây" sang ngữ cảnh cá nhân). Chat 1-1 giữ nguyên 100%.
    if khach_moi and not la_nhom:
        _thong_bao(db, "khach_moi", "Khách hàng mới", f"Khách {cust.display_name or cust.external_id} vừa nhắn tin lần đầu qua kênh {channel}.", cust, conv, "thong_tin", channel)
    if not la_nhom and cai_dat.get("module_thu_thap_thong_tin", True) is not False:
        try:
            kq_thu_thap = extraction_service.extract_and_save(db, cust, msg)
            ten_khach = cust.display_name or cust.external_id
            # Đang chat giải trí (chế độ tự do) thì KHÔNG báo lead làm phiền admin
            if kq_thu_thap.get("sdt_moi") and not tu_do:
                _thong_bao(db, "co_so_dien_thoai", "Khách đã để lại số điện thoại", f"Khách {ten_khach} đã cung cấp số điện thoại {cust.phone}.", cust, conv, "thong_tin", channel)
            if kq_thu_thap.get("du_thong_tin_moi") and not tu_do:
                _thong_bao(db, "du_thong_tin", "Đã thu thập đủ thông tin khách", f"Khách {ten_khach} đã có đủ thông tin cơ bản theo các trường bắt buộc đã cấu hình.", cust, conv, "thong_tin", channel)
        except Exception as e:
            db.add(SystemLog(level="warning", module="thu_thap", message=f"Lỗi trích xuất thông tin khách: {e}", trace_id=trace)); db.commit()
    # PHẦN B (gom tin): tin này thuộc một batch gom và KHÔNG phải tin cuối —
    # đã lưu tin + trích xuất thông tin như thường, nhưng phần sinh/gửi câu
    # trả lời để tin CUỐI của batch đảm nhiệm (khi đó lịch sử đã gồm tin này
    # nên AI trả lời 1 lượt với đủ ngữ cảnh).
    if bo_qua_tra_loi:
        return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "da_gom_cho_tin_sau",
                "conversation_id": conv.id, "customer_id": cust.id}
    # Automation check: bot tạm dừng hoặc nhân viên tiếp quản -> không trả lời tự động
    if not conv.bot_enabled or conv.human_takeover:
        return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "bot_da_tam_dung_hoac_nhan_vien_tiep_quan", "conversation_id": conv.id, "customer_id": cust.id}
    if cai_dat.get("tu_dong_tra_loi_toan_cuc", True) is False:
        return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "tat_tra_loi_toan_cuc", "conversation_id": conv.id, "customer_id": cust.id}
    # Giờ hoạt động: ngoài giờ -> gửi câu ngoài giờ (nếu có) hoặc im lặng
    if not _trong_gio_lam_viec(cai_dat):
        cau_ngoai_gio = str(cai_dat.get("cau_tra_loi_ngoai_gio") or "").strip()
        if cau_ngoai_gio:
            return _send_reply(db, conv, cust, cau_ngoai_gio, trace, channel=channel, cai_dat=cai_dat,
                               tin_khach=_tin_khach(customer_external_id, external_id, cli_msg_id, la_nhom))
        return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "ngoai_gio_lam_viec", "conversation_id": conv.id, "customer_id": cust.id}
    # Từ khóa cấm: bot không tự trả lời, chỉ ghi log cho nhân viên
    chuoi_chuan = normalize_vi(content)
    for tu_cam in _tach_danh_sach(cai_dat.get("tu_khoa_cam")):
        if tu_cam and normalize_vi(tu_cam) in chuoi_chuan:
            db.add(SystemLog(level="warning", module="orchestrator", message=f"Tin chứa từ khóa cấm '{tu_cam}' conv={conv.id} - bot không trả lời", trace_id=trace)); db.commit()
            return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "chua_tu_khoa_cam", "conversation_id": conv.id, "customer_id": cust.id}
    intent = classify_intent(content)
    if intent == "khieu_nai":
        _thong_bao(db, "khieu_nai", "Khách hàng khiếu nại", f"Khách {cust.display_name or cust.external_id} có dấu hiệu khiếu nại: {content[:120]}", cust, conv, "canh_bao", channel)
    if intent == "gap_nhan_vien":
        db.add(SystemLog(level="info", module="orchestrator", message=f"yeu_cau_gap_nhan_vien conv={conv.id}", trace_id=trace)); db.commit()
        so_lan = db.query(SystemLog).filter(
            SystemLog.module == "orchestrator",
            SystemLog.message == f"yeu_cau_gap_nhan_vien conv={conv.id}").count()
        try:
            nguong = int(cai_dat.get("so_lan_yeu_cau_gap_nhan_vien_de_chuyen") or 1)
        except (TypeError, ValueError):
            nguong = 1
        if so_lan >= max(1, nguong):
            _thong_bao(db, "gap_nhan_vien", "Khách yêu cầu gặp nhân viên", f"Khách {cust.display_name or cust.external_id} yêu cầu gặp nhân viên: {content[:120]}", cust, conv, "canh_bao", channel)
            conv.human_takeover = True; db.commit()
            return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "chuyen_nhan_vien_theo_yeu_cau", "conversation_id": conv.id, "customer_id": cust.id, "intent": intent}
        # Chưa đủ ngưỡng: bot tiếp tục hỗ trợ trước, chuyển thật khi đủ số lần yêu cầu
        db.add(SystemLog(level="info", module="orchestrator", message=f"Khách yêu cầu gặp nhân viên lần {so_lan}/{nguong} conv={conv.id} - bot tiếp tục hỗ trợ", trace_id=trace)); db.commit()
    rule = None
    if cai_dat.get("module_tu_dong_hoa", True) is not False:
        rule = automation_service.evaluate_rules(db, conv, content, intent)
    if rule:
        if rule.action_type == "tra_loi" and rule.action_value:
            return _send_reply(db, conv, cust, rule.action_value, trace, rule=rule, channel=channel, cai_dat=cai_dat,
                               tin_khach=_tin_khach(customer_external_id, external_id, cli_msg_id, la_nhom))
        if rule.action_type == "gan_nhan":
            conv.labels = (conv.labels + "," + rule.action_value).strip(","); db.commit()
        if rule.action_type == "chuyen_nhan_vien":
            _thong_bao(db, "gap_nhan_vien", "Khách được chuyển cho nhân viên theo quy tắc", f"Quy tắc tự động hóa đã chuyển hội thoại của khách {cust.display_name or cust.external_id} cho nhân viên.", cust, conv, "canh_bao", channel)
            conv.human_takeover = True; db.commit(); return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "quy_tac_chuyen_nhan_vien", "conversation_id": conv.id, "customer_id": cust.id}
        if rule.action_type == "tam_dung_bot":
            conv.bot_enabled = False; db.commit(); return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "quy_tac_tam_dung_bot", "conversation_id": conv.id, "customer_id": cust.id}
    # Chế độ tự do: KHÔNG truy xuất tri thức/dịch vụ/bộ nhớ tư vấn — chat thuần.
    chunks = []
    memories = []
    if not tu_do:
        chunks = knowledge_service.retrieve(db, content, limit=5)
        # Dịch vụ liên quan: cộng điểm nếu tên dịch vụ xuất hiện
        for s in db.query(ServiceItem).filter(ServiceItem.is_active == True).all():
            if normalize_vi(s.name) in normalize_vi(content) and s.description:
                chunks = [{"document_id": None, "title": s.name, "content": f"{s.name}: {s.description} Giá: {s.price_text or s.price}", "score": 99}] + chunks
                break
        if cai_dat.get("module_bo_nho_ai", True) is not False:
            memories = memory_service.retrieve_memories(db, cust.id, content, limit=3)
    # GĐ mở rộng 1 + registry: khách chưa có SĐT + intent/từ khóa cấu hình ->
    # hỏi xin SĐT, tối đa 1 lần cho mỗi hội thoại (tắt được bằng thu_thap_tu_hoi_sdt).
    # Chế độ tự do: KHÔNG hỏi SĐT (đang chat bạn bè, hỏi số là phá vibe).
    intent_hoi = _tach_danh_sach(cai_dat.get("thu_thap_intent_hoi_sdt"))
    tu_khoa_hoi = _tach_danh_sach(cai_dat.get("thu_thap_tu_khoa_hoi_sdt"))
    kich_hoat_hoi = (not intent_hoi and not tu_khoa_hoi) or intent in intent_hoi or any(
        normalize_vi(tk) in chuoi_chuan for tk in tu_khoa_hoi)
    can_hoi_sdt = (not (cust.phone or "").strip()) and kich_hoat_hoi
    # Đợt Hành vi nhóm (F2): trong NHÓM không bao giờ hỏi xin SĐT (hỏi số cá
    # nhân giữa nhóm đông người là sai ngữ cảnh), kể cả khi intent khớp.
    hoi_sdt = (not la_nhom) and (not tu_do) and (cai_dat.get("thu_thap_tu_hoi_sdt", True) is not False) and can_hoi_sdt and not _da_hoi_sdt(db, conv.id)
    # PR chủ động: danh sách dịch vụ đang mở bán để tiêm vào prompt tư vấn
    # (chỉ chế độ tư vấn; giá 0 và không có giá chữ thì bỏ phần giá).
    dich_vu_pr = []
    if not tu_do and cai_dat.get("bot_chu_dong_pr", True) is not False:
        try:
            so_dv = int(cai_dat.get("so_dich_vu_pr") or 5)
        except (TypeError, ValueError):
            so_dv = 5
        for s in (db.query(ServiceItem).filter(ServiceItem.is_active == True)
                  .order_by(ServiceItem.id).limit(max(1, so_dv)).all()):
            gia = (s.price_text or "").strip()
            if not gia and s.price:
                gia = f"{s.price:,.0f}".replace(",", ".") + "đ"
            dich_vu_pr.append({"ten": s.name, "gia": gia, "mo_ta": (s.description or "")[:200]})
    provider = ai_gateway.get_default_provider(db)
    la_mock = (not provider) or provider.provider == "mock"
    # Mục 10: lịch sử hội thoại đa lượt (số tin theo Cài đặt so_tin_nhan_ngu_canh),
    # không tính tin khách hiện tại (nó là câu hỏi đang xử lý).
    try:
        so_tin_ls = int(cai_dat.get("so_tin_nhan_ngu_canh") or 10)
    except (TypeError, ValueError):
        so_tin_ls = 10
    dong_ls = (db.query(Message)
               .filter(Message.conversation_id == conv.id, Message.id != msg.id)
               .order_by(Message.id.desc()).limit(max(1, so_tin_ls)).all())
    # Đợt E: KHÔNG nạp tin sticker vào lịch sử cho AI. Sticker bot đã gửi
    # được lưu content="[sticker]" (attachment_type="sticker"); nếu nạp
    # nguyên văn thành lượt assistant, AI sẽ BẮT CHƯỚC viết chữ "[sticker]"
    # vào câu trả lời văn bản (lỗi thật khi test). Cũng loại các tin bot cũ
    # chỉ chứa đúng "[sticker]" mà chưa có attachment_type.
    def _la_tin_sticker(m) -> bool:
        if getattr(m, "attachment_type", "") == "sticker":
            return True
        return m.sender_type == "bot" and (m.content or "").strip() == "[sticker]"
    # Đợt Hành vi nhóm: lịch sử NHÓM ghi nhãn NGƯỜI NÓI ("Tên: nội dung") —
    # nhóm có nhiều thành viên, gộp tất cả thành một "user" vô danh khiến AI
    # tưởng đang nói chuyện với một người và lẫn ngữ cảnh. Chat 1-1 giữ nguyên.
    def _noi_dung_lich_su(m) -> str:
        if la_nhom and m.sender_type == "khach":
            ten = (getattr(m, "sender_name", "") or "").strip()
            if ten:
                return f"{ten}: {m.content}"
        return m.content
    lich_su = [{"role": "user" if m.sender_type == "khach" else "assistant", "content": _noi_dung_lich_su(m)}
               for m in reversed(dong_ls) if m.content and not _la_tin_sticker(m)]
    try:
        reply, model_used = ai_gateway.generate_reply(
            db, provider, content, chunks, memories,
            goi_y_hoi_sdt=(hoi_sdt and not la_mock), lich_su=lich_su, cai_dat=cai_dat,
            dich_vu=dich_vu_pr, ho_so_khach=(cust.memory_summary or ""),
            anh_data_uri=anh_data_uri, luat_nhom=la_nhom)
    except ai_gateway.LoiVision as e:
        # Model phía sau provider KHÔNG hỗ trợ xem ảnh: ghi nhật ký riêng
        # "provider_khong_ho_tro_anh" + đánh dấu lên tin của khách để admin
        # biết, rồi trả câu dự phòng lịch sự thay vì im lặng/sập pipeline.
        db.add(SystemLog(level="warning", module="ai_gateway",
                         message=f"provider_khong_ho_tro_anh conv={conv.id} msg={msg.id}: {e}",
                         trace_id=trace)); db.commit()
        try:
            msg.error = "provider_khong_ho_tro_anh"; db.commit()
        except Exception:
            db.rollback()
        cau_du_phong_anh = ("Dạ em đã nhận được ảnh của anh/chị rồi ạ. Hiện hệ thống bên em chưa xem rõ "
                            "được nội dung ảnh này, anh/chị mô tả thêm giúp em, hoặc em chuyển nhân viên "
                            "xem trực tiếp cho mình nhé.")
        return _send_reply(db, conv, cust, cau_du_phong_anh, trace, intent=intent, channel=channel,
                           cai_dat=cai_dat,
                           tin_khach=_tin_khach(customer_external_id, external_id, cli_msg_id, la_nhom))
    except ai_gateway.AIError as e:
        db.add(SystemLog(level="error", module="orchestrator", message=f"Lỗi AI: {e}", trace_id=trace)); db.commit()
        _thong_bao(db, "bot_khong_tra_loi_duoc", "Bot không trả lời được", f"Bot không trả lời được khách {cust.display_name or cust.external_id} do lỗi nhà cung cấp AI: {e}", cust, conv, "canh_bao", channel)
        cau_du_phong = str(cai_dat.get("cau_khi_bot_khong_tra_loi") or "").strip()
        if cau_du_phong:
            return _send_reply(db, conv, cust, cau_du_phong, trace, channel=channel, cai_dat=cai_dat,
                               tin_khach=_tin_khach(customer_external_id, external_id, cli_msg_id, la_nhom))
        return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": f"loi_provider: {e}", "conversation_id": conv.id, "customer_id": cust.id}
    # PHẦN F3: bộ lọc CHỐNG LẶP CÂU — chỉ reply AI sinh qua provider thật ở
    # kênh cá nhân (1-1 lẫn nhóm), không áp token [BO_QUA] (chốt F1 xử lý).
    # Trùng -> sinh lại ĐÚNG 1 lần với chỉ dẫn diễn đạt khác hẳn; vẫn trùng
    # -> NHÓM bỏ qua hẳn, 1-1 vẫn gửi bản lần 2 kèm log cảnh báo.
    if channel == "ca_nhan" and not la_mock and (reply or "").strip() and (reply or "").strip() != "[BO_QUA]":
        cau_trung = _tim_cau_trung(_chuan_hoa_cau(reply), _cac_cau_bot_gan_day(db))
        if cau_trung:
            db.add(SystemLog(level="warning", module="chong_lap_cau",
                             message=f"phat_hien_trung_cau conv={conv.id} cau_trung='{cau_trung[:80]}'",
                             trace_id=trace)); db.commit()
            chi_dan_lai = (f"Câu bạn vừa định nói đã bị dùng gần đây rồi ('{(reply or '')[:120]}'), "
                           "hãy nói lại ý đó bằng cách diễn đạt hoàn toàn khác, không dùng lại cụm từ cũ.")
            try:
                reply_moi, model_moi = ai_gateway.generate_reply(
                    db, provider, content, chunks, memories,
                    goi_y_hoi_sdt=(hoi_sdt and not la_mock), lich_su=lich_su, cai_dat=cai_dat,
                    dich_vu=dich_vu_pr, ho_so_khach=(cust.memory_summary or ""),
                    anh_data_uri=anh_data_uri, luat_nhom=la_nhom,
                    chi_dan_bo_sung=chi_dan_lai)
                if (reply_moi or "").strip():
                    reply, model_used = reply_moi, model_moi
            except Exception as e:
                db.add(SystemLog(level="warning", module="chong_lap_cau",
                                 message=f"sinh_lai_that_bai conv={conv.id}: {e}", trace_id=trace)); db.commit()
            if _tim_cau_trung(_chuan_hoa_cau(reply), _cac_cau_bot_gan_day(db)):
                if la_nhom:
                    db.add(SystemLog(level="warning", module="chong_lap_cau",
                                     message=f"bo_qua_trung_cau_nhom conv={conv.id} cau='{_chuan_hoa_cau(reply)[:80]}'",
                                     trace_id=trace)); db.commit()
                    return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "bo_qua_trung_cau",
                            "conversation_id": conv.id, "customer_id": cust.id}
                db.add(SystemLog(level="warning", module="chong_lap_cau",
                                 message=f"van_gui_du_trung_cau_1_1 conv={conv.id} cau='{_chuan_hoa_cau(reply)[:80]}'",
                                 trace_id=trace)); db.commit()
    # Đợt Hành vi nhóm (F1): chốt chống rep VỚ VẨN trong nhóm — AI đã được
    # dặn (luat_nhom) tự trả [BO_QUA] khi tin tag chỉ là chửi/bả/spam không
    # nội dung. Thấy token này ở lượt NHÓM thì IM LẶNG hẳn: không gửi tin,
    # không sticker (sticker chỉ chạy trong _send_reply). Lượt 1-1 KHÔNG áp
    # chốt này — giữ nguyên hành vi hiện tại.
    if la_nhom and (reply or "").strip() == "[BO_QUA]":
        db.add(SystemLog(level="info", module="orchestrator",
                         message=f"bo_qua_nhom_vo_van conv={conv.id}", trace_id=trace)); db.commit()
        return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "bo_qua_nhom_vo_van",
                "conversation_id": conv.id, "customer_id": cust.id}
    if hoi_sdt:
        if la_mock:
            cau_hoi = str(cai_dat.get("thu_thap_cau_hoi_sdt") or CAU_HOI_SDT_MAC_DINH)
            reply = (reply or "").rstrip() + "\n" + cau_hoi
        _ghi_da_hoi_sdt(db, conv.id, trace)
    if khach_moi:
        tin_chao = str(cai_dat.get("tin_chao_khach_moi") or "").strip()
        if tin_chao:
            reply = tin_chao + "\n" + (reply or "")
    # Policy check đơn giản: không hứa hẹn ngoài dữ liệu - nếu không có nguồn và câu hỏi giá thì vẫn trả lời mẫu 'chưa đủ thông tin' từ mock
    ket_qua_gui = _send_reply(db, conv, cust, reply, trace, chunks=chunks, model_used=model_used, intent=intent, channel=channel,
                              cai_dat=cai_dat, tin_khach=_tin_khach(customer_external_id, external_id, cli_msg_id, la_nhom))
    # Bộ nhớ dài hạn: đủ số tin mới thì tóm tắt gộp hồ sơ khách (chỉ chế độ tư
    # vấn; hàm tự nuốt lỗi, không chặn pipeline). Lượt NHÓM truyền la_nhom để
    # tóm tắt theo kiểu CỐT LÕI CẤP NHÓM (không hồ sơ cá nhân) — đợt F2.
    if not tu_do:
        try:
            memory_service.cap_nhat_tom_tat_bo_nho(db, cust, cai_dat, la_nhom=la_nhom)
        except Exception:
            pass
    return ket_qua_gui


# =====================================================================
# PHẦN B — GOM TIN KHÁCH GỬI LIÊN TIẾP (chỉ chat 1-1, kênh cá nhân)
#
# Khách hay nhắn 2-3 tin dồn dập ("shop ơi" / "giá sao" / "có ship không").
# Trả lời từng tin thì bot rep cụt + thiếu ngữ cảnh. tiep_nhan_tin_den()
# đệm payload theo khóa khách trong cửa sổ gom (thoi_gian_gom_tin_giay):
# - Payload ĐẦU TIÊN của batch giữ vai "chủ batch": chờ hết cửa sổ (tin
#   mới tới trong lúc chờ sẽ gia hạn hạn chót) rồi gọi xu_ly_hang_gom() và
#   trả kết quả thật về cho chính request đó — webhook không phải trả
#   "đang gom" cho sidecar và thứ tự xử lý không bị đảo.
# - Các payload đến sau trong lúc chủ batch đang chờ chỉ nối vào hàng và
#   trả về ly_do="dang_gom_tin" ngay.
# - thoi_gian_gom_tin_giay = 0: chỉ đệm, không tự xả (kiểm thử gọi
#   xu_ly_hang_gom() trực tiếp; vận hành thật nên để >= 1 giây).
# GIỚI HẠN TRUNG THỰC: payload trong cửa sổ gom chỉ nằm trong BỘ NHỚ —
# máy chủ khởi động lại giữa cửa sổ gom (tối đa bằng số giây cấu hình)
# thì các tin chưa xả sẽ mất khỏi pipeline (tin gốc vẫn còn trên Zalo).
# =====================================================================
_HANG_GOM: dict = {}
_HANG_GOM_LOCK = threading.Lock()


def xu_ly_hang_gom(khoa):
    """Xả một hàng gom: chạy process_inbound lần lượt cho từng payload —
    các payload trừ payload CUỐI mang bo_qua_tra_loi=True (chỉ lưu +
    trích xuất), payload cuối chạy pipeline đầy đủ và trả lời 1 lượt.
    Mở session DB mới để dùng được từ mọi luồng. Lỗi chỉ ghi log
    (module "gom_tin"), không ném ra ngoài."""
    with _HANG_GOM_LOCK:
        muc = _HANG_GOM.pop(str(khoa), None)
    if not muc or not muc.get("payloads"):
        return None
    payloads = muc["payloads"]
    from ..database import SessionLocal
    db = SessionLocal()
    try:
        ket_qua = None
        for i, pl in enumerate(payloads):
            pl_day_du = dict(pl)
            pl_day_du["bo_qua_tra_loi"] = i < len(payloads) - 1
            ket_qua = process_inbound(db, **pl_day_du)
        try:
            db.add(SystemLog(level="info", module="gom_tin",
                             message=f"da_xa_hang_gom khoa={khoa} so_tin={len(payloads)}"))
            db.commit()
        except Exception:
            db.rollback()
        return ket_qua
    except Exception as e:
        try:
            db.rollback()
            db.add(SystemLog(level="error", module="gom_tin",
                             message=f"Lỗi xử lý hàng gom khoa={khoa}: {e}"))
            db.commit()
        except Exception:
            pass
        return None
    finally:
        db.close()


def tiep_nhan_tin_den(db: Session, external_id: str, customer_external_id: str, customer_name: str,
                      content: str, zalo_account_id=None, channel: str = "mo_phong",
                      mentions=None, la_nhom: bool = False, bot_uid: str = "",
                      nguoi_gui_id: str = "", cli_msg_id: str = "", dinh_kem=None):
    """Điểm vào DUY NHẤT cho tin đến (router zalo.py gọi hàm này).

    - Kênh mô phỏng / tin NHÓM / gom đang tắt -> process_inbound thẳng
      như trước (nhóm giữ nguyên xử lý từng tin theo luật tag).
    - Chat 1-1 kênh cá nhân + gom bật -> đệm payload theo khách, xem
      khối PHẦN B ở trên về cơ chế chủ batch chờ hết cửa sổ gom.
    """
    payload = {"external_id": external_id, "customer_external_id": customer_external_id,
               "customer_name": customer_name, "content": content,
               "zalo_account_id": zalo_account_id, "channel": channel,
               "mentions": mentions, "la_nhom": la_nhom, "bot_uid": bot_uid,
               "nguoi_gui_id": nguoi_gui_id, "cli_msg_id": cli_msg_id, "dinh_kem": dinh_kem}
    if channel != "ca_nhan" or la_nhom:
        return process_inbound(db, **payload)
    cai_dat = _doc_cai_dat(db)
    if not cai_dat.get("gom_tin_lien_tiep", True):
        return process_inbound(db, **payload)
    tho_giay = cai_dat.get("thoi_gian_gom_tin_giay")
    try:
        giay = float(5 if tho_giay is None else tho_giay)  # 0 là giá trị HỢP LỆ (không tự xả)
    except (TypeError, ValueError):
        giay = 5.0
    giay = min(30.0, max(0.0, giay))
    khoa = str(customer_external_id)
    dang_gom = {"trung": False, "tra_loi": None, "ly_do": "dang_gom_tin", "dang_gom": True}
    if giay <= 0:
        with _HANG_GOM_LOCK:
            muc = _HANG_GOM.setdefault(khoa, {"payloads": [], "han": 0.0, "dang_cho": False})
            muc["payloads"].append(payload)
        return dang_gom
    la_chu_batch = False
    with _HANG_GOM_LOCK:
        muc = _HANG_GOM.get(khoa)
        if muc is not None and muc.get("dang_cho"):
            muc["payloads"].append(payload)
            muc["han"] = time.monotonic() + giay
        else:
            muc = {"payloads": [payload], "han": time.monotonic() + giay, "dang_cho": True}
            _HANG_GOM[khoa] = muc
            la_chu_batch = True
    if not la_chu_batch:
        return dang_gom
    # Chủ batch: chờ hết cửa sổ gom (hạn chót được gia hạn mỗi khi có tin
    # mới nối vào) rồi xả hàng và trả kết quả của tin cuối cho request này.
    try:
        while True:
            with _HANG_GOM_LOCK:
                con_lai = muc["han"] - time.monotonic()
            if con_lai <= 0:
                break
            time.sleep(min(con_lai, 0.2))
    except Exception:
        pass
    ket_qua = xu_ly_hang_gom(khoa)
    return ket_qua or {"trung": False, "tra_loi": None, "ly_do": "loi_gom_tin", "dang_gom": True}


# =====================================================================
# PHẦN C — BOT TỰ NHẮN THÊM (follow-up chủ động, chỉ chat 1-1)
#
# Sau khi _send_reply gửi THÀNH CÔNG ở kênh cá nhân (không phải nhóm,
# không phải chính tin nhắn thêm), lên lịch 1 Timer ngẫu nhiên trong
# khoảng [tin_nhan_them_sau_giay_min, tin_nhan_them_sau_giay_max]. Khi
# Timer cháy, thuc_hien_tin_nhan_them() mở session mới và kiểm tra lại
# toàn bộ điều kiện hủy trước khi sinh + gửi — tối đa 1 tin thêm cho
# mỗi lượt khách nhắn, không bao giờ thành chuỗi vô hạn.
# =====================================================================
_CHI_DAN_NHAN_THEM = (
    "Bạn vừa trả lời xong. Hãy nhắn thêm ĐÚNG MỘT tin thật ngắn (1 câu) như người thật vừa nhớ ra: "
    "bổ sung ý hữu ích, gợi ý liên quan hoặc hỏi thêm nhu cầu. "
    "Nếu thật sự không có gì đáng nhắn thêm, trả về đúng chuỗi [BO_QUA] và không gì khác."
)


def _len_lich_tin_nhan_them(db, conv, cai_dat, tin_bot_id, trace=""):
    """Lên lịch tin nhắn thêm sau lượt bot vừa trả lời (kênh cá nhân 1-1).

    Tách thành hàm riêng để kiểm thử thay bằng bản ghi lại (không chờ thật).
    Mọi lỗi khi lên lịch đều bị nuốt — không được làm hỏng câu trả lời chính.
    """
    try:
        if not cai_dat.get("bot_tu_nhan_them"):
            return
        if not tin_bot_id:
            return

        def _so(khoa, mac_dinh):
            tho = cai_dat.get(khoa)
            try:
                return float(mac_dinh if tho is None else tho)  # 0 hợp lệ, không được thay bằng mặc định
            except (TypeError, ValueError):
                return float(mac_dinh)

        tre_min = _so("tin_nhan_them_sau_giay_min", 30)
        tre_max = _so("tin_nhan_them_sau_giay_max", 90)
        if tre_max < tre_min:
            tre_min, tre_max = tre_max, tre_min
        tre = random.uniform(tre_min, tre_max)
        timer = threading.Timer(tre, _hen_gio_nhan_them, args=(conv.id, tin_bot_id))
        timer.daemon = True
        timer.start()
    except Exception:
        pass


def _hen_gio_nhan_them(conversation_id, tin_bot_id):
    """Callback của Timer — nuốt mọi lỗi để luồng nền không bao giờ sập."""
    try:
        thuc_hien_tin_nhan_them(conversation_id, tin_bot_id)
    except Exception:
        pass


def _da_gui_nhan_them_cho(db, conversation_id, id_tin_khach) -> bool:
    """Đã có 1 tin nhắn thêm được gửi kể từ tin khách này chưa (đánh dấu
    bằng SystemLog module tin_nhan_them — cùng quy ước với da_hoi_sdt)."""
    return db.query(SystemLog).filter(
        SystemLog.module == "tin_nhan_them",
        SystemLog.message.like(f"da_gui_nhan_them conv={conversation_id} sau_khach={id_tin_khach} %"),
    ).first() is not None


def thuc_hien_tin_nhan_them(conversation_id, message_id_cua_luot_bot):
    """Thực hiện tin nhắn thêm (tách riêng để kiểm thử gọi đồng bộ).

    Mở session mới, kiểm tra các điều kiện HỦY (bất kỳ điều nào đúng thì
    hủy im lặng, chỉ ghi SystemLog module "tin_nhan_them"):
    (1) tính năng đã tắt / hội thoại bị nhân viên tiếp quản hoặc bot bị
        tạm dừng (đúng cơ chế conv.bot_enabled + conv.human_takeover mà
        process_inbound dùng để quyết định bot có được rep hay không);
    (2) khách đã nhắn tin MỚI hơn lượt bot vừa rep;
    (3) nhân viên đã nhắn sau lượt bot;
    (4) đã có 1 tin nhắn thêm kể từ tin khách cuối (tối đa 1/lượt).
    Nội dung do AI sinh từ lịch sử hội thoại + chỉ dẫn riêng; AI trả
    [BO_QUA]/rỗng/lỗi thì không gửi. Gửi qua _send_reply với
    la_tin_nhan_them=True (không tự lên lịch tiếp, không kèm sticker).
    """
    from ..database import SessionLocal
    db = SessionLocal()
    try:
        trace = str(uuid.uuid4())[:8]
        conv = db.get(Conversation, conversation_id)
        if not conv:
            return {"gui": False, "ly_do": "khong_tim_thay_hoi_thoai"}
        cust = db.get(Customer, conv.customer_id)
        if not cust:
            return {"gui": False, "ly_do": "khong_tim_thay_khach"}
        cai_dat = _doc_cai_dat(db)

        def _huy(ly_do):
            try:
                db.add(SystemLog(level="info", module="tin_nhan_them",
                                 message=f"huy_nhan_them conv={conv.id} sau_tin_bot={message_id_cua_luot_bot}: {ly_do}",
                                 trace_id=trace))
                db.commit()
            except Exception:
                db.rollback()
            return {"gui": False, "ly_do": ly_do}

        if not cai_dat.get("bot_tu_nhan_them"):
            return _huy("tinh_nang_da_tat")
        # (1) Tiếp quản / tạm dừng bot
        if not conv.bot_enabled or conv.human_takeover:
            return _huy("nhan_vien_tiep_quan_hoac_bot_tam_dung")
        tin_bot = db.get(Message, message_id_cua_luot_bot)
        if not tin_bot or tin_bot.conversation_id != conv.id:
            return _huy("khong_tim_thay_tin_bot")
        # (2) Khách đã nhắn tin mới hơn lượt bot
        if db.query(Message).filter(Message.conversation_id == conv.id,
                                    Message.sender_type == "khach",
                                    Message.id > tin_bot.id).first():
            return _huy("khach_da_nhan_tin_moi")
        # (3) Nhân viên đã nhắn sau lượt bot
        if db.query(Message).filter(Message.conversation_id == conv.id,
                                    Message.sender_type == "nhan_vien",
                                    Message.id > tin_bot.id).first():
            return _huy("nhan_vien_da_nhan_tin")
        # (4) Đã có tin nhắn thêm kể từ tin khách cuối
        tin_khach_cuoi = (db.query(Message)
                          .filter(Message.conversation_id == conv.id, Message.sender_type == "khach")
                          .order_by(Message.id.desc()).first())
        id_khach_cuoi = tin_khach_cuoi.id if tin_khach_cuoi else 0
        if id_khach_cuoi and _da_gui_nhan_them_cho(db, conv.id, id_khach_cuoi):
            return _huy("da_co_tin_nhan_them")
        # Sinh nội dung: lịch sử gần nhất + chỉ dẫn nhắn thêm riêng
        try:
            so_tin_ls = int(cai_dat.get("so_tin_nhan_ngu_canh") or 10)
        except (TypeError, ValueError):
            so_tin_ls = 10
        dong_ls = (db.query(Message)
                   .filter(Message.conversation_id == conv.id)
                   .order_by(Message.id.desc()).limit(max(1, so_tin_ls)).all())
        # Lọc tin sticker khỏi lịch sử (giống process_inbound): không cho AI
        # thấy marker "[sticker]" kẻo bắt chước viết vào câu trả lời.
        lich_su = [{"role": "user" if m.sender_type == "khach" else "assistant", "content": m.content}
                   for m in reversed(dong_ls)
                   if m.content and getattr(m, "attachment_type", "") != "sticker"
                   and not (m.sender_type == "bot" and (m.content or "").strip() == "[sticker]")]
        chi_dan = _CHI_DAN_NHAN_THEM
        if cai_dat.get("che_do_tro_chuyen_tu_do"):
            chi_dan += (" Đang ở chế độ trò chuyện tự do: nhắn như bạn bè thân thiết, "
                        "tự nhiên, vui vẻ, đúng chất chat giải trí.")
        provider = ai_gateway.get_default_provider(db)
        try:
            noi_dung, model_used = ai_gateway.generate_reply(
                db, provider, chi_dan, [], [], lich_su=lich_su, cai_dat=cai_dat,
                ho_so_khach=(cust.memory_summary or ""))
        except Exception as e:
            return _huy(f"loi_ai: {e}")
        noi_dung = (noi_dung or "").strip()
        if not noi_dung or noi_dung == "[BO_QUA]":
            return _huy("ai_bo_qua")
        # PHẦN F3: tin nhắn thêm cũng qua bộ lọc chống lặp câu — trùng với
        # câu bot đã gửi gần đây (toàn hệ thống) thì HỦY như các lý do hủy
        # khác, KHÔNG sinh lại (tin phụ không đáng tốn thêm lượt AI).
        if provider and provider.provider != "mock":
            cau_trung_nt = _tim_cau_trung(_chuan_hoa_cau(noi_dung), _cac_cau_bot_gan_day(db))
            if cau_trung_nt:
                try:
                    db.add(SystemLog(level="warning", module="chong_lap_cau",
                                     message=f"nhan_them_trung_cau conv={conv.id} cau_trung='{cau_trung_nt[:80]}'",
                                     trace_id=trace))
                    db.commit()
                except Exception:
                    db.rollback()
                return _huy("trung_cau_gan_day")
        ket_qua = _send_reply(db, conv, cust, noi_dung, trace, model_used=model_used,
                              channel="ca_nhan", cai_dat=cai_dat, tin_khach=None,
                              la_tin_nhan_them=True)
        if ket_qua.get("ly_do") == "cho_duyet_truoc_khi_gui":
            # Chế độ duyệt trước khi gửi: _send_reply chỉ tạo NHÁP như lượt
            # chính — không tính là đã gửi, không đánh dấu chống trùng.
            try:
                db.add(SystemLog(level="info", module="tin_nhan_them",
                                 message=f"nhan_them_thanh_nhap_cho_duyet conv={conv.id}",
                                 trace_id=trace))
                db.commit()
            except Exception:
                db.rollback()
            return {"gui": False, "ly_do": "cho_duyet_truoc_khi_gui"}
        if not ket_qua.get("tra_loi"):
            try:
                db.add(SystemLog(level="warning", module="tin_nhan_them",
                                 message=f"gui_nhan_them_that_bai conv={conv.id}: {ket_qua.get('ly_do')}",
                                 trace_id=trace))
                db.commit()
            except Exception:
                db.rollback()
            return {"gui": False, "ly_do": ket_qua.get("ly_do") or "gui_that_bai"}
        db.add(SystemLog(level="info", module="tin_nhan_them",
                         message=f"da_gui_nhan_them conv={conv.id} sau_khach={id_khach_cuoi} msg={ket_qua.get('tin_bot_id')}",
                         trace_id=trace))
        db.commit()
        return {"gui": True, "noi_dung": noi_dung, "conversation_id": conv.id}
    finally:
        db.close()


def _tin_khach(customer_external_id, external_id, cli_msg_id, la_nhom):
    return {"thread_id": str(customer_external_id), "external_id": str(external_id or ""),
            "cli_msg_id": str(cli_msg_id or ""), "loai_thread": 1 if la_nhom else 0}


def tinh_do_tre(text, cai_dat) -> int:
    """Độ trễ (mili-giây) trước khi gửi một phần tin theo chế độ tốc độ trả lời.

    Hàm THUẦN (không I/O) để kiểm thử đơn vị:
    - chế độ "ngay" -> 0 (gửi ngay, không hiện đang soạn tin).
    - "tu_nhien": len(text) * toc_do_go_ms_moi_ky_tu.
    - "cham": như tự nhiên nhưng nhân hệ số 2.
    Kết quả luôn kẹp trong [do_tre_tra_loi_toi_thieu_ms, do_tre_tra_loi_toi_da_ms].
    """
    cd = cai_dat or {}
    che_do = str(cd.get("che_do_toc_do_tra_loi") or "tu_nhien")
    if che_do == "ngay":
        return 0

    def _so(khoa, mac_dinh):
        try:
            return float(cd.get(khoa) or mac_dinh)
        except (TypeError, ValueError):
            return float(mac_dinh)

    ms_moi_ky_tu = _so("toc_do_go_ms_moi_ky_tu", 30)
    toi_thieu = _so("do_tre_tra_loi_toi_thieu_ms", 800)
    toi_da = max(toi_thieu, _so("do_tre_tra_loi_toi_da_ms", 6000))
    he_so = 2.0 if che_do == "cham" else 1.0
    tho = len(text or "") * ms_moi_ky_tu * he_so
    return int(min(max(tho, toi_thieu), toi_da))


def _doc_danh_sach_sticker(cai_dat, db=None, trace=""):
    """Đọc + chuẩn hoá cài đặt danh_sach_sticker (JSON mảng [{id, cate_id, type, nhan}]).
    JSON hỏng/không phải mảng -> trả [] và ghi log cảnh báo (bot bỏ qua sticker)."""
    tho = (cai_dat or {}).get("danh_sach_sticker")
    if not tho:
        return []
    try:
        ds = json.loads(tho) if isinstance(tho, str) else tho
    except (TypeError, ValueError):
        ds = None
    if not isinstance(ds, list):
        if db is not None:
            db.add(SystemLog(level="warning", module="sticker",
                             message="Cài đặt danh_sach_sticker không phải JSON mảng hợp lệ — bỏ qua gửi sticker",
                             trace_id=trace))
            db.commit()
        return []
    sach = []
    for x in ds:
        if isinstance(x, dict) and x.get("id"):
            sach.append({
                "id": x.get("id"),
                "cate_id": x.get("cate_id", x.get("cateId", 0)),
                "type": x.get("type", 1),
                "nhan": x.get("nhan", ""),
                "url_xem_truoc": x.get("url_xem_truoc") or x.get("url") or "",
            })
    return sach


def _duoc_gui_sticker(cai_dat, danh_sach) -> bool:
    """Tung xúc xắc theo xac_suat_gui_sticker (%) — tách riêng để kiểm thử
    monkeypatch được module random của orchestrator."""
    if not danh_sach:
        return False
    try:
        xac_suat = float((cai_dat or {}).get("xac_suat_gui_sticker") or 0)
    except (TypeError, ValueError):
        xac_suat = 0.0
    return random.random() * 100 < xac_suat


def _gui_sticker_neu_may(db, conv, cust, cai_dat, tin_khach, trace):
    """Gửi 1 sticker ngẫu nhiên SAU khi câu trả lời văn bản đã gửi xong.

    Chỉ được gọi từ _send_reply khi ít nhất 1 phần tin đã gửi thành công ở
    kênh ca_nhan (mọi cổng chặn — luật nhóm, bot tạm dừng, chuyển nhân viên —
    đều nằm TRƯỚC _send_reply nên sticker không bao giờ lọt qua các cổng đó).
    Lỗi gửi sticker chỉ ghi log, không làm hỏng câu trả lời.
    """
    try:
        if not cai_dat.get("bot_gui_sticker"):
            return
        ds = _doc_danh_sach_sticker(cai_dat, db, trace)
        if not _duoc_gui_sticker(cai_dat, ds):
            return
        sticker = random.choice(ds)
        loai_thread = tin_khach.get("loai_thread", 0) if tin_khach else 0
        try:
            ZaloPersonalConnector().send_sticker(str(cust.external_id), sticker, loai_thread)
        except Exception as e:
            db.add(SystemLog(level="warning", module="sticker",
                             message=f"Không gửi được sticker cho khách {cust.external_id}: {e}",
                             trace_id=trace))
            db.commit()
            return
        db.add(Message(conversation_id=conv.id, external_id=None, sender_type="bot",
                       content="[sticker]", status="da_gui", attachment_type="sticker",
                       attachment_url=json.dumps(sticker, ensure_ascii=False)))
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


def _send_reply(db, conv, cust, reply, trace, chunks=None, model_used="", rule=None, intent="", channel="mo_phong",
                cai_dat=None, tin_khach=None, la_tin_nhan_them: bool = False):
    cd = cai_dat if cai_dat is not None else _doc_cai_dat(db)
    # Mục 6: chuẩn hoá định dạng TRƯỚC khi gửi và trước khi lưu hiển thị.
    reply = dinh_dang_tin_zalo(reply or "")
    if not reply:
        return {"trung": False, "trace_id": trace, "tra_loi": None, "ly_do": "tra_loi_rong",
                "conversation_id": conv.id, "customer_id": cust.id}
    ket_qua_chung = {"trung": False, "trace_id": trace, "conversation_id": conv.id,
                     "customer_id": cust.id, "intent": intent, "nguon": chunks or [], "model": model_used}
    # Chế độ duyệt trước khi gửi: chỉ lưu bản nháp, không gửi thật.
    if cd.get("che_do_duyet_truoc_khi_gui"):
        db.add(Message(conversation_id=conv.id, external_id=None, sender_type="bot", content=reply, status="cho_duyet"))
        db.add(SystemLog(level="info", module="orchestrator", message=f"Câu trả lời hội thoại {conv.id} đang chờ duyệt trước khi gửi", trace_id=trace)); db.commit()
        return {**ket_qua_chung, "tra_loi": reply, "ly_do": "cho_duyet_truoc_khi_gui"}
    # Mục 4: thả tim tin khách trước khi trả lời (chỉ kênh cá nhân, đúng 1 lần/lượt).
    if tin_khach and cd.get("bot_tha_tim") and channel == "ca_nhan":
        try:
            ZaloPersonalConnector().tha_tim(tin_khach["thread_id"], tin_khach["external_id"],
                                            tin_khach.get("loai_thread", 0), tin_khach.get("cli_msg_id", ""))
        except Exception as e:
            db.add(SystemLog(level="warning", module="tha_tim", message=f"Không thả tim được cho tin {tin_khach.get('external_id')}: {e}", trace_id=trace)); db.commit()
    # Mục 5: chia nhỏ tin — áp dụng ở kênh cá nhân (bật/tắt + độ dài theo Cài đặt).
    # PHẦN A: truyền thêm ngưỡng MỀM do_dai_muc_tieu_moi_tin để chia TỰ NHIÊN
    # thành nhiều bong bóng ngắn theo câu, kể cả khi reply dưới ngưỡng cứng.
    cac_phan = [reply]
    if channel == "ca_nhan" and cd.get("gui_tin_chia_nho", True):
        try:
            do_dai = int(cd.get("do_dai_toi_da_moi_tin") or 350)
        except (TypeError, ValueError):
            do_dai = 350
        try:
            muc_tieu = int(cd.get("do_dai_muc_tieu_moi_tin") or 0)
        except (TypeError, ValueError):
            muc_tieu = 0
        cac_phan = chia_tin_nhan(reply, do_dai, muc_tieu) or [reply]
    try:
        do_tre_ms = int(os.getenv("GUI_TIN_DELAY_MS") or cd.get("do_tre_giua_cac_tin_ms") or 700)
    except (TypeError, ValueError):
        do_tre_ms = 700
    loi_cuoi = None
    so_phan_ok = 0
    tin_bot_cuoi = None  # Message bot gửi thành công gần nhất của lượt này (cho PHẦN C)
    # Tốc độ trả lời (theo Cài đặt): chế độ "ngay" = gửi ngay không typing;
    # "tu_nhien"/"cham" = hiện "đang soạn tin" (zca-js sendTypingEvent) rồi
    # chờ theo độ dài phần tin (tinh_do_tre) trước khi gửi — như người thật gõ.
    che_do_toc_do = str(cd.get("che_do_toc_do_tra_loi") or "tu_nhien")
    # Loại thread của đích gửi (0 = User 1-1, 1 = Group): lấy từ tin khách
    # đang xử lý. BẮT BUỘC truyền xuống send_text — nếu không, sidecar mặc
    # định User và tin rep trong NHÓM không bao giờ tới được nhóm (lỗi D).
    try:
        loai_gui = int(tin_khach.get("loai_thread") or 0) if tin_khach else 0
    except (TypeError, ValueError):
        loai_gui = 0
    for idx, phan in enumerate(cac_phan):
        if idx > 0 and do_tre_ms > 0:
            time.sleep(do_tre_ms / 1000.0)
        try:
            if channel == "ca_nhan":
                if che_do_toc_do != "ngay":
                    try:
                        ZaloPersonalConnector().typing(str(cust.external_id), 1 if (tin_khach and tin_khach.get("loai_thread")) else 0)
                    except Exception:
                        pass
                    tre = tinh_do_tre(phan, cd)
                    if idx > 0:
                        tre = max(0, tre - do_tre_ms)  # đã nghỉ do_tre_ms ở trên
                    if tre > 0:
                        time.sleep(tre / 1000.0)
                ZaloPersonalConnector().send_text(str(cust.external_id), phan, loai_gui)
            else:
                mock_connector.send_text(str(conv.id), phan)
            _tin_vua_gui = Message(conversation_id=conv.id, external_id=None, sender_type="bot", content=phan, status="da_gui")
            db.add(_tin_vua_gui)
            tin_bot_cuoi = _tin_vua_gui
            so_phan_ok += 1
        except Exception as e:
            loi_cuoi = e
            db.add(Message(conversation_id=conv.id, external_id=None, sender_type="bot", content=phan,
                           status="loi_gui", error=f"Phần {idx + 1}/{len(cac_phan)}: {e}"))
        db.commit()
    if so_phan_ok == 0:
        db.add(SystemLog(level="error", module="zalo", message=f"Lỗi gửi tin qua kênh {channel}: {loi_cuoi}", trace_id=trace)); db.commit()
        _thong_bao(db, "loi_he_thong", "Lỗi gửi tin qua connector", f"Gửi tin cho khách {cust.display_name or cust.external_id} qua kênh {channel} thất bại: {loi_cuoi}", cust, conv, "khan_cap", channel)
        return {**ket_qua_chung, "tra_loi": None, "ly_do": f"loi_connector: {loi_cuoi}"}
    id_tin_bot_cuoi = None
    if tin_bot_cuoi is not None:
        try:
            id_tin_bot_cuoi = tin_bot_cuoi.id
        except Exception:
            id_tin_bot_cuoi = None
    # Bot gửi sticker: chỉ kênh cá nhân, chỉ khi câu trả lời đã gửi thành công
    # (áp dụng cho cả chế độ tư vấn lẫn trò chuyện tự do vì cả hai đều qua đây).
    # Không cần typing cho sticker. Tin nhắn THÊM (PHẦN C) không kèm sticker
    # để tránh 2 sticker liền nhau.
    if channel == "ca_nhan" and not la_tin_nhan_them:
        _gui_sticker_neu_may(db, conv, cust, cd, tin_khach, trace)
    # PHẦN C: lên lịch tin nhắn thêm — chỉ chat 1-1 (tin_khach loai_thread=1
    # là NHÓM thì bỏ qua), chỉ khi lượt này không phải chính tin nhắn thêm
    # (chống đệ quy), và chỉ sau khi đã gửi thành công ít nhất 1 phần tin.
    # Chế độ duyệt trước khi gửi không tới được đây (đã return ở trên).
    if channel == "ca_nhan" and not la_tin_nhan_them and id_tin_bot_cuoi:
        if not (tin_khach and tin_khach.get("loai_thread")):
            _len_lich_tin_nhan_them(db, conv, cd, id_tin_bot_cuoi, trace)
    # Cập nhật bộ nhớ: ghi sự kiện tương tác. Đợt Hành vi nhóm (F2): lượt
    # NHÓM (tin_khach loai_thread=1) KHÔNG ghi sự kiện "Khách đã hỏi…" —
    # tránh nhồi sự kiện rác vào bộ nhớ nhóm (nhóm chỉ nhớ cốt lõi qua bản
    # tóm tắt riêng). Chat 1-1 giữ nguyên.
    if cd.get("module_bo_nho_ai", True) is not False and not (tin_khach and tin_khach.get("loai_thread")):
        memory_service.remember(db, cust.id, f"Khách đã hỏi và được trả lời: {reply[:120]}", memory_type="su_kien", source="orchestrator", confidence=0.7)
    db.add(SystemLog(level="info", module="orchestrator", message=f"Đã trả lời hội thoại {conv.id} model={model_used} so_phan_tin={len(cac_phan)}", trace_id=trace)); db.commit()
    return {**ket_qua_chung, "tra_loi": reply, "so_phan_tin": len(cac_phan), "tin_bot_id": id_tin_bot_cuoi}
