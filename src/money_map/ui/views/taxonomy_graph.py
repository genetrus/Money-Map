from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components_html

from money_map.core.model import AppData
from money_map.render.taxonomy_graph import render_taxonomy_graph_html
from money_map.ui import components


@st.cache_data(show_spinner="Формирование графа...")
def _build_graph_html(
    data: AppData,
    include_tags: bool,
    outside_only: bool,
) -> str:
    return render_taxonomy_graph_html(
        data,
        include_tags=include_tags,
        outside_only=outside_only,
        height="720px",
        width="100%",
    )


def render(data: AppData) -> None:
    st.title("Граф: 14 способов")
    st.markdown("Визуализация механизмов получения денег и связанных тегов.")
    st.caption("Кликните по узлу вокруг центра — ниже появятся детали выбранного способа.")

    controls = st.columns([2, 2, 1])
    include_tags = controls[0].checkbox(
        "Показать теги (sell/to_whom/value) вторым кольцом",
        value=False,
    )
    outside_only = controls[1].checkbox(
        "Показывать только «вне рынка» (пособия/выплаты/подарки)",
        value=False,
    )
    controls[1].caption(
        "«Вне рынка» = деньги не за сделку/продажу, а по правилам системы или отношениям "
        "(пособия, страховки, подарки и т.п.)."
    )
    if controls[2].button("Обновить"):
        _build_graph_html.clear()

    html = _build_graph_html(data, include_tags, outside_only)
    components_html.html(html, height=760, scrolling=True)

    st.markdown("### Детали")
    available_items = [
        item for item in data.taxonomy if not outside_only or item.outside_market
    ]
    if not available_items:
        st.info("Нет механизмов для выбранного фильтра.")
        return

    item_lookup = {item.id: item for item in available_items}
    available_ids = [item.id for item in available_items]
    selected_current = st.session_state.get("selected_taxonomy")
    selected_index = available_ids.index(selected_current) if selected_current in item_lookup else None
    selected_id = st.selectbox(
        "Механизм",
        available_ids,
        format_func=lambda item_id: item_lookup[item_id].name,
        index=selected_index,
        placeholder="Выберите механизм",
    )
    if selected_id:
        components.set_selected_taxonomy(selected_id)
    components.render_taxonomy_details_card(
        data,
        selected_id,
        components.get_filters(),
        outside_only,
    )
