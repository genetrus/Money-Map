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

    controls = st.columns([2, 2, 1])
    include_tags = controls[0].checkbox(
        "Показать теги (sell/to_whom/value) вторым кольцом",
        value=False,
    )
    outside_only = controls[1].checkbox(
        "Показывать только outside_market=true",
        value=False,
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
    selected_default = available_ids[0]
    selected_current = st.session_state.get("selected_taxonomy", selected_default)
    selected_index = available_ids.index(selected_current) if selected_current in item_lookup else 0
    selected_id = st.selectbox(
        "Механизм",
        available_ids,
        format_func=lambda item_id: item_lookup[item_id].name,
        index=selected_index,
    )
    components.set_selected_taxonomy(selected_id)
    item = item_lookup[selected_id]

    st.subheader(item.name)
    st.write(item.description)
    st.markdown("**Продаём:** " + (", ".join(item.sell) or "—"))
    st.markdown("**Кому:** " + (", ".join(item.to_whom) or "—"))
    st.markdown("**Мера ценности:** " + (", ".join(item.value) or "—"))
    st.markdown("**Типовые ячейки:** " + components.format_cells_inline(item.typical_cells))
    st.markdown("**Вне рынка:** " + ("да" if item.outside_market else "нет"))
    st.markdown("**Риск:** " + (item.risk_notes or "—"))
    st.markdown("**Примеры:**")
    for example in item.examples:
        st.write(f"- {example}")

    st.markdown("#### Связанные ячейки")
    cell_lookup = components.cell_lookup(data)
    for cell_id in item.typical_cells:
        cell = cell_lookup.get(cell_id)
        if cell:
            with st.expander(f"{cell.id} — {cell.label}", expanded=False):
                st.markdown(components.render_cell_card(cell))

    st.markdown("#### Связанные мосты")
    bridges = components.taxonomy_related_bridges(data, item)
    if not bridges:
        st.caption("Нет связанных мостов.")
    else:
        for bridge in bridges:
            if st.button(
                f"{bridge.name} ({bridge.from_cell} → {bridge.to_cell})",
                key=f"tax-star-bridge-{item.id}-{bridge.id}",
            ):
                components.set_selected_bridge(bridge.id)
                components.set_page("Мосты")

    st.markdown("#### Связанные маршруты")
    paths = components.taxonomy_related_paths(data, item)
    if not paths:
        st.caption("Нет связанных маршрутов.")
    else:
        for path in paths:
            if st.button(
                f"{path.name} ({components.ascii_path(path)})",
                key=f"tax-star-path-{item.id}-{path.id}",
            ):
                components.set_selected_path(path.id)
                components.set_page("Маршруты")
