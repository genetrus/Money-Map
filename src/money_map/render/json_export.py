from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from money_map.core.model import AppData


def render_index_json(data: AppData) -> str:
    payload: Dict[str, Any] = {
        "axes": [axis.model_dump() for axis in data.axes],
        "cells": [cell.model_dump() for cell in data.cells],
        "taxonomy": [item.model_dump() for item in data.taxonomy],
        "mappings": data.mappings.model_dump(),
        "paths": [path.model_dump() for path in data.paths],
        "bridges": [bridge.model_dump(by_alias=True) for bridge in data.bridges],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_index_json(data: AppData, path: Path) -> None:
    path.write_text(render_index_json(data), encoding="utf-8")
