from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, List, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components_html
from streamlit_agraph import Config, Edge, Node

from money_map.core.load import load_app_data
from money_map.core.model import AppData, BridgeItem, Cell, PathItem, TaxonomyItem, Variant
from money_map.core.query import list_bridges
from money_map.core.taxonomy_graph import build_taxonomy_star
from money_map.core.validate import validate_app_data
from money_map.render.taxonomy_graph import render_taxonomy_graph_html
from money_map.ui.state import go_to_section, request_nav


@dataclass
class Filters:
    risk: str
    activity: str
    scalability: str


DEFAULT_PAGE = "Обзор"
PAGES = [
    "Обзор",
    "Матрица",
    "Мосты",
    "Маршруты",
    "Сравнение",
    "Поиск",
    "Классификатор",
    "Граф",
    "Способы получения денег",
    "Варианты (конкретика)",
]

NAV_MODES = ["Исследование", "Конструктор пути", "Сравнение"]
NAV_MODE_HINTS = {
    "Исследование": "Смотри связи и открывай детали",
    "Конструктор пути": "Двигайся по шагам к конкретике",
    "Сравнение": "Собирай кандидатов и сравнивай",
}
NAV_STEPS = ["Матрица", "Классификатор", "Способы", "Маршрут", "Мосты", "Варианты"]
NAV_STEP_TO_SECTION = {
    "Матрица": "Матрица",
    "Классификатор": "Классификатор",
    "Способы": "Способы получения денег",
    "Маршрут": "Маршруты",
    "Мосты": "Мосты",
    "Варианты": "Варианты (конкретика)",
}
NAV_SECTION_TO_STEP = {value: key for key, value in NAV_STEP_TO_SECTION.items()}


@st.cache_data(show_spinner="Загрузка данных...")
def load_data() -> Tuple[AppData, List[str]]:
    data = load_app_data()
    errors = validate_app_data(data)
    return data, errors


def reset_cache() -> None:
    load_data.clear()


def init_session_state() -> None:
    st.session_state.setdefault("page", DEFAULT_PAGE)
    st.session_state.setdefault("nav_section", DEFAULT_PAGE)
    st.session_state.setdefault("nav_payload", {})
    st.session_state.setdefault("nav_mode", "Исследование")
    st.session_state.setdefault("nav_step", "Матрица")
    st.session_state.setdefault("compare_items", [])
    st.session_state.setdefault("compare_selected_id", None)
    st.session_state.setdefault("current_page", DEFAULT_PAGE)
    st.session_state.setdefault("active_section", DEFAULT_PAGE)
    st.session_state.setdefault("selected_cell", None)
    st.session_state.setdefault("selected_cell_id", None)
    st.session_state.setdefault("selected_transition", None)
    st.session_state.setdefault("selected_bridge_id", None)
    st.session_state.setdefault("selected_route_id", None)
    st.session_state.setdefault("route_filters_start_cell", None)
    st.session_state.setdefault("route_filters_target_cell", None)
    st.session_state.setdefault("chosen_bridges_by_transition", {})
    st.session_state.setdefault("selected_taxonomy", None)
    st.session_state.setdefault("selected_tax_id", None)
    st.session_state.setdefault("selected_way_id", None)
    st.session_state.setdefault("selected_bridge", None)
    st.session_state.setdefault("selected_path", None)
    st.session_state.setdefault("selected_variant_id", None)
    st.session_state.setdefault("graph_selected_node", None)
    st.session_state.setdefault("graph_selected_bridge", None)
    st.session_state.setdefault("search_query", "")
    st.session_state.setdefault("search_type_filter", "all")
    st.session_state.setdefault("search_selected_result", None)
    st.session_state.setdefault("search_results_limit", 10)
    st.session_state.setdefault("active_tab", "Карта")
    st.session_state.setdefault("ways_ui_tab", "Карта")
    st.session_state.setdefault("pending_nav_section", None)
    st.session_state.setdefault("pending_nav", None)
    st.session_state.setdefault("last_click_id", None)
    st.session_state.setdefault("matrix_focus_cell", None)
    st.session_state.setdefault("ways_highlight_node_id", None)
    st.session_state.setdefault("ways_selected_node_id", None)
    st.session_state.setdefault("ways_selected_way_id", None)
    st.session_state.setdefault("ways_ignore_next_selection", False)
    st.session_state.setdefault("ways_last_tap", {"node_id": None, "timestamp_ms": 0.0})
    st.session_state.setdefault("ways_outside_only", False)
    st.session_state.setdefault("variants_filter_way", "all")
    st.session_state.setdefault("variants_filter_kind", "all")
    st.session_state.setdefault("variants_filter_cell", "all")
    st.session_state.setdefault("variants_filter_outside", False)
    st.session_state.setdefault("variants_mode", "Подбор")
    st.session_state.setdefault("variants_scope", "strict")
    st.session_state.setdefault("variants_library_search", "")
    st.session_state.setdefault("variants_library_sort", "title")
    st.session_state.setdefault("variants_library_mechanism", "all")
    st.session_state.setdefault("variants_library_cell", "all")
    st.session_state.setdefault("variants_library_kind", "all")
    st.session_state.setdefault("shortlist", {})
    st.session_state.setdefault(
        "selection",
        {
            "selected_matrix_cell": None,
            "selected_transition": None,
            "selected_classifiers": {"sell": [], "to_whom": [], "measure": []},
            "selected_mechanism_ids": [],
            "selected_route_id": None,
            "selected_bridge_ids": [],
            "risk": "all",
            "activity": "all",
            "scalability": "all",
        },
    )
    st.session_state.setdefault(
        "selected_classifier_filters",
        {"what_sell": [], "to_whom": [], "value_measure": []},
    )
    st.session_state.setdefault("classifier_selected_what_sell", set())
    st.session_state.setdefault("classifier_selected_to_whom", set())
    st.session_state.setdefault("classifier_selected_value_measure", set())
    st.session_state.setdefault("classifier_mode", "panel")
    st.session_state.setdefault("classifier_selection_snapshot", {})
    st.session_state.setdefault("classifier_directory_search", "")
    st.session_state.setdefault("classifier_directory_group", "all")
    st.session_state.setdefault("matrix_axis_risk", "low")
    st.session_state.setdefault("matrix_axis_activity", "active")
    st.session_state.setdefault("matrix_axis_scalability", "linear")


def _apply_pending_nav_state() -> None:
    if "nav_mode_next" in st.session_state:
        st.session_state["nav_mode"] = st.session_state.pop("nav_mode_next")
    if "nav_step_next" in st.session_state:
        st.session_state["nav_step"] = st.session_state.pop("nav_step_next")


def apply_pending_navigation() -> None:
    _apply_pending_nav_state()
    pending_nav = st.session_state.pop("pending_nav", None)
    if isinstance(pending_nav, dict):
        section = pending_nav.get("section")
        params = pending_nav.get("params", {})
        if isinstance(section, str) and section:
            st.session_state["nav_section"] = section
        if isinstance(params, dict):
            payload = st.session_state.get("nav_payload")
            if not isinstance(payload, dict):
                payload = {}
            payload.update(params)
            st.session_state["nav_payload"] = payload
            st.session_state["nav_intent"] = {"section": section, "params": params}
        st.rerun()

    pending_section = st.session_state.pop("pending_nav_section", None)
    if isinstance(pending_section, str) and pending_section:
        if pending_section != st.session_state.get("nav_section"):
            st.session_state["nav_section"] = pending_section
            st.rerun()

    if st.session_state.get("nav_mode") == "Конструктор пути":
        section = st.session_state.get("nav_section")
        step = NAV_SECTION_TO_STEP.get(section)
        if step:
            st.session_state["nav_step"] = step


def sync_selection_context() -> dict[str, object]:
    selection = st.session_state.get("selection")
    if not isinstance(selection, dict):
        selection = {}
    selection.setdefault("selected_classifiers", {"sell": [], "to_whom": [], "measure": []})
    selection.setdefault("selected_mechanism_ids", [])
    selection.setdefault("selected_bridge_ids", [])
    selection.setdefault("selected_matrix_cell", None)
    selection.setdefault("selected_transition", None)
    selection.setdefault("selected_route_id", None)

    selection["selected_matrix_cell"] = st.session_state.get("selected_cell_id")
    selection["selected_transition"] = st.session_state.get("selected_transition")
    selection["selected_route_id"] = st.session_state.get("selected_route_id")
    selection["risk"] = st.session_state.get("filter_risk", "all")
    selection["activity"] = st.session_state.get("filter_activity", "all")
    selection["scalability"] = st.session_state.get("filter_scalability", "all")

    classifier_state = get_classifier_selection_state()
    selection["selected_classifiers"] = {
        "sell": sorted(classifier_state.get("what_sell", set())),
        "to_whom": sorted(classifier_state.get("to_whom", set())),
        "measure": sorted(classifier_state.get("value_measure", set())),
    }

    mechanism_ids: list[str] = []
    for key in ("selected_way_id", "ways_selected_way_id", "selected_tax_id"):
        way_id = st.session_state.get(key)
        if isinstance(way_id, str) and way_id and way_id not in mechanism_ids:
            mechanism_ids.append(way_id)
    selection["selected_mechanism_ids"] = mechanism_ids

    bridge_ids: list[str] = []
    selected_bridge_id = st.session_state.get("selected_bridge_id")
    if isinstance(selected_bridge_id, str) and selected_bridge_id:
        bridge_ids.append(selected_bridge_id)
    chosen_bridges = st.session_state.get("chosen_bridges_by_transition", {})
    if isinstance(chosen_bridges, dict):
        for bridge_id in chosen_bridges.values():
            if isinstance(bridge_id, str) and bridge_id and bridge_id not in bridge_ids:
                bridge_ids.append(bridge_id)
    selection["selected_bridge_ids"] = bridge_ids

    st.session_state["selection"] = selection
    update_nav_payload_from_state()
    return selection


def update_nav_payload_from_state() -> dict[str, object]:
    payload = st.session_state.get("nav_payload")
    if not isinstance(payload, dict):
        payload = {}
    classifier_state = get_classifier_selection_state()
    payload["selected_cell_id"] = st.session_state.get("selected_cell_id")
    payload["classifier_selected_what_sell"] = set(classifier_state.get("what_sell", set()))
    payload["classifier_selected_to_whom"] = set(classifier_state.get("to_whom", set()))
    payload["classifier_selected_value_measure"] = set(classifier_state.get("value_measure", set()))
    payload["selected_way_id"] = st.session_state.get("selected_way_id")
    payload["selected_route_id"] = st.session_state.get("selected_route_id")
    payload["selected_bridge_id"] = st.session_state.get("selected_bridge_id")
    payload["selected_variant_id"] = st.session_state.get("selected_variant_id")
    st.session_state["nav_payload"] = payload
    return payload


def consume_nav_intent(section: str) -> Optional[dict[str, object]]:
    intent = st.session_state.get("nav_intent")
    if not isinstance(intent, dict):
        return None
    if intent.get("section") != section:
        return None
    params = intent.get("params", {})
    st.session_state.pop("nav_intent", None)
    return params if isinstance(params, dict) else None


def nav_step_complete(step: str) -> bool:
    if step == "Матрица":
        return bool(st.session_state.get("selected_cell_id"))
    if step == "Классификатор":
        selections = get_classifier_selection_state()
        return any(selections.values())
    if step == "Способы":
        return bool(st.session_state.get("selected_way_id"))
    if step == "Маршрут":
        return bool(st.session_state.get("selected_route_id"))
    if step == "Мосты":
        return bool(st.session_state.get("selected_bridge_id"))
    if step == "Варианты":
        return bool(st.session_state.get("selected_variant_id"))
    return False


def render_path_wizard(current_step: str) -> None:
    if st.session_state.get("nav_mode") != "Конструктор пути":
        return
    if current_step not in NAV_STEPS:
        return

    index = NAV_STEPS.index(current_step)
    prev_step = NAV_STEPS[index - 1] if index > 0 else None
    next_step = NAV_STEPS[index + 1] if index + 1 < len(NAV_STEPS) else None

    step_status = []
    for step in NAV_STEPS:
        marker = "✅" if nav_step_complete(step) else "•"
        step_status.append(f"{marker} {step}")

    hints = {
        "Матрица": ("Выберите ячейку матрицы.", "Дальше: уточним классификатор."),
        "Классификатор": ("Выберите хотя бы один чип.", "Дальше: способы."),
        "Способы": ("Выберите способ.", "Дальше: маршрут."),
        "Маршрут": ("Выберите маршрут.", "Дальше: мосты."),
        "Мосты": ("Выберите мост.", "Дальше: варианты."),
        "Варианты": ("Выберите вариант и сохраните.", "Дальше: можно добавить в кандидаты."),
    }
    hint_now, hint_next = hints.get(current_step, ("", ""))

    with st.container(border=True):
        header_cols = st.columns([3, 2])
        header_cols[0].markdown(f"**Шаг:** {current_step}")
        header_cols[1].caption(" · ".join(step_status))

        action_cols = st.columns([1, 1, 3])
        if prev_step:
            if action_cols[0].button("Назад", key=f"wizard-back-{current_step}"):
                st.session_state["nav_step_next"] = prev_step
                request_nav(NAV_STEP_TO_SECTION[prev_step])
        else:
            action_cols[0].button("Назад", key=f"wizard-back-{current_step}", disabled=True)

        can_next = nav_step_complete(current_step) and next_step is not None
        if action_cols[1].button(
            "Дальше",
            key=f"wizard-next-{current_step}",
            disabled=not can_next,
        ):
            if next_step:
                st.session_state["nav_step_next"] = next_step
                request_nav(NAV_STEP_TO_SECTION[next_step])

        if hint_now:
            action_cols[2].caption(f"{hint_now} {hint_next}".strip())


def add_compare_item(item: dict[str, object]) -> bool:
    if not item or not item.get("type") or not item.get("id"):
        return False
    items = st.session_state.get("compare_items")
    if not isinstance(items, list):
        items = []
    for existing in items:
        if existing.get("type") == item.get("type") and existing.get("id") == item.get("id"):
            return False
    items.append(item)
    st.session_state["compare_items"] = items
    return True


def remove_compare_item(item_type: str, item_id: str) -> None:
    items = st.session_state.get("compare_items")
    if not isinstance(items, list):
        return
    st.session_state["compare_items"] = [
        item
        for item in items
        if item.get("type") != item_type or item.get("id") != item_id
    ]


def clear_compare_items() -> None:
    st.session_state["compare_items"] = []


def request_page(page: str) -> None:
    current = st.session_state.get("nav_section")
    if page != current:
        st.session_state["pending_nav_section"] = page
        st.rerun()


CLASSIFIER_SELECTION_KEYS = {
    "what_sell": "classifier_selected_what_sell",
    "to_whom": "classifier_selected_to_whom",
    "value_measure": "classifier_selected_value_measure",
}

CLASSIFIER_GROUP_ALIASES = {
    "sell": "what_sell",
    "what_sell": "what_sell",
    "to": "to_whom",
    "to_whom": "to_whom",
    "value": "value_measure",
    "value_measure": "value_measure",
}


def normalize_classifier_group_key(group: str) -> Optional[str]:
    if not group:
        return None
    normalized = CLASSIFIER_GROUP_ALIASES.get(group, group)
    if normalized in CLASSIFIER_SELECTION_KEYS:
        return normalized
    return None


def get_classifier_selection_state() -> dict[str, set[str]]:
    return {
        group: set(st.session_state.get(key, set()))
        for group, key in CLASSIFIER_SELECTION_KEYS.items()
    }


def sync_classifier_filters_from_state() -> dict[str, list[str]]:
    selections = get_classifier_selection_state()
    filters = {group: sorted(selections[group]) for group in CLASSIFIER_SELECTION_KEYS}
    st.session_state["selected_classifier_filters"] = filters
    return filters


def clear_classifier_selections() -> None:
    for key in CLASSIFIER_SELECTION_KEYS.values():
        st.session_state[key] = set()
    sync_classifier_filters_from_state()


def add_classifier_selection(group: str, value: str) -> None:
    normalized = normalize_classifier_group_key(group)
    if not normalized or not value:
        return
    key = CLASSIFIER_SELECTION_KEYS[normalized]
    selected = set(st.session_state.get(key, set()))
    if value not in selected:
        selected.add(value)
        st.session_state[key] = selected


def apply_classifier_filter_request(request: object) -> None:
    def _apply(group: str, value: str) -> None:
        add_classifier_selection(group, value)

    if isinstance(request, list):
        for item in request:
            if isinstance(item, dict):
                _apply(item.get("group", ""), item.get("id", ""))
            elif isinstance(item, tuple) and len(item) == 2:
                _apply(item[0], item[1])
    elif isinstance(request, dict):
        _apply(request.get("group", ""), request.get("id", ""))
    elif isinstance(request, tuple) and len(request) == 2:
        _apply(request[0], request[1])

    sync_classifier_filters_from_state()


def score_variant_against_classifiers(
    variant: Variant,
    selections: dict[str, set[str]],
) -> Optional[float]:
    if not selections or not any(selections.values()):
        return 0.0

    total_score = 0.0
    penalty = 0.0
    group_to_tags = {
        "what_sell": variant.sell_tags,
        "to_whom": variant.to_whom_tags,
        "value_measure": variant.value_tags,
    }
    for group, selected in selections.items():
        if not selected:
            continue
        tags = group_to_tags.get(group, [])
        if tags:
            overlap = selected.intersection(tags)
            if not overlap:
                return None
            total_score += len(overlap) * 2.0
        else:
            penalty += 0.5
    return total_score - penalty


MATRIX_AXES_TO_CELL = {
    ("low", "active", "linear"): "A1",
    ("low", "active", "scalable"): "A2",
    ("low", "passive", "linear"): "P1",
    ("low", "passive", "scalable"): "P2",
    ("high", "active", "linear"): "A3",
    ("high", "active", "scalable"): "A4",
    ("high", "passive", "linear"): "P3",
    ("high", "passive", "scalable"): "P4",
}

MATRIX_CELL_TO_AXES = {
    cell_id: {"risk": risk, "activity": activity, "scalability": scalability}
    for (risk, activity, scalability), cell_id in MATRIX_AXES_TO_CELL.items()
}

AXIS_LABELS = {
    "risk": {"low": "Низкий риск", "high": "Высокий риск"},
    "activity": {"active": "Активно", "passive": "Пассивно"},
    "scalability": {"linear": "Линейно", "scalable": "Масштабируемо"},
}


def axes_to_cell_id(risk: str, activity: str, scalability: str) -> Optional[str]:
    return MATRIX_AXES_TO_CELL.get((risk, activity, scalability))


def cell_to_axes(cell_id: str) -> Optional[dict[str, str]]:
    return MATRIX_CELL_TO_AXES.get(cell_id)


def axis_label(axis: str, value: str) -> str:
    return AXIS_LABELS.get(axis, {}).get(value, value)


def set_page(page: str) -> None:
    st.session_state["page"] = page
    st.session_state["active_section"] = page
    if page != st.session_state.get("nav_section"):
        st.session_state["pending_nav_section"] = page


def set_selected_cell(cell_id: Optional[str]) -> None:
    st.session_state["selected_cell"] = cell_id
    st.session_state["selected_cell_id"] = cell_id
    st.session_state["graph_selected_node"] = cell_id


def set_selected_taxonomy(item_id: Optional[str]) -> None:
    st.session_state["selected_taxonomy"] = item_id
    st.session_state["selected_way_id"] = item_id


def set_selected_tax_id(item_id: Optional[str]) -> None:
    st.session_state["selected_tax_id"] = item_id
    st.session_state["selected_taxonomy"] = item_id
    st.session_state["selected_way_id"] = item_id


def set_selected_bridge(bridge_id: Optional[str]) -> None:
    st.session_state["selected_bridge"] = bridge_id
    st.session_state["selected_bridge_id"] = bridge_id
    st.session_state["graph_selected_bridge"] = bridge_id


def set_selected_path(path_id: Optional[str]) -> None:
    st.session_state["selected_path"] = path_id
    st.session_state["selected_route_id"] = path_id


def set_selected_variant(variant_id: Optional[str]) -> None:
    st.session_state["selected_variant_id"] = variant_id


def get_filters() -> Filters:
    return Filters(
        risk=st.session_state.get("filter_risk", "all"),
        activity=st.session_state.get("filter_activity", "all"),
        scalability=st.session_state.get("filter_scalability", "all"),
    )


def sidebar_filters() -> Filters:
    st.sidebar.markdown("### Глобальные фильтры")
    risk = st.sidebar.selectbox(
        "Риск",
        ["all", "low", "high"],
        format_func=lambda value: {
            "all": "Все",
            "low": "Низкий",
            "high": "Высокий",
        }[value],
        key="filter_risk",
    )
    activity = st.sidebar.selectbox(
        "Активность",
        ["all", "active", "passive"],
        format_func=lambda value: {
            "all": "Все",
            "active": "Активно",
            "passive": "Пассивно",
        }[value],
        key="filter_activity",
    )
    scalability = st.sidebar.selectbox(
        "Масштабируемость",
        ["all", "linear", "scalable"],
        format_func=lambda value: {
            "all": "Все",
            "linear": "Линейно",
            "scalable": "Масштабируемо",
        }[value],
        key="filter_scalability",
    )
    return Filters(risk=risk, activity=activity, scalability=scalability)


def filter_cells(cells: Iterable[Cell], filters: Filters) -> List[Cell]:
    results = list(cells)
    if filters.risk != "all":
        results = [cell for cell in results if cell.risk == filters.risk]
    if filters.activity != "all":
        results = [cell for cell in results if cell.activity == filters.activity]
    if filters.scalability != "all":
        results = [cell for cell in results if cell.scalability == filters.scalability]
    return results


def get_allowed_cells_from_global_filters(data: AppData, filters: Filters) -> set[str]:
    return {cell.id for cell in filter_cells(data.cells, filters)}


def apply_global_filters_to_variants(
    variants: Iterable[Variant],
    filters: Filters,
) -> List[Variant]:
    results = list(variants)
    if filters.risk != "all":
        results = [variant for variant in results if variant.risk_level == filters.risk]
    if filters.activity != "all":
        results = [variant for variant in results if variant.activity == filters.activity]
    if filters.scalability != "all":
        results = [variant for variant in results if variant.scalability == filters.scalability]
    return results


def apply_global_filters_to_ways(
    ways: Iterable[TaxonomyItem],
    filters: Filters,
    data: AppData,
) -> List[TaxonomyItem]:
    allowed_cells = get_allowed_cells_from_global_filters(data, filters)
    filtered_variant_ids = {
        variant.primary_way_id
        for variant in apply_global_filters_to_variants(data.variants, filters)
    }
    filtered = []
    for item in ways:
        if not allowed_cells and not filtered_variant_ids:
            continue
        if any(cell in allowed_cells for cell in item.typical_cells) or item.id in filtered_variant_ids:
            filtered.append(item)
    return filtered


def filter_taxonomy_by_cells(
    taxonomy: Iterable[TaxonomyItem],
    allowed_cells: set[str],
) -> List[str]:
    if not allowed_cells:
        return []
    return [
        item.id
        for item in taxonomy
        if any(cell_id in allowed_cells for cell_id in item.typical_cells)
    ]


def cell_lookup(data: AppData) -> Dict[str, Cell]:
    return {cell.id: cell for cell in data.cells}


def taxonomy_lookup(data: AppData) -> Dict[str, TaxonomyItem]:
    return {item.id: item for item in data.taxonomy}


def paths_for_cell(data: AppData, cell_id: str) -> List[PathItem]:
    return [path for path in data.paths if cell_id in path.sequence]


def bridges_for_cell(data: AppData, cell_id: str) -> List[BridgeItem]:
    return [bridge for bridge in data.bridges if bridge.from_cell == cell_id or bridge.to_cell == cell_id]


def bridges_between(data: AppData, from_cell: str, to_cell: str) -> List[BridgeItem]:
    return list_bridges(data, from_cell=from_cell, to_cell=to_cell)


def danger_bridge(bridge: BridgeItem) -> bool:
    trigger_words = ("опасно", "лотерея", "плечо")
    notes = bridge.notes.lower()
    return any(word in notes for word in trigger_words)


def taxonomy_related_bridges(data: AppData, item: TaxonomyItem) -> List[BridgeItem]:
    related_cells = set(item.typical_cells)
    return [bridge for bridge in data.bridges if bridge.from_cell in related_cells or bridge.to_cell in related_cells]


def taxonomy_related_paths(data: AppData, item: TaxonomyItem) -> List[PathItem]:
    related_cells = set(item.typical_cells)
    return [path for path in data.paths if any(cell in related_cells for cell in path.sequence)]


def format_cells_inline(cells: Iterable[str]) -> str:
    return ", ".join(cells) if cells else "—"


def render_cell_card(cell: Cell) -> str:
    examples = "; ".join(cell.examples[:2]) if cell.examples else "—"
    return (
        f"**{cell.id} — {cell.label}**\n\n"
        f"{cell.short}\n\n"
        f"Примеры: {examples}"
    )


def ascii_focus_diagram(cell_id: str, outgoing: List[BridgeItem]) -> str:
    if not outgoing:
        return f"[{cell_id}]"
    arrows = "  ".join([f"{cell_id} → {bridge.to_cell}" for bridge in outgoing[:3]])
    return arrows


def ascii_path(path: PathItem) -> str:
    return " → ".join(path.sequence)


def load_css() -> None:
    css_path = Path(__file__).resolve().parent / "assets" / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def _outside_market_label(outside_market: bool) -> str:
    return "Вне рынка: Да" if outside_market else "Вне рынка: Нет"


def _chips(values: Iterable[str]) -> str:
    return " ".join(f"`{value}`" for value in values) if values else "—"


def chips(values: Iterable[str]) -> str:
    return _chips(values)


def render_taxonomy_details_card(
    app_data: AppData,
    tax_id: Optional[str],
    filters: Filters,
    outside_only: bool,
) -> None:
    with st.container(border=True):
        if not tax_id:
            st.markdown("Нажмите на любой узел (например «Зарплата») — здесь появятся детали.")
            return

        item = taxonomy_lookup(app_data).get(tax_id)
        if not item:
            st.warning("Механизм не найден.")
            return

        header_left, header_right = st.columns([3, 2])
        with header_left:
            st.markdown(f"### {item.name}")
        badge = _outside_market_label(item.outside_market)
        if item.outside_market:
            badge = f"{badge} · ⚠️ не рыночный механизм"
        with header_right:
            st.markdown(f"**{badge}**")

        if st.session_state.get("nav_mode") == "Сравнение":
            if st.button(
                "+ В сравнение",
                key=f"ways-compare-{item.id}",
                use_container_width=True,
            ):
                add_compare_item(
                    {
                        "type": "way",
                        "id": item.id,
                        "name": item.name,
                        "cell_id": item.typical_cells[0] if item.typical_cells else None,
                        "classifier_tags": [
                            *item.sell,
                            *item.to_whom,
                            *item.value,
                        ],
                    },
                )

        st.markdown("#### Коротко")
        st.write(item.description)
        st.caption(item.risk_notes or "—")
        if item.examples:
            st.markdown("**Примеры**")
            for example in item.examples:
                st.markdown(f"- {example}")

        st.markdown("#### Теги (что продаёшь / кому / как меряется)")
        tag_cols = st.columns(3)
        with tag_cols[0]:
            st.caption("Что продаёшь")
            st.markdown(_chips(item.sell))
        with tag_cols[1]:
            st.caption("Кому")
            st.markdown(_chips(item.to_whom))
        with tag_cols[2]:
            st.caption("Как меряется")
            st.markdown(_chips(item.value))

        def _show_more_key(suffix: str) -> str:
            return f"ways-links-{item.id}-{suffix}-more"

        def _toggle_show_more(suffix: str) -> None:
            st.session_state[_show_more_key(suffix)] = True

        def _render_link_group(
            title: str,
            entries: list[tuple[str, dict[str, object]]],
            suffix: str,
        ) -> None:
            st.markdown(f"**{title}**")
            if not entries:
                st.caption("—")
                return
            show_all = bool(st.session_state.get(_show_more_key(suffix), False))
            visible = entries if show_all else entries[:5]
            cols = st.columns(len(visible)) if visible else []
            for idx, (label, payload) in enumerate(visible):
                cols[idx].button(
                    label,
                    key=f"ways-links-{item.id}-{suffix}-{idx}-{label}",
                    on_click=go_to_section,
                    args=(payload.get("section", ""),),
                    kwargs={k: v for k, v in payload.items() if k != "section"},
                    use_container_width=True,
                )
            if not show_all and len(entries) > 5:
                st.button(
                    "Показать ещё",
                    key=f"ways-links-{item.id}-{suffix}-show",
                    on_click=_toggle_show_more,
                    args=(suffix,),
                )

        st.markdown("#### Идеальная схема связей")
        matrix_entries = [
            (cell_id, {"section": "Матрица", "cell_id": cell_id})
            for cell_id in item.typical_cells
        ]
        _render_link_group(
            "Матрица",
            matrix_entries,
            "matrix",
        )

        sell_labels = [
            (app_data.mappings.sell_items.get(tag).label if tag in app_data.mappings.sell_items else tag, tag)
            for tag in item.sell
        ]
        to_whom_labels = [
            (
                app_data.mappings.to_whom_items.get(tag).label if tag in app_data.mappings.to_whom_items else tag,
                tag,
            )
            for tag in item.to_whom
        ]
        value_labels = [
            (
                app_data.mappings.value_measures.get(tag).label if tag in app_data.mappings.value_measures else tag,
                tag,
            )
            for tag in item.value
        ]
        classifier_entries: list[tuple[str, dict[str, object]]] = []
        classifier_entries.extend(
            [
                (label, {"section": "Классификатор", "classifier": {"group": "what_sell", "id": tag}})
                for label, tag in sell_labels
            ]
        )
        classifier_entries.extend(
            [
                (label, {"section": "Классификатор", "classifier": {"group": "to_whom", "id": tag}})
                for label, tag in to_whom_labels
            ]
        )
        classifier_entries.extend(
            [
                (label, {"section": "Классификатор", "classifier": {"group": "value_measure", "id": tag}})
                for label, tag in value_labels
            ]
        )
        _render_link_group("Классификатор", classifier_entries, "classifier")

        bridges = taxonomy_related_bridges(app_data, item)
        bridge_entries = [
            (bridge.name, {"section": "Мосты", "bridge_id": bridge.id})
            for bridge in bridges
        ]
        _render_link_group("Мосты", bridge_entries, "bridges")

        paths = taxonomy_related_paths(app_data, item)
        route_entries = [
            (path.name, {"section": "Маршруты", "route_id": path.id})
            for path in paths
        ]
        _render_link_group("Маршруты", route_entries, "routes")

        classifier_payload = []
        classifier_payload.extend(
            [{"group": "what_sell", "id": tag} for tag in item.sell]
        )
        classifier_payload.extend(
            [{"group": "to_whom", "id": tag} for tag in item.to_whom]
        )
        classifier_payload.extend(
            [{"group": "value_measure", "id": tag} for tag in item.value]
        )
        if st.button(
            "Добавить в Варианты (конкретика)",
            key=f"ways-links-{item.id}-variants",
        ):
            go_to_section(
                "Варианты (конкретика)",
                way_id=item.id,
                variant_cell_filter=item.typical_cells[0] if item.typical_cells else "all",
                classifier=classifier_payload if classifier_payload else None,
            )

        st.markdown("#### Связанные ячейки матрицы (A1..P4)")
        if not item.typical_cells:
            st.caption("Нет типовых ячеек.")
        else:
            lookup = cell_lookup(app_data)
            for cell_id in item.typical_cells:
                cell = lookup.get(cell_id)
                summary = cell.short if cell and cell.short else (cell.label if cell else "—")
                row = st.columns([1, 5])
                with row[0]:
                    if st.button(cell_id, key=f"tax-cell-{item.id}-{cell_id}"):
                        go_to_section("Матрица", cell_id=cell_id)
                with row[1]:
                    st.markdown(summary)

        st.markdown("#### Конкретные варианты (конкретика)")
        variants = app_data.variants_by_way_id.get(item.id, [])
        variants = apply_global_filters_to_variants(variants, filters)
        if outside_only:
            variants = [variant for variant in variants if variant.outside_market]
        if not variants:
            st.caption("Нет вариантов для этого способа.")
        else:
            for variant in variants[:10]:
                label = f"{variant.title} · {variant.kind}"
                if st.button(
                    label,
                    key=f"tax-variant-{item.id}-{variant.id}",
                ):
                    go_to_section("Варианты (конкретика)", variant_id=variant.id, way_id=item.id)

        st.markdown("#### Связанные мосты")
        if not bridges:
            st.caption("Нет связанных мостов.")
        else:
            grouped: Dict[Tuple[str, str], List[BridgeItem]] = {}
            for bridge in bridges:
                grouped.setdefault((bridge.from_cell, bridge.to_cell), []).append(bridge)
            for (from_cell, to_cell), items in grouped.items():
                names = ", ".join(bridge.name for bridge in items)
                with st.expander(f"{from_cell} → {to_cell} — {names}", expanded=False):
                    for bridge in items:
                        if len(items) > 1:
                            st.markdown(f"**{bridge.name}**")
                        st.markdown(bridge.notes or "—")
                        st.caption("Механизмы")
                        st.markdown(_chips(bridge.mechanisms))
                        st.caption("Проверки")
                        if bridge.checks:
                            for check in bridge.checks:
                                st.markdown(f"- {check}")
                        else:
                            st.markdown("—")

        st.markdown("#### Связанные маршруты")
        paths = taxonomy_related_paths(app_data, item)
        if not paths:
            st.caption("Нет связанных маршрутов.")
        else:
            for path in paths:
                st.markdown(f"**{path.name}**")
                st.markdown(f"`{ascii_path(path)}`")
                st.caption(path.note or "—")


@st.cache_data(show_spinner="Формирование графа...")
def _build_taxonomy_graph_html(
    data: AppData,
    include_tags: bool,
    outside_only: bool,
    selected_tax_id: Optional[str],
) -> str:
    return render_taxonomy_graph_html(
        data,
        include_tags=include_tags,
        outside_only=outside_only,
        selected_tax_id=selected_tax_id,
        height="720px",
        width="100%",
    )


def render_taxonomy_star_graph(
    app_data: AppData,
    selected_tax_id: Optional[str],
    show_tags: bool,
    outside_only: bool,
) -> None:
    html = _build_taxonomy_graph_html(
        app_data,
        include_tags=show_tags,
        outside_only=outside_only,
        selected_tax_id=selected_tax_id,
    )
    components_html.html(html, height=760, scrolling=True)


def clear_taxonomy_graph_cache() -> None:
    _build_taxonomy_graph_html.clear()


def render_taxonomy_list(app_data: AppData, search_query: str) -> Optional[str]:
    items = sorted(app_data.taxonomy, key=lambda item: item.name)
    if search_query:
        lowered = search_query.lower()
        items = [item for item in items if lowered in item.name.lower()]
    if not items:
        st.info("Нет механизмов под текущий запрос.")
        return None

    options = [item.id for item in items]
    name_lookup = {item.id: item.name for item in items}
    current = st.session_state.get("selected_tax_id")
    if current in options:
        desired = current
    else:
        desired = options[0]

    if st.session_state.get("taxonomy_list_select") != desired:
        st.session_state["taxonomy_list_select"] = desired

    selected_id = st.radio(
        "Список механизмов",
        options,
        format_func=lambda item_id: name_lookup[item_id],
        key="taxonomy_list_select",
    )
    if selected_id and selected_id != current:
        set_selected_tax_id(selected_id)
    return selected_id


def _label_font_size(text: str) -> int:
    length = len(text)
    if length <= 16:
        return 12
    if length <= 26:
        return 10
    return 9


def _node_color(kind: str) -> str:
    if kind == "root":
        return "#FDE68A"
    if kind == "taxonomy":
        return "#93C5FD"
    if kind == "tag":
        return "#D1D5DB"
    return "#FFFFFF"


CLASSIFIER_GROUP_CONFIG: Dict[str, Dict[str, object]] = {
    "sell": {
        "label": "Что продаём",
        "color": "#2A9D8F",
        "ids": {"access", "attention", "capital", "property", "result", "risk", "time"},
    },
    "to_whom": {
        "label": "Кому",
        "color": "#E9C46A",
        "ids": {"many_people", "market", "platform", "single_client", "state"},
    },
    "value": {
        "label": "Мера ценности",
        "color": "#8E6AC8",
        "ids": {"appreciation", "payout", "percent", "price", "rate", "rent"},
    },
}


def classifier_legend_items() -> List[Tuple[str, str, str]]:
    order = ("sell", "to_whom", "value")
    items: List[Tuple[str, str, str]] = []
    for group in order:
        config = CLASSIFIER_GROUP_CONFIG[group]
        color = str(config["color"])
        items.append((str(config["label"]), color, _darken_hex(color)))
    return items


def _darken_hex(color: str, factor: float = 0.75) -> str:
    value = color.lstrip("#")
    r = int(value[0:2], 16)
    g = int(value[2:4], 16)
    b = int(value[4:6], 16)
    r = max(0, min(255, int(r * factor)))
    g = max(0, min(255, int(g * factor)))
    b = max(0, min(255, int(b * factor)))
    return f"#{r:02X}{g:02X}{b:02X}"


def _text_color_for_background(color: str) -> str:
    value = color.lstrip("#")
    r = int(value[0:2], 16) / 255
    g = int(value[2:4], 16) / 255
    b = int(value[4:6], 16) / 255
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#FFFFFF" if luminance < 0.5 else "#0B0B0B"


def _classifier_tag_style(attrs: Dict[str, object], node_id: str) -> Optional[Dict[str, str]]:
    group = attrs.get("group")
    if not isinstance(group, str):
        group = node_id.split(":", 1)[0] if ":" in node_id else ""
    group = _normalize_classifier_group(group)
    tag_id = node_id.split(":", 1)[1] if ":" in node_id else node_id
    config = CLASSIFIER_GROUP_CONFIG.get(group)
    if not config:
        return None
    ids = config["ids"]
    if not isinstance(ids, set) or tag_id not in ids:
        return None
    color = str(config["color"])
    return {
        "color": color,
        "border_color": _darken_hex(color),
        "font_color": _text_color_for_background(color),
    }


def _normalize_classifier_group(group: str) -> str:
    if group in {"to", "to_whom"}:
        return "to_whom"
    return group


def wrap_label(text: str, max_chars_per_line: int = 12, max_lines: int = 3) -> str:
    words = text.split()
    if not words:
        return ""

    lines: List[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars_per_line:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) >= max_lines:
            break

    if len(lines) < max_lines and current:
        lines.append(current)

    total_words = len(words)
    used_words = len(" ".join(lines).split())
    if used_words < total_words:
        last_line = lines[-1]
        if len(last_line) >= max_chars_per_line:
            last_line = last_line[: max(0, max_chars_per_line - 1)].rstrip()
        last_line = f"{last_line}…" if last_line else "…"
        lines[-1] = last_line

    return "\n".join(lines[:max_lines])


def _taxonomy_tooltip_text(item: TaxonomyItem) -> str:
    sell = ", ".join(item.sell) or "—"
    to_whom = ", ".join(item.to_whom) or "—"
    value = ", ".join(item.value) or "—"
    outside_label = _outside_market_label(item.outside_market)
    return (
        f"{item.name}\n"
        f"{outside_label}\n"
        f"sell: {sell}\n"
        f"to: {to_whom}\n"
        f"value: {value}"
    )


def _strip_anchor_tags(text: str) -> str:
    return re.sub(r"</?a\b[^>]*>", "", text, flags=re.IGNORECASE)


def _strip_markdown_links(text: str) -> str:
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)


def _sanitize_nodes_inplace(nodes: List[Node]) -> List[tuple[str, str, object]]:
    bad: List[tuple[str, str, object]] = []
    for node in nodes:
        for attr in ("url", "href", "link", "target", "openNewTab"):
            if hasattr(node, attr):
                try:
                    setattr(node, attr, None)
                except Exception:
                    pass
            if hasattr(node, "__dict__") and attr in node.__dict__:
                node.__dict__.pop(attr, None)

        if hasattr(node, "label") and isinstance(node.label, str):
            if "<a" in node.label or "href=" in node.label:
                node.label = (
                    node.label.replace("<a", "")
                    .replace("href=", "")
                    .replace("target=", "")
                )
        if hasattr(node, "title") and isinstance(node.title, str):
            if "<a" in node.title or "href=" in node.title:
                node.title = (
                    node.title.replace("<a", "")
                    .replace("href=", "")
                    .replace("target=", "")
                )

        if hasattr(node, "__dict__"):
            for attr in ("url", "href", "link"):
                value = node.__dict__.get(attr)
                if value:
                    bad.append((node.id, attr, value))

    return bad


def build_ways14_agraph_graph(
    app_data: AppData,
    outside_only: bool,
    show_tags: bool,
    selected_tax_id: Optional[str],
    highlighted_node_id: Optional[str],
    allowed_taxonomy_ids: Optional[set[str]] = None,
) -> Tuple[List[Node], List[Edge], Config]:
    graph = build_taxonomy_star(
        app_data,
        include_tags=show_tags,
        outside_only=outside_only,
        allowed_taxonomy_ids=allowed_taxonomy_ids,
    )
    selected_node = f"tax:{selected_tax_id}" if selected_tax_id else None
    taxonomy_items = taxonomy_lookup(app_data)
    nodes: List[Node] = []
    edges: List[Edge] = []

    for node_id, attrs in graph.nodes(data=True):
        kind = attrs.get("kind", "")
        label_text = attrs.get("label", node_id)
        if not isinstance(label_text, str):
            label_text = str(label_text)
        label_text = _strip_markdown_links(_strip_anchor_tags(label_text))
        label_text = (
            label_text.replace("<br />", "\n")
            .replace("<br/>", "\n")
            .replace("<br>", "\n")
        )
        if kind == "tag":
            wrapped = wrap_label(label_text, max_chars_per_line=10, max_lines=2)
            base_size = 40
            font_size = 9
        else:
            wrapped = wrap_label(label_text, max_chars_per_line=12, max_lines=3)
            base_size = 70 if kind == "root" else 62
            font_size = _label_font_size(label_text)

        border_width = 2
        border_color = "#2563EB"
        size = base_size
        background_color = _node_color(kind)
        font_color = "#0b0b0b"
        if kind == "tag":
            tag_style = _classifier_tag_style(attrs, node_id)
            if tag_style:
                background_color = tag_style["color"]
                border_color = tag_style["border_color"]
                font_color = tag_style["font_color"]
        if node_id == selected_node:
            border_width = 4
            border_color = "#1D4ED8"
            size = base_size + 8

        title = attrs.get("title", label_text)
        if not isinstance(title, str):
            title = str(title) if title is not None else label_text
        if kind == "taxonomy" and node_id.startswith("tax:"):
            tax_id = node_id.removeprefix("tax:")
            item = taxonomy_items.get(tax_id)
            if item:
                title = _taxonomy_tooltip_text(item)
        title = _strip_markdown_links(_strip_anchor_tags(title))
        title = (
            title.replace("<br />", "\n")
            .replace("<br/>", "\n")
            .replace("<br>", "\n")
        )

        nodes.append(
            Node(
                id=node_id,
                label=wrapped,
                title=title,
                x=attrs.get("x"),
                y=attrs.get("y"),
                fixed=True,
                size=size,
                shape="circle",
                color={"background": background_color, "border": border_color},
                borderWidth=border_width,
                font={
                    "face": "Segoe UI, Inter, Arial",
                    "size": font_size,
                    "color": font_color,
                    "bold": True,
                    "align": "center",
                },
            )
        )

    for source, target, attrs in graph.edges(data=True):
        kind = attrs.get("kind")
        is_highlighted = highlighted_node_id in {source, target}
        base_color = "#9CA3AF"
        edge_color = "#2E7D32" if is_highlighted else base_color
        base_width = attrs.get("width", 1)
        edge_width = max(base_width + 3, 4) if is_highlighted else base_width
        edges.append(
            Edge(
                source=source,
                target=target,
                color=edge_color,
                width=edge_width,
                arrows="to",
            )
        )

    config = Config(
        width="100%",
        height=720,
        directed=True,
        physics=False,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightBehavior=True,
        highlightColor="#1D4ED8",
    )
    return nodes, edges, config
