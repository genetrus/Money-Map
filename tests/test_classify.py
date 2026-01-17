from money_map.core.classify import classify_by_tags, classify_by_text
from money_map.core.load import load_app_data


def test_classify_by_tags() -> None:
    data = load_app_data()
    result = classify_by_tags(data, sell=["result"], to_whom=["platform"], value=["percent"])
    assert result.taxonomy_scores
    assert result.cell_scores


def test_classify_by_text() -> None:
    data = load_app_data()
    result = classify_by_text(data, "Я получаю процент с продаж на платформе")
    assert any(tag == "percent" for tag in result.tags["value"])
