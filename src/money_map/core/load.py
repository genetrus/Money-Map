from __future__ import annotations

import json
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
}


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _data_dir() -> Path:
    override = os.environ.get("MONEY_MAP_DATA_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[3] / "data"


def _load_variants(data_dir: Path) -> list[Variant]:
    generated_dir = data_dir / "variants"
    generated_paths = [
        generated_dir / "variants.generated.json",
        generated_dir / "variants.generated.yaml",
        generated_dir / "variants.generated.yml",
    ]

    raw_variants: Dict[str, Any] | None = None
    for path in generated_paths:
        if path.exists():
            raw_variants = _load_json(path) if path.suffix == ".json" else _load_yaml(path)
            break

    if raw_variants is None:
        fallback_path = data_dir / "variants.yaml"
        if not fallback_path.exists():
            raise FileNotFoundError(f"Не найден файл данных: {fallback_path}")
        raw_variants = _load_yaml(fallback_path)

    variants_list = raw_variants.get("variants", [])
    variants_by_id: Dict[str, Dict[str, Any]] = {item["id"]: item for item in variants_list}

    manual_paths = [
        generated_dir / "variants.manual.json",
        generated_dir / "variants.manual.yaml",
        generated_dir / "variants.manual.yml",
    ]
    for path in manual_paths:
        if path.exists():
            manual_raw = _load_json(path) if path.suffix == ".json" else _load_yaml(path)
            for item in manual_raw.get("variants", []):
                base = variants_by_id.get(item.get("id"))
                if base:
                    merged = {**base, **item}
                    variants_by_id[item["id"]] = merged
                else:
                    variants_by_id[item["id"]] = item
            break

    variants = [Variant(**item) for _, item in sorted(variants_by_id.items())]
    return variants


def load_app_data() -> AppData:
    data_dir = _data_dir()
    raw: Dict[str, Dict[str, Any]] = {}
    for key, filename in DATA_FILES.items():
        path = data_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Не найден файл данных: {path}")
        raw[key] = _load_yaml(path)

    variants = _load_variants(data_dir)
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
