from __future__ import annotations

import streamlit as st

from money_map.core.model import AppData
from money_map.ui import components


def _ensure_defaults(data: AppData) -> None:
    taxonomy_ids = [item.id for item in data.taxonomy]
    current = st.session_state.get("selected_tax_id")
    if current not in taxonomy_ids:
        st.session_state["selected_tax_id"] = taxonomy_ids[0] if taxonomy_ids else None
    if st.session_state.get("active_tab") not in {"Карта", "Справочник"}:
        st.session_state["active_tab"] = "Карта"


def _render_map(data: AppData) -> None:
    st.markdown(
        "Нажмите на кружок — откроется справочник. "
        "Выбор делается кликом по кружку на карте."
    )
    controls = st.columns([2, 2])
    show_tags = controls[0].checkbox(
        "Показать теги вторым кольцом",
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
    available_items = [
        item for item in data.taxonomy if not outside_only or item.outside_market
    ]
    if not available_items:
        st.info("Нет механизмов для выбранного фильтра.")
        return

    available_ids = [item.id for item in available_items]
    current = st.session_state.get("selected_tax_id")
    if current not in available_ids:
        current = available_ids[0]
        components.set_selected_tax_id(current)

    nodes, edges = components.build_ways14_nodes_edges(
        data,
        show_tags=show_tags,
        outside_only=outside_only,
        selected_tax_id=current,
    )
    selected_node = components.render_ways14_agraph(nodes, edges)
    if selected_node and isinstance(selected_node, str) and selected_node.startswith("tax:"):
        selected_tax_id = selected_node.removeprefix("tax:")
        if selected_tax_id != st.session_state.get("selected_tax_id"):
            st.session_state["selected_tax_id"] = selected_tax_id
            st.session_state["active_tab"] = "Справочник"
            st.rerun()


def _render_directory(data: AppData) -> None:
    items = sorted(data.taxonomy, key=lambda item: item.name)
    if not items:
        st.info("Нет механизмов для отображения.")
        return

    id_to_name = {item.id: item.name for item in items}
    options = [item.id for item in items]
    current = st.session_state.get("selected_tax_id")
    index = options.index(current) if current in options else 0
    st.selectbox(
        "Выберите механизм",
        options,
        format_func=lambda item_id: id_to_name[item_id],
        key="selected_tax_id",
        index=index,
    )
    components.render_taxonomy_details_card(data, st.session_state.get("selected_tax_id"))


def render(data: AppData) -> None:
    st.title("Способы получения денег")
    _ensure_defaults(data)

    st.radio("", ["Карта", "Справочник"], horizontal=True, key="active_tab")

    if st.session_state.get("active_tab") == "Справочник":
        _render_directory(data)
    else:
        _render_map(data)
