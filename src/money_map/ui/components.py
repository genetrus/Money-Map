from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import streamlit as st

from money_map.core.load import load_app_data
from money_map.core.model import AppData, BridgeItem, Cell, PathItem, TaxonomyItem
from money_map.core.query import list_bridges
from money_map.core.validate import validate_app_data


@dataclass
class Filters:
    risk: str
    activity: str
    scalability: str


DEFAULT_PAGE = "Обзор"
PAGES = [
    "Обзор",
    "Матрица",
    "Таксономия",
    "Мосты",
    "Маршруты",
    "Поиск",
    "Классификатор",
    "Граф: 14 способов",
    "Граф",
]


@st.cache_data(show_spinner="Загрузка данных...")
def load_data() -> Tuple[AppData, List[str]]:
    data = load_app_data()
    errors = validate_app_data(data)
    return data, errors


def reset_cache() -> None:
    load_data.clear()


def init_session_state() -> None:
    st.session_state.setdefault("page", DEFAULT_PAGE)
    st.session_state.setdefault("selected_cell", None)
    st.session_state.setdefault("selected_taxonomy", None)
    st.session_state.setdefault("selected_bridge", None)
    st.session_state.setdefault("selected_path", None)
    st.session_state.setdefault("graph_selected_node", None)
    st.session_state.setdefault("graph_selected_bridge", None)
    st.session_state.setdefault("search_query", "")


def set_page(page: str) -> None:
    st.session_state["page"] = page


def set_selected_cell(cell_id: Optional[str]) -> None:
    st.session_state["selected_cell"] = cell_id
    st.session_state["graph_selected_node"] = cell_id


def set_selected_taxonomy(item_id: Optional[str]) -> None:
    st.session_state["selected_taxonomy"] = item_id


def set_selected_bridge(bridge_id: Optional[str]) -> None:
    st.session_state["selected_bridge"] = bridge_id
    st.session_state["graph_selected_bridge"] = bridge_id


def set_selected_path(path_id: Optional[str]) -> None:
    st.session_state["selected_path"] = path_id


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
