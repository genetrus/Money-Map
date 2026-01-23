from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, List, Optional

import streamlit as st

from money_map.core.model import AppData
from money_map.ui import components
from money_map.ui.state import go_to_section

TYPE_LABELS = {
    "all": "Все",
    "ways": "Способы",
    "bridges": "Мосты",
    "routes": "Маршруты",
    "variants": "Варианты",
    "classifiers": "Классификаторы",
    "matrix": "Матрица",
}

CLASSIFIER_GROUP_LABELS = {
    "what_sell": "Что продаём",
    "to_whom": "Кому",
    "value_measure": "Мера ценности",
}

CELL_PATTERN = re.compile(r"[AP][1-4]", re.IGNORECASE)
TRANSITION_PATTERN = re.compile(r"([AP][1-4])\s*->\s*([AP][1-4])", re.IGNORECASE)


@dataclass
class SearchEntry:
    type: str
    id: str
    title: str
    subtitle: str
    search_blob: str
    tags_blob: str
    id_norm: str
    title_norm: str
    cells: List[str]
    way_id: Optional[str] = None
    transition: Optional[str] = None
    route_cells: Optional[List[str]] = None
    classifier_group: Optional[str] = None
    classifier_id: Optional[str] = None


def _normalize(text: str) -> str:
    if not text:
        return ""
    normalized = text.lower().replace("→", "->")
    normalized = normalized.replace("->", " arrow ")
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = normalized.replace(" arrow ", "->")
    return " ".join(normalized.split())


def _extract_cells(query: str) -> List[str]:
    return [match.group(0).upper() for match in CELL_PATTERN.finditer(query)]


def _parse_query(query: str, axis_map: Dict[str, str]) -> Dict[str, Optional[object]]:
    normalized = _normalize(query)
    transition_match = TRANSITION_PATTERN.search(normalized)
    transition = None
    if transition_match:
        transition = f"{transition_match.group(1).upper()}->{transition_match.group(2).upper()}"
    exact_cell = normalized.upper() if re.fullmatch(r"[AP][1-4]", normalized) else None
    cells = _extract_cells(normalized)
    route_cells = cells if len(cells) >= 3 else None
    axis_cell = None
    for phrase, cell_id in axis_map.items():
        if phrase in normalized:
            axis_cell = cell_id
            break
    return {
        "normalized": normalized,
        "exact_cell": exact_cell,
        "axis_cell": axis_cell,
        "transition": transition,
        "route_cells": route_cells,
        "cells": cells,
    }


def _build_axis_phrase_map(data: AppData) -> Dict[str, str]:
    phrases = {}
    for cell in data.cells:
        axes = components.cell_to_axes(cell.id) or {}
        labels = [
            components.axis_label("risk", axes.get("risk", "")),
            components.axis_label("activity", axes.get("activity", "")),
            components.axis_label("scalability", axes.get("scalability", "")),
        ]
        phrase = _normalize(" ".join(labels))
        if phrase:
            phrases[phrase] = cell.id
    return phrases


def _score_entry(
    entry: SearchEntry,
    query_info: Dict[str, Optional[object]],
    boosts: Dict[str, Optional[object]],
) -> float:
    query_norm = query_info.get("normalized") or ""
    score = 0.0
    if query_norm and query_norm in entry.title_norm:
        score += 6
    if query_norm and query_norm in entry.search_blob:
        score += 3
    if query_norm and query_norm in entry.tags_blob:
        score += 2
    if query_norm and query_norm == entry.id_norm:
        score += 8

    query_cell = query_info.get("exact_cell") or query_info.get("axis_cell")
    if query_cell and query_cell in entry.cells:
        score += 4
    transition = query_info.get("transition")
    if transition and entry.transition == transition:
        score += 5
    route_cells = query_info.get("route_cells")
    if route_cells and entry.route_cells:
        chain = "->".join(route_cells)
        if chain in "->".join(entry.route_cells):
            score += 4

    selected_cell = boosts.get("selected_cell_id")
    if selected_cell and selected_cell in entry.cells:
        score += 1.5
    selected_way = boosts.get("selected_way_id")
    if selected_way and entry.way_id == selected_way:
        score += 1.5
    allowed_cells = boosts.get("allowed_cells")
    if allowed_cells and entry.cells:
        if any(cell in allowed_cells for cell in entry.cells):
            score += 0.5
    classifier_filters = boosts.get("classifier_filters") or {}
    if classifier_filters and entry.tags_blob:
        for values in classifier_filters.values():
            if any(_normalize(value) in entry.tags_blob for value in values):
                score += 0.5
    return score


def _build_indices(data: AppData) -> List[SearchEntry]:
    entries: List[SearchEntry] = []
    way_lookup = {item.id: item.name for item in data.taxonomy}
    for item in data.taxonomy:
        labels = []
        mapping_lookup = {
            "what_sell": data.mappings.sell_items,
            "to_whom": data.mappings.to_whom_items,
            "value_measure": data.mappings.value_measures,
        }
        for group, tags in [
            ("what_sell", item.sell),
            ("to_whom", item.to_whom),
            ("value_measure", item.value),
        ]:
            for tag in tags[:1]:
                label = mapping_lookup[group].get(tag)
                labels.append(label.label if label else tag)
        subtitle = " · ".join(labels) if labels else "Типовые ячейки: " + ", ".join(item.typical_cells[:3])
        keywords = [
            item.name,
            item.description,
            " ".join(item.examples),
            " ".join(item.sell),
            " ".join(item.to_whom),
            " ".join(item.value),
        ]
        search_blob = _normalize(" ".join(keywords))
        tags_blob = _normalize(" ".join(item.sell + item.to_whom + item.value))
        entries.append(
            SearchEntry(
                type="ways",
                id=item.id,
                title=item.name,
                subtitle=subtitle,
                search_blob=search_blob,
                tags_blob=tags_blob,
                id_norm=_normalize(item.id),
                title_norm=_normalize(item.name),
                cells=item.typical_cells,
                way_id=item.id,
            )
        )

    for cell in data.cells:
        axes = components.cell_to_axes(cell.id) or {}
        subtitle = " · ".join(
            [
                components.axis_label("risk", axes.get("risk", "")),
                components.axis_label("activity", axes.get("activity", "")),
                components.axis_label("scalability", axes.get("scalability", "")),
            ]
        )
        keywords = [cell.id, cell.label, cell.short, " ".join(cell.examples), subtitle]
        entries.append(
            SearchEntry(
                type="matrix",
                id=cell.id,
                title=f"{cell.id} — {cell.label}",
                subtitle=subtitle,
                search_blob=_normalize(" ".join(keywords)),
                tags_blob="",
                id_norm=_normalize(cell.id),
                title_norm=_normalize(cell.label),
                cells=[cell.id],
            )
        )

    for bridge in data.bridges:
        transition = f"{bridge.from_cell}->{bridge.to_cell}"
        subtitle = f"Переход: {bridge.from_cell}→{bridge.to_cell}"
        keywords = [
            bridge.name,
            bridge.notes,
            " ".join(bridge.checks),
            " ".join(bridge.mechanisms),
            " ".join(bridge.tags),
            transition,
        ]
        entries.append(
            SearchEntry(
                type="bridges",
                id=bridge.id,
                title=bridge.name,
                subtitle=subtitle,
                search_blob=_normalize(" ".join(keywords)),
                tags_blob=_normalize(" ".join(bridge.tags)),
                id_norm=_normalize(bridge.id),
                title_norm=_normalize(bridge.name),
                cells=[bridge.from_cell, bridge.to_cell],
                transition=transition,
            )
        )

    for path in data.paths:
        chain = "→".join(path.sequence)
        subtitle = chain
        keywords = [path.name, path.note, " ".join(path.sequence)]
        entries.append(
            SearchEntry(
                type="routes",
                id=path.id,
                title=path.name,
                subtitle=subtitle,
                search_blob=_normalize(" ".join(keywords)),
                tags_blob="",
                id_norm=_normalize(path.id),
                title_norm=_normalize(path.name),
                cells=path.sequence,
                route_cells=path.sequence,
            )
        )

    classifier_groups = [
        ("what_sell", data.mappings.sell_items),
        ("to_whom", data.mappings.to_whom_items),
        ("value_measure", data.mappings.value_measures),
    ]
    for group, mapping in classifier_groups:
        for item_id, item in mapping.items():
            keywords = [item_id, item.label, item.notes or ""]
            entries.append(
                SearchEntry(
                    type="classifiers",
                    id=f"{group}:{item_id}",
                    title=item.label,
                    subtitle=CLASSIFIER_GROUP_LABELS.get(group, group),
                    search_blob=_normalize(" ".join(keywords)),
                    tags_blob=_normalize(item_id),
                    id_norm=_normalize(item_id),
                    title_norm=_normalize(item.label),
                    cells=item.typical_cells or [],
                    classifier_group=group,
                    classifier_id=item_id,
                )
            )

    for variant in data.variants:
        cells = variant.matrix_cells
        way_label = way_lookup.get(variant.primary_way_id, variant.primary_way_id)
        subtitle_parts = [variant.kind]
        if cells:
            subtitle_parts.append(", ".join(cells[:3]))
        subtitle_parts.append(way_label)
        subtitle = " · ".join([part for part in subtitle_parts if part])
        keywords = [
            variant.title,
            variant.kind,
            " ".join(variant.requirements),
            " ".join(variant.first_steps),
            " ".join(variant.sell_tags),
            " ".join(variant.to_whom_tags),
            " ".join(variant.value_tags),
            variant.notes or "",
        ]
        entries.append(
            SearchEntry(
                type="variants",
                id=variant.id,
                title=variant.title,
                subtitle=subtitle,
                search_blob=_normalize(" ".join(keywords)),
                tags_blob=_normalize(" ".join(variant.sell_tags + variant.to_whom_tags + variant.value_tags)),
                id_norm=_normalize(variant.id),
                title_norm=_normalize(variant.title),
                cells=cells,
                way_id=variant.primary_way_id,
            )
        )

    return entries


def render(data: AppData) -> None:
    def _reset_search_state() -> None:
        st.session_state["search_results_limit"] = 10
        st.session_state["search_selected_result"] = None

    st.title("Поиск")
    st.markdown("Поиск по способам, мостам, ячейкам, маршрутам, классификаторам и вариантам.")

    header_cols = st.columns([3, 2])
    with header_cols[0]:
        st.text_input(
            "Поиск",
            key="search_query",
            placeholder="Например: зарплата, A1, A1->A2, автоматизация",
            on_change=_reset_search_state,
        )
    with header_cols[1]:
        st.radio(
            "Тип",
            list(TYPE_LABELS.keys()),
            key="search_type_filter",
            horizontal=True,
            format_func=lambda value: TYPE_LABELS[value],
            on_change=_reset_search_state,
        )

    query = st.session_state.get("search_query", "").strip()
    if not query:
        st.info("Введите текст, чтобы начать поиск.")
        return

    axis_map = _build_axis_phrase_map(data)
    query_info = _parse_query(query, axis_map)
    entries = _build_indices(data)

    filters = components.get_filters()
    boosts = {
        "selected_cell_id": st.session_state.get("selected_cell_id"),
        "selected_way_id": st.session_state.get("selected_way_id"),
        "allowed_cells": components.get_allowed_cells_from_global_filters(data, filters),
        "classifier_filters": st.session_state.get("selected_classifier_filters", {}),
    }

    scored = []
    for entry in entries:
        score = _score_entry(entry, query_info, boosts)
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda item: item[0], reverse=True)

    counts = {key: 0 for key in TYPE_LABELS if key != "all"}
    for _, entry in scored:
        counts[entry.type] += 1

    summary = ", ".join(
        f"{TYPE_LABELS[key]} ({counts[key]})" for key in counts
    )
    st.caption(f"Результаты: {summary}")

    type_filter = st.session_state.get("search_type_filter", "all")
    filtered = [entry for _, entry in scored if type_filter == "all" or entry.type == type_filter]

    limit = st.session_state.get("search_results_limit", 10)
    visible = filtered[:limit]

    if not visible:
        st.warning("Ничего не найдено по текущему запросу.")
        return

    def _select_result(entry: SearchEntry) -> None:
        st.session_state["search_selected_result"] = {"type": entry.type, "id": entry.id}

    def _open_entry(entry: SearchEntry) -> None:
        if entry.type == "ways":
            go_to_section("ways", way_id=entry.id, open_tab="directory")
        elif entry.type == "matrix":
            go_to_section("matrix", cell_id=entry.id)
        elif entry.type == "bridges":
            go_to_section(
                "bridges",
                transition=entry.transition,
                bridge_id=entry.id,
            )
        elif entry.type == "routes":
            go_to_section("routes", route_id=entry.id)
        elif entry.type == "classifiers":
            go_to_section(
                "variants",
                classifier={"group": entry.classifier_group, "id": entry.classifier_id},
            )
        elif entry.type == "variants":
            go_to_section(
                "variants",
                variant_id=entry.id,
                way_id=entry.way_id,
            )

    def _show_variants(entry: SearchEntry) -> None:
        if entry.type == "ways":
            go_to_section("variants", way_id=entry.id)
        elif entry.type == "matrix":
            go_to_section("variants", cell_id=entry.id, variant_cell_filter=entry.id)
        elif entry.type == "bridges":
            go_to_section(
                "variants",
                transition=entry.transition,
                bridge_id=entry.id,
            )
        elif entry.type == "routes":
            go_to_section("variants", route_id=entry.id)
        elif entry.type == "classifiers":
            go_to_section(
                "variants",
                classifier={"group": entry.classifier_group, "id": entry.classifier_id},
            )

    for idx, entry in enumerate(visible):
        with st.container(border=True):
            title_cols = st.columns([4, 1])
            with title_cols[0]:
                st.markdown(f"**{entry.title}**")
                st.caption(entry.subtitle)
            with title_cols[1]:
                st.markdown(f"`{TYPE_LABELS.get(entry.type, entry.type)}`")

            action_cols = st.columns([1, 1, 1])
            action_cols[0].button(
                "Открыть",
                key=f"search-open-{entry.type}-{entry.id}-{idx}",
                use_container_width=True,
                on_click=_open_entry,
                args=(entry,),
            )
            action_cols[1].button(
                "Выбрать",
                key=f"search-select-{entry.type}-{entry.id}-{idx}",
                use_container_width=True,
                on_click=_select_result,
                args=(entry,),
            )
            if entry.type in {"ways", "matrix", "bridges", "routes", "classifiers"}:
                action_cols[2].button(
                    "Показать конкретику",
                    key=f"search-variants-{entry.type}-{entry.id}-{idx}",
                    use_container_width=True,
                    on_click=_show_variants,
                    args=(entry,),
                )
            else:
                action_cols[2].markdown(" ")

    if len(filtered) > limit:
        st.button(
            "Показать ещё",
            key="search-show-more",
            on_click=lambda: st.session_state.update(
                {"search_results_limit": limit + 10}
            ),
        )

    selected = st.session_state.get("search_selected_result")
    if not selected:
        return

    selected_entry = next(
        (entry for entry in entries if entry.type == selected.get("type") and entry.id == selected.get("id")),
        None,
    )
    if not selected_entry:
        return

    with st.container(border=True):
        st.markdown(
            f"**Вы выбрали:** {selected_entry.title} "
            f"({TYPE_LABELS.get(selected_entry.type, selected_entry.type)})"
        )
        actions = st.columns(3)
        if selected_entry.type == "matrix" and selected_entry.cells:
            actions[0].button(
                "Открыть в Матрице",
                key="search-context-matrix",
                on_click=go_to_section,
                args=("matrix",),
                kwargs={"cell_id": selected_entry.id},
            )
        if selected_entry.transition:
            actions[1].button(
                "Открыть Мосты",
                key="search-context-bridges",
                on_click=go_to_section,
                args=("bridges",),
                kwargs={
                    "transition": selected_entry.transition,
                    "bridge_id": selected_entry.id if selected_entry.type == "bridges" else None,
                },
            )
        if selected_entry.route_cells:
            actions[2].button(
                "Открыть Маршруты",
                key="search-context-routes",
                on_click=go_to_section,
                args=("routes",),
                kwargs={"route_id": selected_entry.id if selected_entry.type == "routes" else None},
            )

        quick_actions = st.columns(2)
        quick_actions[0].button(
            "Показать конкретику",
            key="search-context-variants",
            on_click=_show_variants,
            args=(selected_entry,),
            use_container_width=True,
        )
        quick_actions[1].button(
            "Открыть",
            key="search-context-open",
            on_click=_open_entry,
            args=(selected_entry,),
            use_container_width=True,
        )
