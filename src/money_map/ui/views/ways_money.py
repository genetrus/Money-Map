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
    st.markdown("Выберите механизм на карте или через список ниже.")
    controls = st.columns([2, 2, 1])
    show_tags = controls[0].checkbox(
        "Показать теги вторым кольцом",
        value=False,
    )
    outside_only = controls[1].checkbox(
        "Показывать только «вне рынка»",
        value=False,
    )
    controls[1].caption(
        "«Вне рынка» = деньги не за сделку, а по правилам системы или отношениям "
        "(пособия, страховки, подарки и т.п.)."
    )
    if controls[2].button("Обновить граф"):
        components.clear_taxonomy_graph_cache()

    available_items = [
        item for item in data.taxonomy if not outside_only or item.outside_market
    ]
    if not available_items:
        st.info("Нет механизмов для выбранного фильтра.")
        return

    item_lookup = {item.id: item for item in available_items}
    available_ids = [item.id for item in available_items]
    current = st.session_state.get("selected_tax_id")
    if current not in item_lookup:
        current = available_ids[0]
        components.set_selected_tax_id(current)

    if st.session_state.get("taxonomy_map_select") != current:
        st.session_state["taxonomy_map_select"] = current

    def _on_select_change() -> None:
        selected = st.session_state.get("taxonomy_map_select")
        components.set_selected_tax_id(selected)
        st.session_state["active_tab"] = "Справочник"

    st.selectbox(
        "Выберите способ",
        available_ids,
        format_func=lambda item_id: item_lookup[item_id].name,
        key="taxonomy_map_select",
        on_change=_on_select_change,
    )
    st.caption("Выбор через список — основной способ обновления данных и карты.")

    components.render_taxonomy_star_graph(
        data,
        selected_tax_id=current,
        show_tags=show_tags,
        outside_only=outside_only,
    )


def _render_directory(data: AppData) -> None:
    left, right = st.columns([1, 2])
    with left:
        query = st.text_input("Поиск по названию", key="taxonomy_search")
        selected_id = components.render_taxonomy_list(data, query)

    with right:
        components.render_taxonomy_details_card(data, selected_id or st.session_state.get("selected_tax_id"))


def render(data: AppData) -> None:
    st.title("Способы получения денег")
    _ensure_defaults(data)

    st.radio("", ["Карта", "Справочник"], horizontal=True, key="active_tab")

    if st.session_state.get("active_tab") == "Справочник":
        _render_directory(data)
    else:
        _render_map(data)
