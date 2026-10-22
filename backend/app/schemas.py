"""Schemas Pydantic v2."""
from pydantic import BaseModel
from typing import Optional, List

class LoginIn(BaseModel): email: str; password: str
class UserCreate(BaseModel): email: str; password: str; full_name: str = ""; role: str = "NhanVien"
class ProviderIn(BaseModel):
    name: str; provider: str = "mock"; base_url: str = ""; api_key: str = ""; model: str = "mock-model"
    embedding_model: str = ""; max_tokens: int = 2000; timeout: int = 30; is_active: bool = True; is_default: bool = False
class ProviderUpdate(BaseModel):
    name: Optional[str] = None; provider: Optional[str] = None; base_url: Optional[str] = None; api_key: Optional[str] = None
    model: Optional[str] = None; embedding_model: Optional[str] = None; max_tokens: Optional[int] = None; timeout: Optional[int] = None
    is_active: Optional[bool] = None; is_default: Optional[bool] = None
class CustomerIn(BaseModel): external_id: Optional[str] = None; display_name: str = ""; phone: str = ""; email: str = ""; labels: str = ""; group_name: str = ""; notes: str = ""; assignee: str = ""
class CollectedInfoIn(BaseModel): field: str; value: str; verified: bool = False
class CollectedInfoUpdate(BaseModel): value: Optional[str] = None; verified: Optional[bool] = None
class ServiceIn(BaseModel): code: Optional[str] = None; name: str; description: str = ""; category: str = ""; price: float = 0; price_text: str = ""; policy: str = ""; faq: str = ""; keywords: str = ""; is_active: bool = True
class KnowledgeIn(BaseModel): title: str; content: str; source_type: str = "van_ban"; service_id: Optional[int] = None
class MemoryIn(BaseModel): customer_id: Optional[int] = None; memory_type: str = "ngu_nghia"; content: str; source: str = "nhap_tay"; confidence: float = 0.9; verified: bool = False; pinned: bool = False
class MemoryUpdate(BaseModel): content: Optional[str] = None; memory_type: Optional[str] = None; confidence: Optional[float] = None; verified: Optional[bool] = None; pinned: Optional[bool] = None
class RuleIn(BaseModel): name: str; description: str = ""; condition_type: str = "chua_tu_khoa"; condition_value: str = ""; action_type: str = "goi_ai"; action_value: str = ""; priority: int = 10; is_active: bool = True
class InboundIn(BaseModel): external_id: str; customer_external_id: str = "mock-khach-1"; customer_name: str = "Khách mô phỏng"; content: str; zalo_account_id: Optional[int] = None
class SendMessageIn(BaseModel): content: str; sender_type: str = "nhan_vien"
class AITestIn(BaseModel): question: str; provider_id: Optional[int] = None; service_id: Optional[int] = None
class RetrieveIn(BaseModel): query: str; limit: int = 5
