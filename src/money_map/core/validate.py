from __future__ import annotations

from typing import List, Set

from money_map.core.ids import CELL_IDS
from money_map.core.model import AppData


EXPECTED_CELL_IDS = set(CELL_IDS)


def validate_app_data(data: AppData) -> List[str]:
    errors: List[str] = []
    axis_values = {axis.id: set(axis.values) for axis in data.axes}
    if {"activity", "scalability", "risk"} - set(axis_values):
        errors.append("Отсутствуют обязательные оси: activity, scalability, risk.")

    cell_ids = {cell.id for cell in data.cells}
    if cell_ids != EXPECTED_CELL_IDS:
        missing = sorted(EXPECTED_CELL_IDS - cell_ids)
        extra = sorted(cell_ids - EXPECTED_CELL_IDS)
        if missing:
            errors.append(f"Не хватает ячеек: {', '.join(missing)}")
        if extra:
            errors.append(f"Лишние ячейки: {', '.join(extra)}")

    for cell in data.cells:
        if cell.activity not in axis_values.get("activity", set()):
            errors.append(f"Ячейка {cell.id}: неверное значение activity {cell.activity}")
        if cell.scalability not in axis_values.get("scalability", set()):
            errors.append(f"Ячейка {cell.id}: неверное значение scalability {cell.scalability}")
        if cell.risk not in axis_values.get("risk", set()):
            errors.append(f"Ячейка {cell.id}: неверное значение risk {cell.risk}")

    _validate_mappings(data, errors)
    _validate_taxonomy(data, errors)
    _validate_variants(data, axis_values, errors)
    _validate_paths(data, errors)
    _validate_bridges(data, errors)

    return errors


def _validate_mappings(data: AppData, errors: List[str]) -> None:
    mappings = data.mappings
    if not mappings.sell_items or not mappings.to_whom_items or not mappings.value_measures:
        errors.append("mappings.yaml должен содержать sell_items, to_whom_items, value_measures.")


def _validate_taxonomy(data: AppData, errors: List[str]) -> None:
    cell_ids = {cell.id for cell in data.cells}
    sell_keys = set(data.mappings.sell_items)
    to_whom_keys = set(data.mappings.to_whom_items)
    value_keys = set(data.mappings.value_measures)

    for item in data.taxonomy:
        missing_fields: List[str] = []
        for field in [
            "id",
            "name",
            "sell",
            "to_whom",
            "value",
            "typical_cells",
            "description",
            "examples",
            "risk_notes",
        ]:
            if getattr(item, field) is None:
                missing_fields.append(field)
        if missing_fields:
            errors.append(
                f"Таксономия {item.id}: отсутствуют поля {', '.join(missing_fields)}"
            )

        invalid_sell = sorted(set(item.sell) - sell_keys)
        invalid_to = sorted(set(item.to_whom) - to_whom_keys)
        invalid_value = sorted(set(item.value) - value_keys)
        if invalid_sell:
            errors.append(f"Таксономия {item.id}: неизвестные sell: {', '.join(invalid_sell)}")
        if invalid_to:
            errors.append(f"Таксономия {item.id}: неизвестные to_whom: {', '.join(invalid_to)}")
        if invalid_value:
            errors.append(f"Таксономия {item.id}: неизвестные value: {', '.join(invalid_value)}")

        invalid_cells = sorted(set(item.typical_cells) - cell_ids)
        if invalid_cells:
            errors.append(
                f"Таксономия {item.id}: неизвестные ячейки {', '.join(invalid_cells)}"
            )


def _validate_variants(
    data: AppData,
    axis_values: dict[str, set[str]],
    errors: List[str],
) -> None:
    cell_ids = {cell.id for cell in data.cells}
    taxonomy_ids = {item.id for item in data.taxonomy}
    sell_keys = set(data.mappings.sell_items)
    to_whom_keys = set(data.mappings.to_whom_items)
    value_keys = set(data.mappings.value_measures)

    for variant in data.variants:
        if variant.primary_way_id not in taxonomy_ids:
            errors.append(
                f"Вариант {variant.id}: неизвестный primary_way_id {variant.primary_way_id}"
            )
        invalid_cells = sorted(set(variant.matrix_cells) - cell_ids)
        if invalid_cells:
            errors.append(
                f"Вариант {variant.id}: неизвестные ячейки {', '.join(invalid_cells)}"
            )
        invalid_sell = sorted(set(variant.sell_tags) - sell_keys)
        invalid_to = sorted(set(variant.to_whom_tags) - to_whom_keys)
        invalid_value = sorted(set(variant.value_tags) - value_keys)
        if invalid_sell:
            errors.append(f"Вариант {variant.id}: неизвестные sell_tags {', '.join(invalid_sell)}")
        if invalid_to:
            errors.append(
                f"Вариант {variant.id}: неизвестные to_whom_tags {', '.join(invalid_to)}"
            )
        if invalid_value:
            errors.append(
                f"Вариант {variant.id}: неизвестные value_tags {', '.join(invalid_value)}"
            )
        if variant.risk_level not in axis_values.get("risk", set()):
            errors.append(
                f"Вариант {variant.id}: неверное значение risk_level {variant.risk_level}"
            )
        if variant.activity not in axis_values.get("activity", set()):
            errors.append(
                f"Вариант {variant.id}: неверное значение activity {variant.activity}"
            )
        if variant.scalability not in axis_values.get("scalability", set()):
            errors.append(
                f"Вариант {variant.id}: неверное значение scalability {variant.scalability}"
            )


def _validate_paths(data: AppData, errors: List[str]) -> None:
    cell_ids = {cell.id for cell in data.cells}
    for path in data.paths:
        invalid_cells = [cell for cell in path.sequence if cell not in cell_ids]
        if invalid_cells:
            errors.append(
                f"Путь {path.id}: неизвестные ячейки {', '.join(sorted(set(invalid_cells)))}"
            )


def _validate_bridges(data: AppData, errors: List[str]) -> None:
    cell_ids = {cell.id for cell in data.cells}
    for bridge in data.bridges:
        if bridge.from_cell not in cell_ids:
            errors.append(f"Мост {bridge.id}: неизвестная ячейка from {bridge.from_cell}")
        if bridge.to_cell not in cell_ids:
            errors.append(f"Мост {bridge.id}: неизвестная ячейка to {bridge.to_cell}")
