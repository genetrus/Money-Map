from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components_html
from streamlit_agraph import Config, Edge, Node

from money_map.core.load import load_app_data
from money_map.core.model import AppData, BridgeItem, Cell, PathItem, TaxonomyItem
from money_map.core.query import list_bridges
from money_map.core.taxonomy_graph import build_taxonomy_star
from money_map.core.validate import validate_app_data
from money_map.render.taxonomy_graph import render_taxonomy_graph_html


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
    "Поиск",
    "Классификатор",
    "Граф",
    "Способы получения денег",
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
    st.session_state.setdefault("selected_tax_id", None)
    st.session_state.setdefault("selected_bridge", None)
    st.session_state.setdefault("selected_path", None)
    st.session_state.setdefault("graph_selected_node", None)
    st.session_state.setdefault("graph_selected_bridge", None)
    st.session_state.setdefault("search_query", "")
    st.session_state.setdefault("active_tab", "Карта")
    st.session_state.setdefault("last_click_id", None)
    st.session_state.setdefault("matrix_focus_cell", None)
    st.session_state.setdefault("ways_highlight_node_id", None)
    st.session_state.setdefault("ways_last_click_id", None)
    st.session_state.setdefault("ways_last_click_ts", None)
    st.session_state.setdefault("ways_last_click_is_double", False)


def set_page(page: str) -> None:
    st.session_state["page"] = page


def set_selected_cell(cell_id: Optional[str]) -> None:
    st.session_state["selected_cell"] = cell_id
    st.session_state["graph_selected_node"] = cell_id


def set_selected_taxonomy(item_id: Optional[str]) -> None:
    st.session_state["selected_taxonomy"] = item_id


def set_selected_tax_id(item_id: Optional[str]) -> None:
    st.session_state["selected_tax_id"] = item_id
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


def get_allowed_cells_from_global_filters(data: AppData, filters: Filters) -> set[str]:
    return {cell.id for cell in filter_cells(data.cells, filters)}


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


def render_taxonomy_details_card(app_data: AppData, tax_id: Optional[str]) -> None:
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
                        st.session_state["request_nav_section"] = "Матрица"
                        st.session_state["request_matrix_focus_cell"] = cell_id
                        st.rerun()
                with row[1]:
                    st.markdown(summary)

        st.markdown("#### Связанные мосты")
        bridges = taxonomy_related_bridges(app_data, item)
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
        f"{item.name}<br>"
        f"{outside_label}<br>"
        f"sell: {sell}<br>"
        f"to: {to_whom}<br>"
        f"value: {value}"
    )


def _strip_anchor_tags(text: str) -> str:
    return re.sub(r"</?a\b[^>]*>", "", text, flags=re.IGNORECASE)


def _strip_markdown_links(text: str) -> str:
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)


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
