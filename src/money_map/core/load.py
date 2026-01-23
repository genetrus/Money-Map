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
    Variant,
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
    "variants": "variants.yaml",
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

    variants = [Variant(**item) for item in raw["variants"].get("variants", [])]
    variants_by_id = {variant.id: variant for variant in variants}
    variants_by_way: Dict[str, list[Variant]] = {}
    variants_by_cell: Dict[str, list[Variant]] = {}
    for variant in variants:
        variants_by_way.setdefault(variant.primary_way_id, []).append(variant)
        for cell_id in variant.matrix_cells:
            variants_by_cell.setdefault(cell_id, []).append(variant)

    return AppData(
        axes=[Axis(**item) for item in raw["axes"].get("axes", [])],
        cells=[Cell(**item) for item in raw["cells"].get("cells", [])],
        taxonomy=[TaxonomyItem(**item) for item in raw["taxonomy"].get("taxonomy", [])],
        mappings=Mappings(**raw["mappings"]),
        paths=[PathItem(**item) for item in raw["paths"].get("paths", [])],
        bridges=[BridgeItem(**item) for item in raw["bridges"].get("bridges", [])],
        diagrams=DiagramConfig(**raw["diagrams"]),
        keywords=Keywords(**raw["keywords"]),
        variants=variants,
        variants_by_way_id=variants_by_way,
        variants_by_cell_id=variants_by_cell,
        variant_by_id=variants_by_id,
    )
