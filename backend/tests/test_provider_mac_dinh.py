"""Chống tái diễn sự cố 23/10/2026: hai provider cùng is_default (kể cả Mock)
khiến get_default_provider vớ phải Mock -> bot trả lời bằng câu mẫu mô phỏng
trên môi trường thật. Provider THẬT luôn phải thắng Mock.
"""
from app.database import SessionLocal
from app.models import AIProviderConfig
from app.services.ai_gateway import get_default_provider


def _tao(db, name, provider, is_default, is_active=True):
    p = AIProviderConfig(name=name, provider=provider, model=f"{provider}-model",
                         api_key_encrypted="", is_default=is_default, is_active=is_active,
                         status="da_ket_noi")
    db.add(p); db.commit(); db.refresh(p)
    return p


def test_107_mac_dinh_that_thang_mock_khi_ca_hai_mac_dinh():
    db = SessionLocal()
    try:
        mock_p = _tao(db, "Mock test 107", "mock", True)
        that_p = _tao(db, "That test 107", "openai_compatible", True)
        chon = get_default_provider(db)
        assert chon is not None and chon.id == that_p.id and chon.provider != "mock"
    finally:
        db.query(AIProviderConfig).filter(AIProviderConfig.name.like("%test 107")).delete(synchronize_session=False)
        db.commit(); db.close()


def test_108_mock_mac_dinh_duy_nhat_duoc_ton_trong():
    # Sửa semantics (23/10, bản vá sự cố Mock đầu viết quá tay): Mock là mặc
    # định DUY NHẤT = lựa chọn tường minh của admin → phải được tôn trọng dù
    # có provider thật đang bật nhưng KHÔNG phải mặc định. Bản cũ ghi đè mặc
    # định này nên các luồng dùng Mock mặc định (test_90...) sập vì provider
    # thật seed chưa cấu hình khóa API. Sự cố gốc (2 mặc định) do test_107 giữ.
    db = SessionLocal()
    cu = {}
    try:
        cu = {p.id: p.is_default for p in db.query(AIProviderConfig).all()}
        db.query(AIProviderConfig).update({AIProviderConfig.is_default: False}); db.commit()
        mock_p = _tao(db, "Mock test 108", "mock", True)
        _tao(db, "That test 108", "openai_compatible", False)
        chon = get_default_provider(db)
        assert chon is not None and chon.id == mock_p.id
    finally:
        db.query(AIProviderConfig).filter(AIProviderConfig.name.like("%test 108")).delete(synchronize_session=False)
        for pid, md in cu.items():
            db.query(AIProviderConfig).filter(AIProviderConfig.id == pid).update({AIProviderConfig.is_default: md})
        db.commit(); db.close()
