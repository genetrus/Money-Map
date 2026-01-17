from __future__ import annotations

import importlib.util
from pathlib import Path

from money_map.app.cli import build_streamlit_command


def test_build_streamlit_command_uses_app_path() -> None:
    spec = importlib.util.find_spec("money_map.ui.app")
    assert spec is not None
    assert spec.origin is not None

    app_path = Path(spec.origin)
    command = build_streamlit_command(app_path)

    assert command[1:4] == ["-m", "streamlit", "run"]
    assert command[-1].endswith("app.py")
