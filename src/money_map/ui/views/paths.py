from __future__ import annotations

import streamlit as st

from money_map.core.model import AppData
from money_map.ui import components
from money_map.ui.state import go_to_section


def render(data: AppData, filters: components.Filters) -> None:
    st.title("Маршруты")
    st.markdown("Выберите маршрут и изучите пошаговые переходы.")

    def _clear_bridge_context() -> None:
        st.session_state["selected_bridge_id"] = None

    selected_bridge_id = st.session_state.get("selected_bridge_id")
    bridge_lookup = {bridge.id: bridge for bridge in data.bridges}
    bridge = bridge_lookup.get(selected_bridge_id) if selected_bridge_id else None

    paths = data.paths
    if bridge:
        paths = [
            path
            for path in data.paths
            if bridge.from_cell in path.sequence
            and bridge.to_cell in path.sequence
            and path.sequence.index(bridge.from_cell) < path.sequence.index(bridge.to_cell)
        ]
        context_cols = st.columns([4, 1])
        context_cols[0].markdown(f"**Контекст:** `Мост: {bridge.name}`")
        context_cols[1].button(
            "Сбросить",
            key="paths-clear-bridge",
            on_click=_clear_bridge_context,
        )
        if not paths:
            st.info("Нет маршрутов для выбранного моста.")
            return

    left, right = st.columns([1, 2])

    available_ids = {path.id for path in paths}
    selected_id = st.session_state.get("selected_route_id") or st.session_state.get("selected_path")
    if selected_id not in available_ids:
        st.session_state["selected_route_id"] = None
        st.session_state["selected_path"] = None
        selected_id = None

    with left:
        for path in sorted(paths, key=lambda item: item.name):
            if st.button(
                path.name,
                key=f"path-item-{path.id}",
                use_container_width=True,
            ):
                components.set_selected_path(path.id)

    if not selected_id:
        with right:
            st.info("Выберите маршрут слева.")
        return

    path = next((item for item in data.paths if item.id == selected_id), None)
    if not path:
        with right:
            st.warning("Маршрут не найден.")
        return

    with right:
        st.subheader(path.name)
        st.markdown(f"**Путь:** {components.ascii_path(path)}")
        st.write(path.note)

        st.markdown("#### Переходы и мосты")
        for idx in range(len(path.sequence) - 1):
            start = path.sequence[idx]
            end = path.sequence[idx + 1]
            bridges = components.bridges_between(data, start, end)[:2]
            st.markdown(f"**{start} → {end}**")
            if not bridges:
                st.caption("Нет прямых мостов.")
            else:
                for bridge in bridges:
                    st.write(f"- {bridge.name} ({bridge.id})")

            variants = data.variants_by_cell_id.get(start, [])
            variants = components.apply_global_filters_to_variants(variants, filters)
            if variants:
                st.caption("Варианты для шага:")
                for variant in variants[:4]:
                    if st.button(
                        f"{variant.title} · {variant.kind}",
                        key=f"path-variant-{path.id}-{start}-{variant.id}",
                    ):
                        go_to_section(
                            "Варианты (конкретика)",
                            variant_id=variant.id,
                            way_id=variant.primary_way_id,
                        )

        if st.button("Показать ASCII", key=f"path-ascii-{path.id}"):
            st.code(components.ascii_path(path), language="text")
