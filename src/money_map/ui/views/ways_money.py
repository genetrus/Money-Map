from __future__ import annotations

import time

import streamlit as st
from streamlit_agraph import agraph

from money_map.core.model import AppData, TaxonomyItem
from money_map.ui import components


def _render_map(
    data: AppData,
    filtered_items: list[TaxonomyItem],
    allowed_taxonomy_ids: set[str],
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
    outside_only = controls[1].checkbox(
        "Показывать только «вне рынка» (пособия/страховки/подарки)",
        value=False,
        help=(
            "«Вне рынка» = деньги не за сделку/продажу, "
            "а по правилам системы или отношениям."
        ),
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
    current = st.session_state.get("selected_tax_id")
    if current not in available_ids:
        current = available_ids[0]

    nodes, edges, config = components.build_ways14_agraph_graph(
        data,
        outside_only=outside_only,
        show_tags=show_tags,
        selected_tax_id=current,
        highlighted_node_id=st.session_state.get("ways_highlight_node_id"),
        allowed_taxonomy_ids=allowed_taxonomy_ids,
    )
    result = agraph(nodes=nodes, edges=edges, config=config)
    clicked_id = None
    if isinstance(result, dict):
        if result.get("selected_node"):
            clicked_id = result["selected_node"]
        elif result.get("selectedNodes"):
            clicked_id = result["selectedNodes"][0]
        elif result.get("nodes") is not None:
            nodes_value = result.get("nodes", [])
            if nodes_value:
                first_node = nodes_value[0]
                clicked_id = first_node.get("id") if isinstance(first_node, dict) else first_node
    elif isinstance(result, str):
        clicked_id = result

    if clicked_id and isinstance(clicked_id, str):
        now = time.monotonic()
        last_click_ts = st.session_state.get("ways_last_click_ts")
        last_click_id = st.session_state.get("ways_last_click_id")
        is_double_click = (
            last_click_id == clicked_id
            and last_click_ts is not None
            and now - last_click_ts <= 0.9
        )
        st.session_state["ways_last_click_ts"] = now
        st.session_state["ways_last_click_id"] = clicked_id
        if st.session_state.get("ways_highlight_node_id") != clicked_id:
            st.session_state["ways_highlight_node_id"] = clicked_id
            if not is_double_click:
                st.rerun()
        if is_double_click and clicked_id.startswith("tax:"):
            selected_tax_id = clicked_id.removeprefix("tax:")
            st.session_state["pending_selected_tax_id"] = selected_tax_id
            st.session_state["request_tab"] = "Справочник"
            st.session_state["last_click_id"] = clicked_id
            st.rerun()
    elif clicked_id is None:
        if st.session_state.get("ways_highlight_node_id") is not None:
            st.session_state["ways_highlight_node_id"] = None
            st.rerun()

    st.session_state["last_click_id"] = clicked_id
    st.caption(f"Последний клик: {st.session_state.get('last_click_id') or '—'}")


def _render_directory(
    data: AppData,
    filtered_items: list[TaxonomyItem],
) -> None:
    items = sorted(filtered_items, key=lambda item: item.name)
    if not items:
        st.info("Нет подходящих способов.")
        return

    id_to_name = {item.id: item.name for item in items}
    options = [item.id for item in items]
    st.selectbox(
        "Выберите механизм",
        options,
        key="selected_tax_id",
        format_func=lambda item_id: id_to_name[item_id],
    )
    components.render_taxonomy_details_card(data, st.session_state.get("selected_tax_id"))


def render(data: AppData, filters: components.Filters) -> None:
    pending_tax_id = st.session_state.get("pending_selected_tax_id")
    if pending_tax_id:
        st.session_state["selected_tax_id"] = pending_tax_id
        st.session_state["pending_selected_tax_id"] = None

    requested_tab = st.session_state.get("request_tab")
    if requested_tab:
        st.session_state["active_tab"] = requested_tab
        st.session_state["request_tab"] = None

    st.title("Способы получения денег")
    allowed_cells = components.get_allowed_cells_from_global_filters(data, filters)
    filtered_taxonomy_ids = components.filter_taxonomy_by_cells(data.taxonomy, allowed_cells)
    filtered_items = [item for item in data.taxonomy if item.id in filtered_taxonomy_ids]

    current = st.session_state.get("selected_tax_id")
    if current not in filtered_taxonomy_ids:
        st.session_state["selected_tax_id"] = filtered_taxonomy_ids[0] if filtered_taxonomy_ids else None
    if st.session_state.get("active_tab") not in {"Карта", "Справочник"}:
        st.session_state["active_tab"] = "Карта"

    st.radio("", ["Карта", "Справочник"], horizontal=True, key="active_tab")

    if st.session_state.get("active_tab") == "Справочник":
        _render_directory(data, filtered_items)
    else:
        _render_map(data, filtered_items, set(filtered_taxonomy_ids))
