from __future__ import annotations

import time
from typing import Any

import streamlit as st

from money_map.core.model import AppData, TaxonomyItem
from money_map.core.taxonomy_graph import build_taxonomy_star
from money_map.ui import components, cyto_graph
from money_map.ui.state import go_to_section


WAYS_TABS = ("Карта", "Справочник")


def _ensure_ways_state_defaults() -> None:
    st.session_state.setdefault("ways_ui_tab", "Карта")
    st.session_state.setdefault("ways_selected_node_id", None)
    st.session_state.setdefault("ways_selected_way_id", None)
    st.session_state.setdefault("ways_highlight_node_id", None)
    st.session_state.setdefault("ways_last_tap", {"node_id": None, "timestamp_ms": 0.0})


def _request_directory_navigation(way_id: str) -> None:
    go_to_section("Способы получения денег", way_id=way_id, tab="Справочник")


def _extract_selected_node_id(selection: object) -> str | None:
    if not isinstance(selection, dict):
        return None

    def _extract(payload: object) -> str | None:
        if isinstance(payload, str):
            return payload or None
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, dict):
                node_id = data.get("id")
                return node_id if isinstance(node_id, str) else None
            node_id = payload.get("id")
            return node_id if isinstance(node_id, str) else None
        return None

    for key in ("nodes", "selectedNodes", "selected_nodes", "node", "selectedNode"):
        payload = selection.get(key)
        if isinstance(payload, list) and payload:
            return _extract(payload[0])
        if isinstance(payload, dict):
            return _extract(payload)
    return None


def _has_selection_keys(selection: object) -> bool:
    if not isinstance(selection, dict):
        return False
    return any(
        key in selection for key in ("nodes", "selectedNodes", "selected_nodes", "node", "selectedNode")
    )


def _node_label(text: str, kind: str) -> str:
    if kind == "tag":
        return components.wrap_label(text, max_chars_per_line=10, max_lines=2)
    return components.wrap_label(text, max_chars_per_line=12, max_lines=3)


def _node_size(text: str, kind: str) -> int:
    if kind == "root":
        return 90
    if kind == "taxonomy":
        return 78 if len(text) > 24 else 72
    if kind == "tag":
        return 48
    return 70


def _node_font_size(text: str, kind: str) -> int:
    if kind == "tag":
        return 9
    return components._label_font_size(text)


def _build_elements(
    data: AppData,
    *,
    outside_only: bool,
    show_tags: bool,
    allowed_taxonomy_ids: set[str] | None,
    highlight_node_id: str | None,
) -> list[dict[str, Any]]:
    graph = build_taxonomy_star(
        data,
        include_tags=show_tags,
        outside_only=outside_only,
        allowed_taxonomy_ids=allowed_taxonomy_ids,
    )
    elements: list[dict[str, Any]] = []

    for node_id, attrs in graph.nodes(data=True):
        kind = attrs.get("kind", "")
        label_text = attrs.get("label", node_id)
        if not isinstance(label_text, str):
            label_text = str(label_text)
        label_text = (
            label_text.replace("<br />", "\n").replace("<br/>", "\n").replace("<br>", "\n")
        )

        background_color = components._node_color(kind)
        border_color = components._darken_hex(background_color)
        font_color = components._text_color_for_background(background_color)
        border_width = 2
        if kind == "tag":
            tag_style = components._classifier_tag_style(attrs, node_id)
            if tag_style:
                background_color = tag_style["color"]
                border_color = tag_style["border_color"]
                font_color = tag_style["font_color"]

        node_size = _node_size(label_text, kind)
        elements.append(
            {
                "data": {
                    "id": node_id,
                    "label": _node_label(label_text, kind),
                    "color": background_color,
                    "border_color": border_color,
                    "border_width": border_width,
                    "font_color": font_color,
                    "font_size": _node_font_size(label_text, kind),
                    "size": node_size,
                    "text_max_width": max(40, node_size - 10),
                },
                "position": {"x": attrs.get("x", 0), "y": attrs.get("y", 0)},
                "classes": kind,
            }
        )

    for source, target, attrs in graph.edges(data=True):
        edge_id = f"{source}__{target}"
        classes = []
        if highlight_node_id:
            if highlight_node_id in {source, target}:
                classes.append("highlighted")
            else:
                classes.append("dimmed")
        elements.append(
            {
                "data": {
                    "id": edge_id,
                    "source": source,
                    "target": target,
                    "width": max(1, int(attrs.get("width", 1))),
                },
                "classes": " ".join(classes),
            }
        )
    return elements


def _stylesheet() -> list[dict[str, Any]]:
    return [
        {
            "selector": "node",
            "style": {
                "label": "data(label)",
                "text-valign": "center",
                "text-halign": "center",
                "text-wrap": "wrap",
                "text-max-width": "data(text_max_width)",
                "font-size": "data(font_size)",
                "font-family": "Segoe UI, Inter, Arial",
                "color": "data(font_color)",
                "background-color": "data(color)",
                "border-color": "data(border_color)",
                "border-width": "data(border_width)",
                "width": "data(size)",
                "height": "data(size)",
            },
        },
        {
            "selector": "edge",
            "style": {
                "line-color": "#94A3B8",
                "target-arrow-color": "#94A3B8",
                "target-arrow-shape": "triangle",
                "curve-style": "bezier",
                "width": "data(width)",
            },
        },
        {
            "selector": ".highlighted",
            "style": {
                "line-color": "#2E7D32",
                "target-arrow-color": "#2E7D32",
                "width": 4,
                "opacity": 1,
            },
        },
        {
            "selector": ".dimmed",
            "style": {"opacity": 0.2},
        },
    ]


def _render_map(
    data: AppData,
    filtered_items: list[TaxonomyItem],
    allowed_taxonomy_ids: set[str],
    outside_only: bool,
) -> None:
    st.markdown(
        "Двойной клик по синему кружку откроет справочник. "
        "Одинарный клик подсветит связи."
    )
    controls = st.columns([2, 2])
    show_tags = controls[0].checkbox(
        "Показать классификаторы вторым кольцом",
        value=False,
    )
    controls[1].caption(
        "Фильтр «вне рынка» применяется ко всей странице.",
    )
    if show_tags:
        legend_items = components.classifier_legend_items()
        legend_html = " ".join(
            (
                "<span style='display:inline-flex;align-items:center;"
                "margin-right:16px;gap:6px;'>"
                f"<span style='width:10px;height:10px;border-radius:50%;"
                f"background:{color};border:1px solid {border};display:inline-block;'></span>"
                f"<span>{label}</span>"
                "</span>"
            )
            for label, color, border in legend_items
        )
        st.markdown(legend_html, unsafe_allow_html=True)
    available_items = [
        item
        for item in filtered_items
        if not outside_only or item.outside_market
    ]
    if not available_items:
        st.info("Ничего не найдено по фильтрам.")
        return

    available_ids = [item.id for item in available_items]
    current = st.session_state.get("selected_way_id")
    if current not in available_ids:
        current = available_ids[0]

    if st.session_state.get("ways_highlight_node_id") is None and current:
        st.session_state["ways_highlight_node_id"] = f"tax:{current}"
        st.session_state["ways_selected_way_id"] = current

    highlight_node_id = st.session_state.get("ways_highlight_node_id")
    elements = _build_elements(
        data,
        outside_only=outside_only,
        show_tags=show_tags,
        allowed_taxonomy_ids=allowed_taxonomy_ids,
        highlight_node_id=highlight_node_id,
    )

    selection = cyto_graph.render_cytoscape(
        elements,
        _stylesheet(),
        layout={"name": "preset", "fit": True, "padding": 30},
        height="720px",
        selection_type="single",
    )
    selected_node_id = _extract_selected_node_id(selection)
    skip_processing = False
    if st.session_state.pop("ways_ignore_next_selection", False):
        if selected_node_id == st.session_state.get("ways_selected_node_id"):
            skip_processing = True

    if selected_node_id and not skip_processing:
        previous_selected = st.session_state.get("ways_selected_node_id")
        previous_highlight = st.session_state.get("ways_highlight_node_id")
        st.session_state["ways_selected_node_id"] = selected_node_id
        st.session_state["ways_highlight_node_id"] = selected_node_id
        if selected_node_id.startswith("tax:"):
            selected_way_id = selected_node_id.removeprefix("tax:")
            if selected_way_id in available_ids:
                st.session_state["selected_way_id"] = selected_way_id
                st.session_state["selected_tax_id"] = selected_way_id
                st.session_state["ways_selected_way_id"] = selected_way_id
        else:
            st.session_state["ways_selected_way_id"] = None

        now_ms = time.monotonic() * 1000
        last_tap = st.session_state.get("ways_last_tap", {"node_id": None, "timestamp_ms": 0.0})
        last_id = last_tap.get("node_id")
        last_ts = float(last_tap.get("timestamp_ms", 0.0))
        is_double = selected_node_id == last_id and (now_ms - last_ts) <= 300
        st.session_state["ways_last_tap"] = {"node_id": selected_node_id, "timestamp_ms": now_ms}
        if is_double and selected_node_id.startswith("tax:"):
            way_id = selected_node_id.removeprefix("tax:")
            _request_directory_navigation(way_id)
        elif selected_node_id != previous_selected or previous_highlight != selected_node_id:
            st.session_state["ways_ignore_next_selection"] = True
            st.rerun()
    elif _has_selection_keys(selection) and not skip_processing:
        if st.session_state.get("ways_highlight_node_id") is not None:
            st.session_state["ways_highlight_node_id"] = None
            st.session_state["ways_selected_node_id"] = None
            st.session_state["ways_selected_way_id"] = None
            st.session_state["ways_ignore_next_selection"] = True
            st.rerun()

    if st.session_state.get("ways_selected_way_id"):
        if st.button("Открыть в справочнике", key="ways-open-directory"):
            _request_directory_navigation(st.session_state["ways_selected_way_id"])




def _render_directory(
    data: AppData,
    filtered_items: list[TaxonomyItem],
    filters: components.Filters,
    outside_only: bool,
) -> None:
    items = sorted(filtered_items, key=lambda item: item.name)
    if not items:
        st.info("Нет подходящих способов.")
        return

    id_to_name = {item.id: item.name for item in items}
    options = [item.id for item in items]
    selected = st.session_state.get("selected_way_id")
    if selected not in options:
        selected = options[0]
        st.session_state["selected_way_id"] = selected
        st.session_state["selected_tax_id"] = selected

    if st.session_state.get("ways_directory_choice") not in options:
        st.session_state["ways_directory_choice"] = selected

    def _sync_directory_choice() -> None:
        st.session_state["selected_way_id"] = st.session_state.get("ways_directory_choice")
        st.session_state["selected_tax_id"] = st.session_state.get("selected_way_id")

    def _sync_selectbox_choice() -> None:
        st.session_state["ways_directory_choice"] = st.session_state.get("selected_way_id")

    st.radio(
        "Список механизмов",
        options,
        key="ways_directory_choice",
        format_func=lambda item_id: id_to_name[item_id],
        on_change=_sync_directory_choice,
    )
    st.selectbox(
        "Быстрый поиск по списку",
        options,
        key="selected_way_id",
        format_func=lambda item_id: id_to_name[item_id],
        on_change=_sync_selectbox_choice,
    )
    selected_way_id = st.session_state.get("selected_way_id")
    if selected_way_id:
        st.session_state["ways_highlight_node_id"] = f"tax:{selected_way_id}"
        st.session_state["ways_selected_way_id"] = selected_way_id
    components.render_taxonomy_details_card(
        data,
        st.session_state.get("selected_way_id"),
        filters,
        outside_only,
    )


def render(data: AppData, filters: components.Filters) -> None:
    _ensure_ways_state_defaults()
    payload = st.session_state.get("nav_payload")
    if isinstance(payload, dict) and payload.get("section") == "Способы получения денег":
        tab = payload.get("tab")
        way_id = payload.get("way_id")
        if isinstance(tab, str) and tab in WAYS_TABS:
            st.session_state["ways_ui_tab"] = tab
        if isinstance(way_id, str):
            st.session_state["selected_way_id"] = way_id
            st.session_state["selected_tax_id"] = way_id
            st.session_state["ways_selected_way_id"] = way_id
        st.session_state["nav_payload"] = None

    if st.session_state.get("ways_ui_tab") not in WAYS_TABS:
        st.session_state["ways_ui_tab"] = "Карта"

    st.title("Способы получения денег")
    outside_only = st.checkbox(
        "Показывать только «вне рынка» (пособия/страховки/подарки)",
        key="ways_outside_only",
        help=(
            "«Вне рынка» = деньги не за сделку/продажу, "
            "а по правилам системы или отношениям."
        ),
    )
    filtered_items = components.apply_global_filters_to_ways(data.taxonomy, filters, data)
    filtered_items = [item for item in filtered_items if not outside_only or item.outside_market]
    filtered_taxonomy_ids = [item.id for item in filtered_items]

    current = st.session_state.get("selected_way_id")
    if current not in filtered_taxonomy_ids:
        st.session_state["selected_way_id"] = filtered_taxonomy_ids[0] if filtered_taxonomy_ids else None
    st.session_state["selected_tax_id"] = st.session_state.get("selected_way_id")

    st.radio("", WAYS_TABS, horizontal=True, key="ways_ui_tab")

    if st.session_state.get("ways_ui_tab") == "Справочник":
        _render_directory(data, filtered_items, filters, outside_only)
    else:
        _render_map(data, filtered_items, set(filtered_taxonomy_ids), outside_only)
