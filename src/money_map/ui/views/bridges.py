from __future__ import annotations

import streamlit as st

from money_map.core.model import AppData
from money_map.ui import components
from money_map.ui.state import go_to_section


def render(data: AppData, filters: components.Filters) -> None:
    st.title("Мосты")
    st.markdown("Фильтруйте мосты и открывайте детали по каждому переходу.")

    cell_ids = [cell.id for cell in data.cells]
    mechanisms = sorted({mech for bridge in data.bridges for mech in bridge.mechanisms})

    filter_cols = st.columns(4)
    from_cell = filter_cols[0].selectbox("Откуда", ["Все"] + cell_ids)
    to_cell = filter_cols[1].selectbox("Куда", ["Все"] + cell_ids)
    mechanism = filter_cols[2].selectbox("Механизм", ["Все"] + mechanisms)
    danger_only = filter_cols[3].checkbox("Только опасные")

    lookup = components.cell_lookup(data)

    def matches_bridge(bridge) -> bool:
        if from_cell != "Все" and bridge.from_cell != from_cell:
            return False
        if to_cell != "Все" and bridge.to_cell != to_cell:
            return False
        if mechanism != "Все" and mechanism not in bridge.mechanisms:
            return False
        if danger_only and not components.danger_bridge(bridge):
            return False
        if filters.risk != "all":
            from_risk = lookup.get(bridge.from_cell).risk
            to_risk = lookup.get(bridge.to_cell).risk
            if from_risk != filters.risk and to_risk != filters.risk:
                return False
        if filters.activity != "all":
            from_activity = lookup.get(bridge.from_cell).activity
            to_activity = lookup.get(bridge.to_cell).activity
            if from_activity != filters.activity and to_activity != filters.activity:
                return False
        if filters.scalability != "all":
            from_scale = lookup.get(bridge.from_cell).scalability
            to_scale = lookup.get(bridge.to_cell).scalability
            if from_scale != filters.scalability and to_scale != filters.scalability:
                return False
        return True

    filtered = [bridge for bridge in data.bridges if matches_bridge(bridge)]
    if not filtered:
        st.warning("По заданным фильтрам мосты не найдены.")
        return

    for bridge in filtered:
        st.markdown(
            f"**{bridge.from_cell} → {bridge.to_cell}** · {bridge.name}\n\n{bridge.notes}"
        )
        if bridge.mechanisms:
            st.caption("Механизмы: " + ", ".join(bridge.mechanisms))
        if bridge.checks:
            st.caption("Проверки: " + ", ".join(bridge.checks))
        if st.button(
            "Выбрать мост",
            key=f"bridge-select-{bridge.id}",
            use_container_width=True,
        ):
            components.set_selected_bridge(bridge.id)
            components.set_page("Граф")
        st.divider()

    selected_id = st.session_state.get("selected_bridge")
    if selected_id:
        selected = next((bridge for bridge in data.bridges if bridge.id == selected_id), None)
        if selected:
            st.subheader("Выбранный мост")
            st.write(f"{selected.from_cell} → {selected.to_cell}")
            st.write(selected.name)
            st.write(selected.notes)

            st.markdown("#### Варианты, где этот мост наиболее типичен")
            variants = (
                data.variants_by_cell_id.get(selected.from_cell, [])
                + data.variants_by_cell_id.get(selected.to_cell, [])
            )
            variants = components.apply_global_filters_to_variants(variants, filters)
            seen: set[str] = set()
            deduped = []
            for variant in variants:
                if variant.id not in seen:
                    seen.add(variant.id)
                    deduped.append(variant)
            if not deduped:
                st.caption("Нет подходящих вариантов.")
            else:
                for variant in deduped[:6]:
                    if st.button(
                        f"{variant.title} · {variant.kind}",
                        key=f"bridge-variant-{selected.id}-{variant.id}",
                    ):
                        go_to_section(
                            "Варианты (конкретика)",
                            variant_id=variant.id,
                            way_id=variant.primary_way_id,
                        )
