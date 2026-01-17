from __future__ import annotations

import streamlit as st
from streamlit_agraph import agraph

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

    nodes, edges, config = components.build_ways14_agraph_graph(
        data,
        outside_only=outside_only,
        show_tags=show_tags,
        selected_tax_id=current,
    )
    result = agraph(nodes=nodes, edges=edges, config=config)
    clicked_id = None
    if isinstance(result, dict):
        if result.get("selected_node"):
            clicked_id = result["selected_node"]
        elif result.get("selectedNodes"):
            clicked_id = result["selectedNodes"][0]
        elif result.get("nodes"):
            first_node = result["nodes"][0]
            clicked_id = first_node.get("id") if isinstance(first_node, dict) else first_node
    elif isinstance(result, str):
        clicked_id = result

    st.session_state["last_click_id"] = clicked_id
    if clicked_id and isinstance(clicked_id, str) and clicked_id.startswith("tax:"):
        selected_tax_id = clicked_id.removeprefix("tax:")
        if selected_tax_id != st.session_state.get("selected_tax_id"):
            st.session_state["selected_tax_id"] = selected_tax_id
            st.session_state["request_tab"] = "Справочник"
            st.rerun()
    st.caption(f"Последний клик: {st.session_state.get('last_click_id') or '—'}")


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

    if "request_tab" in st.session_state:
        st.session_state["active_tab"] = st.session_state["request_tab"]
        del st.session_state["request_tab"]

    st.radio("", ["Карта", "Справочник"], horizontal=True, key="active_tab")

    if st.session_state.get("active_tab") == "Справочник":
        _render_directory(data)
    else:
        _render_map(data)
