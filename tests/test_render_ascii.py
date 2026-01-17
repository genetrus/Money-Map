from money_map.core.load import load_app_data
from money_map.render.ascii import render_full_ascii


def test_render_ascii_contains_key_parts() -> None:
    data = load_app_data()
    output = render_full_ascii(data)
    assert "Матрица" in output
    assert "A1" in output
    assert "Маршруты" in output
    assert "Мосты" in output
