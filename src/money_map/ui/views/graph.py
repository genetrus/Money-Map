from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components_html
from pyvis.network import Network

from money_map.core.model import AppData
from money_map.render.graphviz import render_graphviz
from money_map.ui import components


def render(data: AppData, filters: components.Filters) -> None:
    st.title("Граф переходов")
    st.markdown("Интерактивный граф ячеек и мостов.")

    lookup = components.cell_lookup(data)
    node_options = [cell.id for cell in data.cells]

    control_cols = st.columns(3)
    show_low = control_cols[0].checkbox("Показывать низкий риск", value=True)
    show_high = control_cols[1].checkbox("Показывать высокий риск", value=True)
    selected_node = control_cols[2].selectbox(
        "Фокус на ячейке",
        ["Нет"] + node_options,
        index=0,
        key="graph_selected_node",
    )

    edge_only_selected = st.checkbox("Показывать только мосты из выбранной ячейки")
    if edge_only_selected and selected_node == "Нет":
        st.info("Выберите ячейку, чтобы ограничить список мостов.")
        edge_only_selected = False

    net = Network(height="600px", width="100%", directed=True, bgcolor="#ffffff")
    included_nodes = set()

    for cell in data.cells:
        if filters.risk != "all" and cell.risk != filters.risk:
            continue
        if filters.activity != "all" and cell.activity != filters.activity:
            continue
        if filters.scalability != "all" and cell.scalability != filters.scalability:
            continue
        color = "#A7F3D0" if cell.risk == "low" else "#FCA5A5"
        net.add_node(cell.id, label=f"{cell.id}\n{cell.label}", color=color)
        included_nodes.add(cell.id)

    selected_bridge = st.session_state.get("selected_bridge")
    for bridge in data.bridges:
        from_cell = lookup.get(bridge.from_cell)
        to_cell = lookup.get(bridge.to_cell)
        if not from_cell or not to_cell:
            continue
        if bridge.from_cell not in included_nodes or bridge.to_cell not in included_nodes:
            continue
        if not show_low and from_cell.risk == "low":
            continue
        if not show_high and from_cell.risk == "high":
            continue
        if edge_only_selected and selected_node != "Нет" and bridge.from_cell != selected_node:
            continue
        color = "#2563EB" if bridge.id == selected_bridge else "#9CA3AF"
        net.add_edge(bridge.from_cell, bridge.to_cell, label=bridge.name, color=color)

    html = net.generate_html()
    components_html.html(html, height=650, scrolling=True)

    st.markdown("### Детали выбранной ячейки")
    if selected_node != "Нет":
        components.set_selected_cell(selected_node)
        cell = lookup.get(selected_node)
        if cell:
            st.markdown(f"**{cell.id} — {cell.label}**")
            st.write(cell.short)
            st.write("Примеры:")
            for example in cell.examples:
                st.write(f"- {example}")
            if st.button("Открыть в матрице", key="graph-open-matrix"):
                components.set_page("Матрица")
        else:
            st.caption("Ячейка не найдена.")
    else:
        st.caption("Выберите ячейку в селекторе выше.")

    st.markdown("### Экспорт DOT")
    if st.button("Сформировать DOT", key="graph-export-dot"):
        st.session_state["dot_export"] = render_graphviz(data)

    if "dot_export" in st.session_state:
        with st.expander("DOT текст", expanded=False):
            st.code(st.session_state["dot_export"], language="text")

    if selected_bridge:
        bridge = next((item for item in data.bridges if item.id == selected_bridge), None)
        if bridge:
            st.markdown("### Выбранный мост")
            st.write(f"{bridge.from_cell} → {bridge.to_cell}")
            st.write(bridge.name)
            st.write(bridge.notes)
