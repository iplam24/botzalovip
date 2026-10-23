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


def test_108_chi_mock_mac_dinh_va_co_that_dang_bat_thi_chon_that():
    # DB test dùng chung có sẵn provider thật khác (seed) nên không khẳng
    # định id cụ thể — tính chất cần giữ: provider được chọn KHÔNG BAO GIỜ
    # là Mock khi còn bất kỳ provider thật nào đang bật.
    db = SessionLocal()
    try:
        _tao(db, "Mock test 108", "mock", True)
        _tao(db, "That test 108", "openai_compatible", False)
        chon = get_default_provider(db)
        assert chon is not None and chon.provider != "mock" and chon.is_active
    finally:
        db.query(AIProviderConfig).filter(AIProviderConfig.name.like("%test 108")).delete(synchronize_session=False)
        db.commit(); db.close()
