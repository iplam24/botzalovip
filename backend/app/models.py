"""Mô hình dữ liệu - các thực thể tối thiểu cho MVP."""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .database import Base

def now(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True); email = Column(String, unique=True, index=True, nullable=False)
    # Đợt nâng cấp 2: đăng nhập CHỈ bằng username (duy nhất). Cột mật khẩu vẫn
    # giữ trong DB (không kiểm tra khi đăng nhập nữa) để sau này bật lại được.
    username = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False); full_name = Column(String, default="")
    role = Column(String, default="NhanVien")  # QuanTriVienCaoNhat, QuanTriVien, QuanLy, NhanVien, ChiXem
    is_active = Column(Boolean, default=True); created_at = Column(DateTime, default=now)
    last_login_at = Column(DateTime, nullable=True)

class AIProviderConfig(Base):
    __tablename__ = "ai_providers"
    id = Column(Integer, primary_key=True); name = Column(String, nullable=False)
    provider = Column(String, default="mock")  # mock, openai_compatible
    base_url = Column(String, default=""); api_key_encrypted = Column(Text, default="")
    model = Column(String, default="mock-model"); embedding_model = Column(String, default="")
    max_tokens = Column(Integer, default=2000); timeout = Column(Integer, default=30)
    is_active = Column(Boolean, default=True); is_default = Column(Boolean, default=False)
    status = Column(String, default="chua_kiem_tra"); last_error = Column(Text, default="")
    created_at = Column(DateTime, default=now); updated_at = Column(DateTime, default=now, onupdate=now)

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True); external_id = Column(String, unique=True, index=True)
    display_name = Column(String, default=""); phone = Column(String, default=""); email = Column(String, default="")
    labels = Column(String, default="")  # phẩy phân cách
    group_name = Column(String, default=""); notes = Column(Text, default="")
    assignee = Column(String, default=""); last_interaction_at = Column(DateTime, default=now)
    created_at = Column(DateTime, default=now)
    # Hồ sơ tóm tắt dài hạn về khách (bot "nhớ cực lâu") — AI tóm tắt gộp định kỳ
    memory_summary = Column(Text, default="")

class ZaloAccount(Base):
    __tablename__ = "zalo_accounts"
    id = Column(Integer, primary_key=True); name = Column(String, default="")
    account_type = Column(String, default="mock")  # mock, oa, ca_nhan
    status = Column(String, default="chua_ket_noi")  # da_ket_noi, mat_ket_noi, chua_ket_noi, chua_ho_tro
    external_id = Column(String, default=""); last_connected_at = Column(DateTime, nullable=True)
    last_error = Column(Text, default=""); created_at = Column(DateTime, default=now)

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True); customer_id = Column(Integer, ForeignKey("customers.id"), index=True)
    zalo_account_id = Column(Integer, ForeignKey("zalo_accounts.id"), nullable=True)
    channel = Column(String, default="mo_phong")  # mo_phong | ca_nhan | oa - quyết định connector gửi thật
    status = Column(String, default="dang_xu_ly")  # dang_xu_ly, da_giai_quyet, cho_phan_hoi
    bot_enabled = Column(Boolean, default=True); human_takeover = Column(Boolean, default=False)
    requires_approval = Column(Boolean, default=False); labels = Column(String, default="")
    priority = Column(String, default="trung_binh"); assignee = Column(String, default="")
    created_at = Column(DateTime, default=now); updated_at = Column(DateTime, default=now, onupdate=now)
    customer = relationship("Customer"); messages = relationship("Message", back_populates="conversation")

class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("external_id", name="uq_message_external_id"),)
    id = Column(Integer, primary_key=True); conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True)
    external_id = Column(String, nullable=True, index=True)  # chống trùng
    sender_type = Column(String, default="khach")  # khach, bot, nhan_vien, he_thong
    content = Column(Text, default=""); status = Column(String, default="da_gui")
    error = Column(Text, default=""); created_at = Column(DateTime, default=now)
    conversation = relationship("Conversation", back_populates="messages")

class ServiceItem(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True); code = Column(String, unique=True, index=True)
    name = Column(String, nullable=False); description = Column(Text, default="")
    category = Column(String, default=""); price = Column(Float, default=0); price_text = Column(String, default="")
    policy = Column(Text, default=""); faq = Column(Text, default=""); keywords = Column(String, default="")
    is_active = Column(Boolean, default=True); version = Column(Integer, default=1)
    created_at = Column(DateTime, default=now); updated_at = Column(DateTime, default=now, onupdate=now)

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    id = Column(Integer, primary_key=True); title = Column(String, nullable=False)
    content = Column(Text, default=""); source_type = Column(String, default="van_ban")
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True)
    version = Column(Integer, default=1); is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True); created_at = Column(DateTime, default=now); updated_at = Column(DateTime, default=now, onupdate=now)
    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id = Column(Integer, primary_key=True); document_id = Column(Integer, ForeignKey("knowledge_documents.id"), index=True)
    content = Column(Text, default=""); normalized = Column(Text, default=""); chunk_index = Column(Integer, default=0)
    # Đợt 3 mục 3 (Vector DB): vector nhúng lưu dạng JSON text (list float) để
    # chạy được cả SQLite lẫn Postgres; tính cosine bằng Python (xem embedding_service)
    embedding = Column(Text, default="")
    document = relationship("KnowledgeDocument", back_populates="chunks")

class MemoryItem(Base):
    __tablename__ = "memories"
    id = Column(Integer, primary_key=True); customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    memory_type = Column(String, default="ngu_nghia")  # hoi_thoai, su_kien, ngu_nghia, nghiep_vu, quy_trinh, so_thich
    content = Column(Text, nullable=False); source = Column(String, default="he_thong")
    # Đợt 3 mục 3 (Vector DB): vector nhúng JSON text, tương tự knowledge_chunks
    embedding = Column(Text, default="")
    confidence = Column(Float, default=0.8); verified = Column(Boolean, default=False); pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now); updated_at = Column(DateTime, default=now, onupdate=now)

class AutomationRule(Base):
    __tablename__ = "automation_rules"
    id = Column(Integer, primary_key=True); name = Column(String, nullable=False); description = Column(Text, default="")
    condition_type = Column(String, default="chua_tu_khoa")  # chua_tu_khoa, intent, nhan
    condition_value = Column(String, default=""); action_type = Column(String, default="goi_ai")  # tra_loi, goi_ai, gan_nhan, chuyen_nhan_vien, tam_dung_bot
    action_value = Column(Text, default=""); priority = Column(Integer, default=10)
    is_active = Column(Boolean, default=True); created_at = Column(DateTime, default=now)

class RuleRun(Base):
    __tablename__ = "rule_runs"
    id = Column(Integer, primary_key=True); rule_id = Column(Integer, ForeignKey("automation_rules.id"))
    conversation_id = Column(Integer, nullable=True); result = Column(String, default=""); created_at = Column(DateTime, default=now)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True); job_type = Column(String, default=""); status = Column(String, default="cho")
    payload = Column(Text, default=""); error = Column(Text, default=""); retries = Column(Integer, default=0)
    created_at = Column(DateTime, default=now); finished_at = Column(DateTime, nullable=True)

class SystemLog(Base):
    __tablename__ = "system_logs"
    id = Column(Integer, primary_key=True); level = Column(String, default="info"); module = Column(String, default="")
    message = Column(Text, default=""); trace_id = Column(String, default=""); created_at = Column(DateTime, default=now)

class AIUsage(Base):
    __tablename__ = "ai_usages"
    id = Column(Integer, primary_key=True); provider_id = Column(Integer, nullable=True); model = Column(String, default="")
    prompt_tokens = Column(Integer, default=0); completion_tokens = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0); status = Column(String, default="thanh_cong"); error = Column(Text, default="")
    created_at = Column(DateTime, default=now)

class SystemSetting(Base):
    """Cài đặt hệ thống dạng khóa - giá trị (JSON), sửa được từ giao diện."""
    __tablename__ = "system_settings"
    key = Column(String, primary_key=True)
    value = Column(Text, default="")
    updated_at = Column(DateTime, default=now, onupdate=now)

class CollectedInfo(Base):
    """Thông tin khách hàng do bot tự thu thập từ hội thoại (GĐ mở rộng 1).

    Mỗi giá trị trích xuất được là một bản ghi riêng, có nguồn tin nhắn + độ
    tin cậy + trạng thái xác minh, không ghi đè im lặng lên hồ sơ khách.
    """
    __tablename__ = "thong_tin_thu_thap"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True, nullable=False)
    # ho_ten, so_dien_thoai, email, nhu_cau, dich_vu_quan_tam, ngan_sach,
    # thoi_gian_mong_muon, dia_chi, ghi_chu
    field = Column(String, nullable=False, index=True)
    value = Column(Text, default="")
    source_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    confidence = Column(Float, default=0.8)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now); updated_at = Column(DateTime, default=now, onupdate=now)
    customer = relationship("Customer")

class Notification(Base):
    """Thông báo cho quản trị viên (GĐ mở rộng 1): sự kiện nghiệp vụ quan trọng."""
    __tablename__ = "thong_bao"
    id = Column(Integer, primary_key=True)
    # khach_moi, co_so_dien_thoai, du_thong_tin, gap_nhan_vien, khieu_nai,
    # bot_khong_tra_loi_duoc, loi_he_thong
    type = Column(String, nullable=False, index=True)
    title = Column(String, default=""); content = Column(Text, default="")
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    level = Column(String, default="thong_tin")  # thong_tin, canh_bao, khan_cap
    is_read = Column(Boolean, default=False, index=True)
    sent_via_zalo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)

class PhanBoBanBe(Base):
    """Phân bổ bạn bè Zalo cho nhân viên phụ trách (Đợt nâng cấp 2, mục 9.5).

    Dữ liệu bạn bè được đồng bộ từ sidecar zca-js (getAllFriends thật).
    Đồng bộ chỉ upsert tên/avatar — KHÔNG xóa phân bổ admin đã gán.
    """
    __tablename__ = "phan_bo_ban_be"
    id = Column(Integer, primary_key=True)
    zalo_friend_id = Column(String, unique=True, index=True, nullable=False)
    ten_hien_thi = Column(String, default=""); avatar_url = Column(String, default="")
    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    ghi_chu = Column(Text, default="")
    created_at = Column(DateTime, default=now); updated_at = Column(DateTime, default=now, onupdate=now)
    admin = relationship("User")

class BackupRecord(Base):
    __tablename__ = "backups"
    id = Column(Integer, primary_key=True); filename = Column(String, default=""); path = Column(String, default="")
    size = Column(Integer, default=0); status = Column(String, default="thanh_cong"); created_at = Column(DateTime, default=now)
