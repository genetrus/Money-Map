from __future__ import annotations

import time

import streamlit as st
from streamlit_agraph import agraph

from money_map.core.model import AppData, TaxonomyItem
from money_map.ui import components


def _get_clicked_id(result: object) -> str | None:
    if isinstance(result, str):
        return result or None
    if not isinstance(result, dict):
        return None

    def _extract_from_value(value: object) -> str | None:
        if isinstance(value, str):
            return value or None
        if isinstance(value, dict):
            node_id = value.get("id")
            return node_id if isinstance(node_id, str) else None
        if isinstance(value, list) and value:
            return _extract_from_value(value[0])
        return None

    for key in ("selected_node", "selectedNodes", "selected_nodes", "selectedNode", "node"):
        node_id = _extract_from_value(result.get(key))
        if node_id:
            return node_id

    return _extract_from_value(result.get("nodes"))


def _render_map(
    data: AppData,
    filtered_items: list[TaxonomyItem],
    allowed_taxonomy_ids: set[str],
    outside_only: bool,
) -> None:
    st.markdown(
        "Двойной клик по кружку откроет справочник. "
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

    nodes, edges, config = components.build_ways14_agraph_graph(
        data,
        outside_only=outside_only,
        show_tags=show_tags,
        selected_tax_id=current,
        highlighted_node_id=st.session_state.get("ways_map_focus_id"),
        allowed_taxonomy_ids=allowed_taxonomy_ids,
    )
    components._sanitize_nodes_inplace(nodes)
    result = agraph(nodes=nodes, edges=edges, config=config)
    clicked_id = _get_clicked_id(result)
    has_selection_keys = isinstance(result, dict) and any(
        key in result for key in ("selected_node", "selectedNodes", "selected_nodes", "selectedNode", "node", "nodes")
    )
    dbl = False
    if clicked_id is not None:
        now = time.monotonic()
        last_click_id = st.session_state.get("ways_last_click_id")
        last_click_ts = st.session_state.get("ways_last_click_ts", 0.0) or 0.0
        dbl = (
            clicked_id == last_click_id
            and (now - last_click_ts) <= 0.6
        )
        st.session_state["ways_last_click_id"] = clicked_id
        st.session_state["ways_last_click_ts"] = now

    if clicked_id and isinstance(clicked_id, str):
        st.session_state["ways_map_focus_id"] = clicked_id
        if dbl and clicked_id.startswith("tax:"):
            selected_way_id = clicked_id.removeprefix("tax:")
            st.session_state["selected_way_id"] = selected_way_id
            st.session_state["selected_tax_id"] = selected_way_id
            st.session_state["ways_tab"] = "Справочник"
            st.rerun()
        if not dbl:
            st.rerun()
    elif clicked_id is None and has_selection_keys:
        if st.session_state.get("ways_map_focus_id") is not None:
            st.session_state["ways_map_focus_id"] = None
            st.rerun()

    if st.button("Сбросить подсветку", key="ways-map-reset-highlight"):
        st.session_state["ways_map_focus_id"] = None
        st.rerun()




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
    if st.session_state.get("selected_way_id") not in options:
        st.session_state["selected_way_id"] = options[0]
        st.session_state["selected_tax_id"] = options[0]
    st.selectbox(
        "Выберите механизм",
        options,
        key="selected_way_id",
        format_func=lambda item_id: id_to_name[item_id],
    )
    components.render_taxonomy_details_card(
        data,
        st.session_state.get("selected_way_id"),
        filters,
        outside_only,
    )


def render(data: AppData, filters: components.Filters) -> None:
    payload = st.session_state.get("nav_payload")
    if isinstance(payload, dict) and payload.get("section") == "Способы получения денег":
        way_id = payload.get("way_id")
        tab = payload.get("tab")
        if isinstance(way_id, str):
            st.session_state["selected_way_id"] = way_id
            st.session_state["selected_tax_id"] = way_id
        if isinstance(tab, str):
            st.session_state["ways_tab"] = tab
        st.session_state["nav_payload"] = None

    if st.session_state.get("ways_tab") not in {"Карта", "Справочник"}:
        st.session_state["ways_tab"] = "Карта"

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

    st.radio("", ["Карта", "Справочник"], horizontal=True, key="ways_tab")

    if st.session_state.get("ways_tab") == "Справочник":
        _render_directory(data, filtered_items, filters, outside_only)
    else:
        _render_map(data, filtered_items, set(filtered_taxonomy_ids), outside_only)
