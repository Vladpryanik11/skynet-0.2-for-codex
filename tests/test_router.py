import pytest

from institute.router import keyword_fallback, normalize_department_override


def test_keyword_fallback_routes_coders_request():
    assert keyword_fallback("сделай python агента для telegram бота") == "coders"


def test_keyword_fallback_routes_marketing_request():
    assert keyword_fallback("напиши рекламный пост и оффер") == "marketing"


def test_keyword_fallback_routes_design_request():
    assert keyword_fallback("создай дизайн лендинга по референсам") == "design"


def test_keyword_fallback_returns_none_for_unclear_request():
    assert keyword_fallback("привет как дела") is None


def test_normalize_department_override_accepts_known_department():
    assert normalize_department_override(" Marketing ") == "marketing"


def test_normalize_department_override_rejects_unknown_department():
    with pytest.raises(ValueError):
        normalize_department_override("sales")
