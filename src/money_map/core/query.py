from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from money_map.core.model import AppData, BridgeItem, Cell, PathItem, TaxonomyItem


def list_axes(data: AppData) -> List[Dict[str, object]]:
    return [{"id": axis.id, "values": axis.values, "labels": axis.labels} for axis in data.axes]


def list_cells(data: AppData) -> List[Cell]:
    return sorted(data.cells, key=lambda cell: cell.id)


def get_cell(data: AppData, cell_id: str) -> Optional[Cell]:
    return next((cell for cell in data.cells if cell.id == cell_id), None)


def list_taxonomy(data: AppData) -> List[TaxonomyItem]:
    return sorted(data.taxonomy, key=lambda item: item.id)


def get_taxonomy(data: AppData, item_id: str) -> Optional[TaxonomyItem]:
    return next((item for item in data.taxonomy if item.id == item_id), None)


def list_bridges(
    data: AppData, from_cell: Optional[str] = None, to_cell: Optional[str] = None
) -> List[BridgeItem]:
    bridges = data.bridges
    if from_cell:
        bridges = [bridge for bridge in bridges if bridge.from_cell == from_cell]
    if to_cell:
        bridges = [bridge for bridge in bridges if bridge.to_cell == to_cell]
    return sorted(bridges, key=lambda bridge: bridge.id)


def list_paths(data: AppData) -> List[PathItem]:
    return sorted(data.paths, key=lambda item: item.id)


def get_path(data: AppData, path_id: str) -> Optional[PathItem]:
    return next((path for path in data.paths if path.id == path_id), None)


def search_text(data: AppData, text: str) -> Dict[str, List[str]]:
    needle = text.lower()
    results: Dict[str, List[str]] = {"taxonomy": [], "bridges": [], "cells": []}

    for item in data.taxonomy:
        haystack = " ".join([item.name, item.description, item.risk_notes, " ".join(item.examples)]).lower()
        if needle in haystack:
            results["taxonomy"].append(item.id)

    for bridge in data.bridges:
        haystack = " ".join([bridge.name, bridge.notes, " ".join(bridge.checks)]).lower()
        if needle in haystack:
            results["bridges"].append(bridge.id)

    for cell in data.cells:
        haystack = " ".join([cell.label, cell.short, " ".join(cell.examples)]).lower()
        if needle in haystack:
            results["cells"].append(cell.id)

    for key in results:
        results[key] = sorted(results[key])
    return results


def iter_keywords(data: AppData) -> Iterable[str]:
    tags = data.keywords.keywords.get("tags", {})
    for group in tags.values():
        for entries in group.values():
            yield from entries
