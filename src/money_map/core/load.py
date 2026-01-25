from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

import yaml

from money_map.core.model import (
    ActivityProfileDefinition,
    ActivitySubprofileDefinition,
    AppData,
    AutoTagging,
    Axis,
    BridgeItem,
    Cell,
    DiagramConfig,
    EntryLevelDefinition,
    Keywords,
    Mappings,
    PathItem,
    TaxonomyItem,
    Variant,
    WorkFormatDefinition,
)
from money_map.domain.activity_tagging import auto_tag_layers, auto_tag_variant

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


def _load_activity_profiles(data_dir: Path) -> list[ActivityProfileDefinition]:
    path = data_dir / "activity_profiles.yaml"
    if not path.exists():
        return []
    raw = _load_yaml(path)
    return [ActivityProfileDefinition(**item) for item in raw.get("activity_profiles", [])]


def _load_activity_subprofiles(data_dir: Path) -> list[ActivitySubprofileDefinition]:
    path = data_dir / "activity_subprofiles.yaml"
    if not path.exists():
        return []
    raw = _load_yaml(path)
    return [ActivitySubprofileDefinition(**item) for item in raw.get("activity_subprofiles", [])]


def _load_work_formats(data_dir: Path) -> list[WorkFormatDefinition]:
    path = data_dir / "work_formats.yaml"
    if not path.exists():
        return []
    raw = _load_yaml(path)
    return [WorkFormatDefinition(**item) for item in raw.get("work_formats", [])]


def _load_entry_levels(data_dir: Path) -> list[EntryLevelDefinition]:
    path = data_dir / "entry_levels.yaml"
    if not path.exists():
        return []
    raw = _load_yaml(path)
    return [EntryLevelDefinition(**item) for item in raw.get("entry_levels", [])]


def _load_money_way_profile_map(data_dir: Path) -> Dict[str, list[str]]:
    path = data_dir / "money_way_profile_map.yaml"
    if not path.exists():
        return {}
    raw = _load_yaml(path)
    return raw.get("money_way_profile_map", {})


def _load_auto_tagging(data_dir: Path) -> AutoTagging:
    path = data_dir / "auto_tagging.yaml"
    if not path.exists():
        return AutoTagging()
    raw = _load_yaml(path)
    return AutoTagging(**raw.get("auto_tagging", {}))


def _apply_auto_tagging(
    variants: list[Variant],
    auto_tagging: AutoTagging,
    profiles: list[ActivityProfileDefinition],
    subprofiles: list[ActivitySubprofileDefinition],
    *,
    confidence_threshold: float = 0.45,
) -> None:
    subprofile_parent = {
        subprofile.id: subprofile.parent_profile_id for subprofile in subprofiles
    }
    merged_profile_keywords: Dict[str, list[str]] = {}
    merged_subprofile_keywords: Dict[str, list[str]] = {}

    for profile in profiles:
        if profile.tags:
            merged_profile_keywords.setdefault(profile.id, []).extend(profile.tags)
    for profile_id, keywords in auto_tagging.profile_keywords.items():
        merged_profile_keywords.setdefault(profile_id, []).extend(keywords)
    for subprofile in subprofiles:
        if subprofile.tags:
            merged_subprofile_keywords.setdefault(subprofile.id, []).extend(subprofile.tags)
    for sub_id, keywords in auto_tagging.subprofile_keywords.items():
        merged_subprofile_keywords.setdefault(sub_id, []).extend(keywords)
    for variant in variants:
        text_parts = [variant.title, variant.notes or "", " ".join(variant.keywords)]
        text = " ".join(part for part in text_parts if part)
        if not variant.profile_id:
            result = auto_tag_variant(
                text,
                profile_keywords=merged_profile_keywords,
                subprofile_keywords=merged_subprofile_keywords,
                subprofile_parent=subprofile_parent,
            )
            if result.profile_id and result.confidence >= confidence_threshold:
                variant.profile_id = result.profile_id
                if result.subprofile_id:
                    variant.subprofile_id = result.subprofile_id
        if not variant.work_format_ids:
            variant.work_format_ids = auto_tag_layers(
                text,
                keywords_map=auto_tagging.work_format_keywords,
            )
        if not variant.entry_level_ids:
            variant.entry_level_ids = auto_tag_layers(
                text,
                keywords_map=auto_tagging.entry_level_keywords,
            )


def load_app_data() -> AppData:
    data_dir = _data_dir()
    raw: Dict[str, Dict[str, Any]] = {}
    for key, filename in DATA_FILES.items():
        path = data_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Не найден файл данных: {path}")
        raw[key] = _load_yaml(path)

    activity_profiles = _load_activity_profiles(data_dir)
    activity_subprofiles = _load_activity_subprofiles(data_dir)
    work_formats = _load_work_formats(data_dir)
    entry_levels = _load_entry_levels(data_dir)
    money_way_profile_map = _load_money_way_profile_map(data_dir)
    auto_tagging = _load_auto_tagging(data_dir)

    variants = _load_variants(data_dir)
    _apply_auto_tagging(variants, auto_tagging, activity_profiles, activity_subprofiles)
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
        activity_profiles=activity_profiles,
        activity_subprofiles=activity_subprofiles,
        work_formats=work_formats,
        entry_levels=entry_levels,
        money_way_profile_map=money_way_profile_map,
        auto_tagging=auto_tagging,
        variants=variants,
        variants_by_way_id=variants_by_way,
        variants_by_cell_id=variants_by_cell,
        variant_by_id=variants_by_id,
    )
