from __future__ import annotations

import pytest


def test_wrap_label_limits_lines_and_not_empty() -> None:
    pytest.importorskip("streamlit")
    from money_map.ui.components import wrap_label

    text = "Очень длинное название механизма получения денег"
    result = wrap_label(text, max_chars_per_line=12, max_lines=3)

    assert result
    assert len(result.splitlines()) <= 3
