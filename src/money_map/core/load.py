from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml

from money_map.core.model import (
    AppData,
    Axis,
    BridgeItem,
    Cell,
    DiagramConfig,
    Keywords,
    Mappings,
    PathItem,
    TaxonomyItem,
)

DATA_FILES = {
    "axes": "axes.yaml",
    "cells": "cells.yaml",
    "taxonomy": "taxonomy.yaml",
    "mappings": "mappings.yaml",
    "paths": "paths.yaml",
    "bridges": "bridges.yaml",
    "diagrams": "diagrams.yaml",
    "keywords": "keywords.yaml",
}


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _data_dir() -> Path:
    override = os.environ.get("MONEY_MAP_DATA_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[3] / "data"


def load_app_data() -> AppData:
    data_dir = _data_dir()
    raw: Dict[str, Dict[str, Any]] = {}
    for key, filename in DATA_FILES.items():
        path = data_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Не найден файл данных: {path}")
        raw[key] = _load_yaml(path)

    return AppData(
        axes=[Axis(**item) for item in raw["axes"].get("axes", [])],
        cells=[Cell(**item) for item in raw["cells"].get("cells", [])],
        taxonomy=[TaxonomyItem(**item) for item in raw["taxonomy"].get("taxonomy", [])],
        mappings=Mappings(**raw["mappings"]),
        paths=[PathItem(**item) for item in raw["paths"].get("paths", [])],
        bridges=[BridgeItem(**item) for item in raw["bridges"].get("bridges", [])],
        diagrams=DiagramConfig(**raw["diagrams"]),
        keywords=Keywords(**raw["keywords"]),
    )
