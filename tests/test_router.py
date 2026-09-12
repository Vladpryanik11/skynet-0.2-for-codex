from institute.router import keyword_fallback


def test_keyword_fallback_routes_coders_request():
    assert keyword_fallback("сделай python агента для telegram бота") == "coders"


def test_keyword_fallback_routes_marketing_request():
    assert keyword_fallback("напиши рекламный пост и оффер") == "marketing"


def test_keyword_fallback_routes_design_request():
    assert keyword_fallback("создай дизайн лендинга по референсам") == "design"


def test_keyword_fallback_returns_none_for_unclear_request():
    assert keyword_fallback("привет как дела") is None
