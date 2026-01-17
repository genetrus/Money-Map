from __future__ import annotations


def test_ui_module_import() -> None:
    import money_map.ui as ui

    assert hasattr(ui, "__version__")
