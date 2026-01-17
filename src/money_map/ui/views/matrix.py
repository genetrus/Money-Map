from __future__ import annotations

from typing import Optional

import streamlit as st

from money_map.core.model import AppData, Cell
from money_map.core.query import list_bridges
from money_map.ui import components


def _find_cell(data: AppData, risk: str, activity: str, scalability: str) -> Optional[Cell]:
    for cell in data.cells:
        if (
            cell.risk == risk
            and cell.activity == activity
            and cell.scalability == scalability
        ):
            return cell
    return None


def render(data: AppData, filters: components.Filters) -> None:
    st.title("Матрица 2×2×2")
    st.markdown("Нажмите на ячейку, чтобы открыть детали и связанные мосты.")

    focus_cell = st.session_state.get("matrix_focus_cell")
    if focus_cell and st.session_state.get("selected_cell") != focus_cell:
        components.set_selected_cell(focus_cell)

    for risk_key, risk_label in [("low", "Низкий риск"), ("high", "Высокий риск")]:
        if filters.risk != "all" and filters.risk != risk_key:
            continue
        st.subheader(risk_label)
        st.markdown("**Активность × Масштабируемость**")

        for activity_key, activity_label in [("active", "Активно"), ("passive", "Пассивно")]:
            row_cols = st.columns(2)
            for idx, scale_key in enumerate(["linear", "scalable"]):
                cell = _find_cell(data, risk_key, activity_key, scale_key)
                with row_cols[idx]:
                    if not cell:
                        st.info("Ячейка не найдена")
                        continue
                    if filters.activity != "all" and cell.activity != filters.activity:
                        st.caption("Скрыто фильтром активности")
                        continue
                    if filters.scalability != "all" and cell.scalability != filters.scalability:
                        st.caption("Скрыто фильтром масштабируемости")
                        continue
                    with st.container(border=cell.id == focus_cell):
                        st.markdown(components.render_cell_card(cell))
                        if cell.id == focus_cell:
                            st.caption("Фокусная ячейка")
                    if st.button(
                        f"Открыть {cell.id}",
                        key=f"cell-{cell.id}",
                        use_container_width=True,
                    ):
                        components.set_selected_cell(cell.id)
            st.divider()

    selected_id = st.session_state.get("selected_cell")
    if not selected_id:
        st.info("Выберите ячейку, чтобы увидеть детали.")
        return

    cell = components.cell_lookup(data).get(selected_id)
    if not cell:
        st.warning("Выбранная ячейка не найдена.")
        return

    st.subheader(f"Детали ячейки {cell.id}")
    st.markdown(f"**{cell.label}**")
    st.write(cell.short)
    st.write("Примеры:")
    for example in cell.examples:
        st.write(f"- {example}")

    outgoing = list_bridges(data, from_cell=cell.id)
    st.markdown("#### Исходящие мосты")
    if not outgoing:
        st.caption("Исходящих мостов нет.")
    else:
        for bridge in outgoing:
            st.markdown(
                f"- **{bridge.name}** ({bridge.from_cell} → {bridge.to_cell}) — {bridge.notes}"
            )
            if bridge.checks:
                st.caption("Проверки: " + ", ".join(bridge.checks))

    relevant_sell = {
        tag
        for tag, mapping in data.mappings.sell_items.items()
        if mapping.typical_cells and cell.id in mapping.typical_cells
    }
    relevant_value = {
        tag
        for tag, mapping in data.mappings.value_measures.items()
        if mapping.typical_cells and cell.id in mapping.typical_cells
    }
    related_taxonomy = [
        item
        for item in data.taxonomy
        if cell.id in item.typical_cells
        or relevant_sell.intersection(item.sell)
        or relevant_value.intersection(item.value)
    ]
    st.markdown("#### Связанная таксономия")
    if not related_taxonomy:
        st.caption("Нет связанных механизмов.")
    else:
        for item in related_taxonomy:
            if st.button(
                f"{item.name} ({item.id})",
                key=f"tax-{cell.id}-{item.id}",
            ):
                components.set_selected_taxonomy(item.id)
                components.set_page("Таксономия")

    st.markdown("#### Мини-диаграмма")
    st.code(components.ascii_focus_diagram(cell.id, outgoing), language="text")
