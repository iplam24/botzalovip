"""Bộ nhớ dài hạn: lưu, chống trùng, truy xuất theo khách hàng và từ khóa.

Bổ sung: HỒ SƠ TÓM TẮT DÀI HẠN theo khách (customers.memory_summary) — sau mỗi
N tin nhắn của khách (cài đặt bo_nho_tom_tat_sau_bao_nhieu_tin, mặc định 6),
hệ thống tóm tắt gộp (hồ sơ cũ + tin mới) thành một hồ sơ ngắn và tiêm vào
mọi lượt trả lời tư vấn để bot "nhớ" khách. Mốc đã tóm tắt tới đâu được lưu
bằng SystemLog module "bo_nho" dạng "tom_tat cust=<id> msg=<message_id>".
"""
from sqlalchemy.orm import Session
from ..models import MemoryItem, Message, SystemLog, CollectedInfo, Conversation
from .text_utils import normalize_vi

def _nhung_cho_muc(db: Session, item):
    """Nhúng vector cho một ký ức (nếu nguồn sẵn sàng); lỗi thì bỏ qua êm."""
    try:
        from . import embedding_service
        vec = embedding_service.nhung_mot(db, item.content)
        if vec:
            item.embedding = embedding_service.ghi_vector(vec)
            db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


def remember(db: Session, customer_id, content, memory_type="ngu_nghia", source="he_thong", confidence=0.8):
    # Chống trùng: cùng khách + cùng nội dung chuẩn hóa
    existing = db.query(MemoryItem).filter(MemoryItem.customer_id == customer_id).all()
    for m in existing:
        if normalize_vi(m.content) == normalize_vi(content): return m, False
    item = MemoryItem(customer_id=customer_id, content=content, memory_type=memory_type, source=source, confidence=confidence)
    db.add(item); db.commit(); db.refresh(item)
    # Đợt 3 mục 3: nhúng vector ngay khi tạo ký ức (nguồn chưa sẵn sàng -> bỏ qua)
    _nhung_cho_muc(db, item)
    return item, True

def retrieve_memories(db: Session, customer_id, query="", limit=5):
    q = db.query(MemoryItem)
    if customer_id: q = q.filter(MemoryItem.customer_id == customer_id)
    items = q.order_by(MemoryItem.pinned.desc(), MemoryItem.created_at.desc()).all()
    if query:
        nq = normalize_vi(query); items = sorted(items, key=lambda m: -sum(1 for w in nq.split() if w in normalize_vi(m.content)))
    ket_qua = items[:limit]
    # Đợt 3 mục 3: bổ sung ký ức khớp NGỮ NGHĨA (cosine) ngoài danh sách từ khóa
    if query:
        try:
            from ..routers.cai_dat import doc_cai_dat
            from . import embedding_service
            if doc_cai_dat(db).get("tim_kiem_ngu_nghia", True):
                qv = embedding_service.nhung_mot(db, query)
                if qv:
                    da_co = {id(m) for m in ket_qua}
                    ung_vien = []
                    for m in items:
                        if id(m) in da_co:
                            continue
                        vec = embedding_service.doc_vector(m.embedding)
                        if vec and embedding_service.cosine(qv, vec) >= 0.3:
                            ung_vien.append((embedding_service.cosine(qv, vec), m))
                    ung_vien.sort(key=lambda x: -x[0])
                    ket_qua = ket_qua + [m for _, m in ung_vien]
        except Exception:
            pass
    return ket_qua


def trang_thai_vector(db: Session) -> dict:
    """Trạng thái nhúng của bộ nhớ AI: nguồn + đã nhúng/tổng số ký ức."""
    from . import embedding_service
    gia_tri = [h[0] for h in db.query(MemoryItem.embedding).all()]
    da = sum(1 for v in gia_tri if v)
    tt = embedding_service.nguon_hien_tai(db)
    return {"tong_muc": len(gia_tri), "da_nhung": da, "chua_nhung": len(gia_tri) - da,
            "nguon": tt["nguon"], "san_sang": tt["san_sang"], "mo_ta": tt["mo_ta"]}


def nhung_lai_tat_ca(db: Session) -> dict:
    """Nhúng (lại) vector cho mọi ký ức; nguồn chưa sẵn sàng -> không ghi gì."""
    from . import embedding_service
    items = db.query(MemoryItem).all()
    vectors = embedding_service.nhung_nhieu(db, [m.content for m in items]) if items else []
    if vectors:
        for m, vec in zip(items, vectors):
            m.embedding = embedding_service.ghi_vector(vec)
        db.commit()
    return trang_thai_vector(db)


# ---- Hồ sơ tóm tắt dài hạn theo khách ----
def _moc_da_tom_tat(db: Session, customer_id) -> int:
    """ID tin nhắn khách gần nhất đã được gộp vào hồ sơ tóm tắt (0 nếu chưa)."""
    dong = (db.query(SystemLog)
            .filter(SystemLog.module == "bo_nho",
                    SystemLog.message.like(f"tom_tat cust={customer_id} msg=%"))
            .order_by(SystemLog.id.desc()).first())
    if not dong:
        return 0
    try:
        return int(str(dong.message).rsplit("msg=", 1)[1])
    except Exception:
        return 0


def _tom_tat_quy_tac(db: Session, customer, tin_moi, la_nhom: bool = False) -> str:
    """Tóm tắt bằng quy tắc (dùng khi provider là Mock/mô phỏng): dựng hồ sơ từ
    thông tin đã thu thập + hồ sơ khách + vài tin gần nhất — không để trống.

    Lượt NHÓM (la_nhom=True, đợt Hành vi nhóm F2): bản quy tắc cũng chỉ giữ
    CỐT LÕI CẤP NHÓM — bỏ hẳn SĐT + thông tin thu thập cá nhân, chỉ nêu tên
    nhóm + vài trao đổi chung gần nhất kèm tên người nói."""
    if la_nhom:
        cac_phan = []
        if (customer.display_name or "").strip():
            cac_phan.append(f"Nhóm {customer.display_name.strip()}")
        if tin_moi:
            cac_phan.append("Trao đổi gần đây trong nhóm: " + "; ".join(
                f'{(getattr(m, "sender_name", "") or "Thành viên")}: "{(m.content or "")[:60]}"'
                for m in tin_moi[-3:]))
        if not cac_phan:
            return ""
        return ". ".join(cac_phan) + "."
    cac_phan = []
    if (customer.display_name or "").strip():
        cac_phan.append(f"Khách {customer.display_name.strip()}")
    if (customer.phone or "").strip():
        cac_phan.append(f"SĐT {customer.phone.strip()}")
    thu_thap = {}
    for t in (db.query(CollectedInfo)
              .filter(CollectedInfo.customer_id == customer.id)
              .order_by(CollectedInfo.id.desc()).all()):
        thu_thap.setdefault(t.field, t.value)
    nhan_truong = {"nhu_cau": "Nhu cầu", "dich_vu_quan_tam": "Quan tâm",
                   "ngan_sach": "Ngân sách", "thoi_gian_mong_muon": "Thời gian mong muốn",
                   "dia_chi": "Địa chỉ/khu vực", "email": "Email"}
    for truong, nhan in nhan_truong.items():
        if thu_thap.get(truong):
            cac_phan.append(f"{nhan}: {thu_thap[truong]}")
    if tin_moi:
        cac_phan.append("Gần đây khách trao đổi: " + "; ".join(
            f'"{(m.content or "")[:60]}"' for m in tin_moi[-3:]))
    if not cac_phan:
        return ""
    return ". ".join(cac_phan) + "."


def _tom_tat_bang_ai(db: Session, provider, customer, tom_tat_cu: str, tin_moi, la_nhom: bool = False) -> str:
    """Gọi provider AI thật để tóm tắt gộp hồ sơ cũ + tin mới. Lỗi thì ném ra
    để hàm gọi quyết định bỏ qua (không chặn pipeline trả lời khách).

    Lượt NHÓM (la_nhom=True, đợt Hành vi nhóm F2): dùng chỉ dẫn RIÊNG cho
    nhóm — chỉ giữ thông tin CỐT LÕI CẤP NHÓM, tuyệt đối không ghi thông
    tin cá nhân của từng thành viên."""
    from . import ai_gateway
    from ..security import decrypt_secret
    from ..models import AIUsage
    key = decrypt_secret(provider.api_key_encrypted)
    if not key or not provider.base_url:
        raise ai_gateway.AIError("Chưa cấu hình khóa API/địa chỉ API để tóm tắt bộ nhớ")
    if la_nhom:
        transcript = "\n".join(
            f"{(getattr(m, 'sender_name', '') or 'Thành viên')}: {m.content}" for m in tin_moi if m.content)
        noi_dung = (
            f"Bản tóm tắt cốt lõi hiện tại của NHÓM:\n{tom_tat_cu or '(chưa có)'}\n\n"
            f"Tin nhắn mới trong nhóm:\n{transcript}\n\n"
            "Hãy viết BẢN TÓM TẮT CỐT LÕI MỚI CỦA NHÓM (gộp bản cũ với tin mới, bỏ trùng lặp), tối đa khoảng 120 từ, "
            "CHỈ gồm thông tin cốt lõi CẤP NHÓM: nhóm này là nhóm gì/chủ đề chính, luật lệ hoặc thỏa thuận chung "
            "được nhắc trong nhóm, quyết định/thông tin chung quan trọng. "
            "TUYỆT ĐỐI KHÔNG ghi thông tin cá nhân của từng thành viên (tên riêng kèm số điện thoại, nhu cầu mua "
            "hàng cá nhân, chuyện riêng tư). Chỉ viết đúng bản tóm tắt, không giải thích, không chào hỏi."
        )
        he_thong = ("Bạn là hệ thống ghi nhớ thông tin cốt lõi của nhóm chat. Chỉ ghi thông tin cấp nhóm, "
                    "tuyệt đối không ghi thông tin cá nhân của từng thành viên, chỉ dựa trên dữ kiện được "
                    "cung cấp, tuyệt đối không bịa thêm.")
    else:
        transcript = "\n".join(f"Khách: {m.content}" for m in tin_moi if m.content)
        noi_dung = (
            f"Hồ sơ tóm tắt hiện tại:\n{tom_tat_cu or '(chưa có)'}\n\n"
            f"Tin nhắn mới của khách:\n{transcript}\n\n"
            "Hãy viết HỒ SƠ TÓM TẮT MỚI (gộp hồ sơ cũ với tin mới, bỏ trùng lặp), tối đa khoảng 120 từ, gồm: "
            "định danh/tên nếu biết, nhu cầu và sở thích, đã hỏi/mua những gì, điểm cần lưu ý, việc đang dang dở. "
            "Chỉ viết đúng hồ sơ, không giải thích, không chào hỏi."
        )
        he_thong = "Bạn là hệ thống ghi nhớ khách hàng. Viết hồ sơ tóm tắt ngắn gọn, chính xác, chỉ dựa trên dữ kiện được cung cấp, tuyệt đối không bịa thêm."
    payload = {"model": provider.model, "stream": False, "temperature": 0.3, "max_tokens": 500,
               "messages": [
                   {"role": "system", "content": he_thong},
                   {"role": "user", "content": noi_dung}]}
    with ai_gateway.http_client(timeout=provider.timeout or 30) as client:
        r = client.post(f"{provider.base_url.rstrip('/')}/chat/completions",
                        headers={"Authorization": f"Bearer {key}"}, json=payload)
        if r.status_code >= 400:
            raise ai_gateway.AIError(f"Provider trả lỗi {r.status_code} khi tóm tắt bộ nhớ")
        parsed = ai_gateway.parse_chat_response(r.text, r.headers.get("content-type", ""))
    text = (parsed.get("content") or "").strip()
    if not text:
        raise ai_gateway.AIError("Provider trả nội dung rỗng khi tóm tắt bộ nhớ")
    usage = parsed.get("usage") or {}
    db.add(AIUsage(provider_id=provider.id, model=parsed.get("model") or provider.model,
                   prompt_tokens=usage.get("prompt_tokens", 0) or 0,
                   completion_tokens=usage.get("completion_tokens", 0) or 0, status="thanh_cong"))
    db.commit()
    return text


def cap_nhat_tom_tat_bo_nho(db: Session, customer, cai_dat: dict = None, force: bool = False, la_nhom: bool = False):
    """Tóm tắt gộp hồ sơ dài hạn cho khách khi đủ số tin mới (hoặc force=True).

    Trả về hồ sơ mới nếu đã tóm tắt, None nếu chưa đủ tin / lỗi AI (bỏ qua,
    mốc không đổi nên lần xử lý sau đủ tin sẽ thử lại). KHÔNG ném lỗi ra ngoài.
    """
    try:
        cd = cai_dat
        if cd is None:
            from ..routers.cai_dat import doc_cai_dat
            cd = doc_cai_dat(db)
        try:
            nguong = int(cd.get("bo_nho_tom_tat_sau_bao_nhieu_tin") or 6)
        except (TypeError, ValueError):
            nguong = 6
        moc = _moc_da_tom_tat(db, customer.id)
        conv_ids = [c.id for c in db.query(Conversation).filter(Conversation.customer_id == customer.id).all()]
        if not conv_ids:
            return None
        tin_moi = (db.query(Message)
                   .filter(Message.conversation_id.in_(conv_ids),
                           Message.sender_type == "khach", Message.id > moc)
                   .order_by(Message.id).all())
        if force and not tin_moi:
            # Tóm tắt tay khi chưa có tin mới: dùng 10 tin khách gần nhất làm ngữ cảnh
            tin_moi = (db.query(Message)
                       .filter(Message.conversation_id.in_(conv_ids), Message.sender_type == "khach")
                       .order_by(Message.id.desc()).limit(10).all())
            tin_moi = list(reversed(tin_moi))
        if not tin_moi:
            return None
        if not force and len(tin_moi) < max(1, nguong):
            return None
        from . import ai_gateway
        provider = ai_gateway.get_default_provider(db)
        if provider and provider.provider != "mock":
            try:
                tom_tat = _tom_tat_bang_ai(db, provider, customer, customer.memory_summary or "", tin_moi, la_nhom=la_nhom)
            except Exception as e:
                db.add(SystemLog(level="warning", module="bo_nho",
                                 message=f"Tóm tắt bộ nhớ bằng AI thất bại cho khách {customer.id}: {e}"))
                db.commit()
                return None
        else:
            tom_tat = _tom_tat_quy_tac(db, customer, tin_moi, la_nhom=la_nhom)
        if not tom_tat:
            return None
        customer.memory_summary = tom_tat
        db.add(SystemLog(level="info", module="bo_nho",
                         message=f"tom_tat cust={customer.id} msg={tin_moi[-1].id}"))
        db.commit()
        return tom_tat
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return None
