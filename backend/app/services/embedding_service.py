"""Dịch vụ nhúng văn bản (embedding) cho Vector DB — Đợt nâng cấp 3, mục 3.

Thiết kế (ưu tiên đơn giản + đúng + kiểm thử được):
- Vector được lưu dạng JSON text (list[float]) ngay trên knowledge_chunks và
  memories, tính độ tương đồng cosine bằng Python thuần. Quy mô dữ liệu vừa
  (nghìn–chục nghìn đoạn) chạy tốt, và chạy được cả trên SQLite (bản kiểm thử)
  lẫn Postgres (bản thật). Trên Postgres hệ thống còn thử bật extension
  pgvector lúc khởi động để sẵn sàng nâng cấp (xem BAO_CAO_NGHIEM_THU.md).

Thứ tự chọn nguồn nhúng:
1) EMBEDDING_FAKE=1 (chỉ dùng cho kiểm thử/hồ sơ demo): vector deterministic
   sinh từ hash bag-of-words — cùng một câu luôn cho cùng một vector.
2) Nhà cung cấp AI mặc định có embedding_model + base_url + khóa API:
   gọi POST {base_url}/embeddings tương thích OpenAI.
3) fastembed cài local (model paraphrase-multilingual-MiniLM-L12-v2) — import
   an toàn: chưa cài/chưa tải được model thì coi như chưa sẵn sàng.
Không có nguồn nào -> trả None; tầng truy hồi tự rơi về tìm từ khóa như cũ.
TUYỆT ĐỐI không làm sập ứng dụng và không giả vờ đã nhúng khi chưa nhúng.
"""
import hashlib
import importlib.util
import json
import math
import os
from .text_utils import normalize_vi

CHIEU_FAKE = 128
TEN_MODEL_LOCAL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_model_local = None
_model_local_loi = False


def _vector_fake(text: str) -> list:
    """Vector deterministic từ hash bag-of-words (CHỈ cho kiểm thử).

    Mỗi từ (đã bỏ dấu) cộng 1.0 vào một 'ô' do sha256 quyết định; cuối cùng
    chuẩn hoá L2. Văn bản giống nhau -> vector y hệt; văn bản trùng nhiều từ
    -> cosine cao. Đủ để kiểm chứng cơ chế nhúng + truy hồi."""
    vec = [0.0] * CHIEU_FAKE
    for tu in normalize_vi(text).split():
        h = hashlib.sha256(tu.encode("utf-8")).digest()
        vec[int.from_bytes(h[:2], "little") % CHIEU_FAKE] += 1.0
    return _chuan_hoa_l2(vec)


def _chuan_hoa_l2(vec: list) -> list:
    do_dai = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / do_dai for x in vec]


def cosine(a, b) -> float:
    """Độ tương đồng cosine giữa 2 vector (chấp nhận list hoặc chuỗi JSON)."""
    va, vb = doc_vector(a), doc_vector(b)
    if not va or not vb:
        return 0.0
    n = min(len(va), len(vb))
    return sum(va[i] * vb[i] for i in range(n))


def doc_vector(gia_tri):
    """Đọc vector từ giá trị lưu trong DB (chuỗi JSON) hoặc list sẵn có."""
    if not gia_tri:
        return None
    if isinstance(gia_tri, (list, tuple)):
        return [float(x) for x in gia_tri] or None
    try:
        v = json.loads(gia_tri)
        return [float(x) for x in v] if isinstance(v, list) and v else None
    except Exception:
        return None


def ghi_vector(vec) -> str:
    return json.dumps([float(x) for x in vec]) if vec else ""


def _co_fastembed() -> bool:
    try:
        return importlib.util.find_spec("fastembed") is not None
    except Exception:
        return False


def _lay_model_local():
    """Nạp lười model fastembed local; lỗi (chưa cài/chưa tải) -> None."""
    global _model_local, _model_local_loi
    if _model_local is not None:
        return _model_local
    if _model_local_loi:
        return None
    try:
        from fastembed import TextEmbedding
        _model_local = TextEmbedding(model_name=TEN_MODEL_LOCAL)
    except Exception:
        _model_local_loi = True
        return None
    return _model_local


def nguon_hien_tai(db=None) -> dict:
    """Trạng thái nguồn nhúng hiện tại (để hiển thị UI + endpoint trạng thái).

    san_sang=False nghĩa là hệ thống đang rơi về tìm từ khóa — hiển thị trung
    thực, không giả vờ đã nhúng."""
    if os.getenv("EMBEDDING_FAKE") == "1":
        return {"nguon": "fake", "san_sang": True,
                "mo_ta": "Vector giả deterministic (chế độ kiểm thử EMBEDDING_FAKE=1)"}
    if db is not None:
        try:
            from . import ai_gateway
            p = ai_gateway.get_default_provider(db)
            if p and getattr(p, "embedding_model", "") and p.base_url:
                return {"nguon": "provider", "san_sang": True,
                        "mo_ta": f"API /embeddings của nhà cung cấp mặc định, model {p.embedding_model}"}
        except Exception:
            pass
    if _co_fastembed():
        return {"nguon": "local", "san_sang": True,
                "mo_ta": f"fastembed local: {TEN_MODEL_LOCAL} (tải model ở lần nhúng đầu tiên)"}
    return {"nguon": "chua_san_sang", "san_sang": False,
            "mo_ta": "Chưa có nguồn nhúng: hãy đặt embedding_model cho nhà cung cấp AI mặc định "
                     "hoặc cài gói fastembed. Hệ thống tạm tìm theo từ khóa."}


def _nhung_qua_provider(db, texts: list):
    from . import ai_gateway
    from ..security import decrypt_secret
    p = ai_gateway.get_default_provider(db)
    if not p or not getattr(p, "embedding_model", "") or not p.base_url:
        return None
    key = decrypt_secret(p.api_key_encrypted)
    if not key:
        return None
    try:
        with ai_gateway.http_client(timeout=p.timeout or 30) as client:
            r = client.post(f"{p.base_url.rstrip('/')}/embeddings",
                            headers={"Authorization": f"Bearer {key}"},
                            json={"model": p.embedding_model, "input": texts})
            if r.status_code >= 400:
                return None
            data = r.json()
        muc = sorted(data.get("data", []), key=lambda d: d.get("index", 0))
        vectors = [d.get("embedding") for d in muc]
        if len(vectors) != len(texts) or any(not v for v in vectors):
            return None
        return [[float(x) for x in v] for v in vectors]
    except Exception:
        return None


def nhung_nhieu(db, texts: list):
    """Nhúng nhiều văn bản. Trả list vector tương ứng, hoặc None nếu chưa có
    nguồn nhúng sẵn sàng (người gọi phải xử lý: bỏ qua, rơi về từ khóa)."""
    texts = [t or "" for t in texts]
    if not texts:
        return []
    if os.getenv("EMBEDDING_FAKE") == "1":
        return [_vector_fake(t) for t in texts]
    vectors = _nhung_qua_provider(db, texts)
    if vectors is not None:
        return vectors
    model = _lay_model_local()
    if model is not None:
        try:
            return [[float(x) for x in v] for v in model.embed(texts)]
        except Exception:
            return None
    return None


def nhung_mot(db, text: str):
    """Nhúng một văn bản; None nếu chưa sẵn sàng."""
    ket_qua = nhung_nhieu(db, [text])
    return ket_qua[0] if ket_qua else None


# Tên gọi thân thiện dùng trong các module khác
embed_mot = nhung_mot
embed_nhieu = nhung_nhieu
trang_thai = nguon_hien_tai
