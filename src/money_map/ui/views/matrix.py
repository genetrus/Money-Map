from __future__ import annotations

from collections import defaultdict
from typing import Iterable

import streamlit as st

from money_map.core.model import AppData, BridgeItem, PathItem, TaxonomyItem
from money_map.ui import components
from money_map.ui.state import go_to_section, request_nav


def _index_by_cell(items: Iterable[TaxonomyItem]) -> dict[str, list[TaxonomyItem]]:
    grouped: dict[str, list[TaxonomyItem]] = defaultdict(list)
    for item in items:
        for cell_id in item.typical_cells:
            grouped[cell_id].append(item)
    return grouped


def _index_paths_by_cell(paths: Iterable[PathItem]) -> dict[str, list[PathItem]]:
    grouped: dict[str, list[PathItem]] = defaultdict(list)
    for path in paths:
        for cell_id in path.sequence:
            grouped[cell_id].append(path)
    return grouped


def _index_bridges_by_from(
    bridges: Iterable[BridgeItem],
) -> tuple[dict[str, list[BridgeItem]], dict[tuple[str, str], list[BridgeItem]]]:
    by_from: dict[str, list[BridgeItem]] = defaultdict(list)
    by_transition: dict[tuple[str, str], list[BridgeItem]] = defaultdict(list)
    for bridge in bridges:
        by_from[bridge.from_cell].append(bridge)
        by_transition[(bridge.from_cell, bridge.to_cell)].append(bridge)
    return by_from, by_transition


def _axis_defaults(
    filters: components.Filters,
    selected_cell_id: str | None,
) -> dict[str, str]:
    axes = components.cell_to_axes(selected_cell_id) if selected_cell_id else None
    base = axes or {"risk": "low", "activity": "active", "scalability": "linear"}
    return {
        "risk": filters.risk if filters.risk != "all" else base["risk"],
        "activity": filters.activity if filters.activity != "all" else base["activity"],
        "scalability": filters.scalability if filters.scalability != "all" else base["scalability"],
    }


def _sync_axis_state(defaults: dict[str, str], selected_cell_id: str | None) -> None:
    for axis in ("risk", "activity", "scalability"):
        key = f"matrix_axis_{axis}"
        desired = defaults[axis]
        current = st.session_state.get(key)
        if current not in components.AXIS_LABELS[axis]:
            st.session_state[key] = desired
        if selected_cell_id and current != desired:
            st.session_state[key] = desired


def _clear_transition_state() -> None:
    st.session_state["selected_transition"] = None
    st.session_state["selected_bridge_id"] = None


def _queue_global_filter_updates(risk: str, activity: str, scalability: str) -> None:
    if st.session_state.get("filter_risk") != risk:
        st.session_state["request_filter_risk"] = risk
    if st.session_state.get("filter_activity") != activity:
        st.session_state["request_filter_activity"] = activity
    if st.session_state.get("filter_scalability") != scalability:
        st.session_state["request_filter_scalability"] = scalability


def _select_cell(cell_id: str) -> None:
    components.set_selected_cell(cell_id)
    _clear_transition_state()


def render(data: AppData, filters: components.Filters) -> None:
    payload = components.consume_nav_intent("Матрица")
    if isinstance(payload, dict):
        cell_id = payload.get("cell_id")
        if isinstance(cell_id, str):
            components.set_selected_cell(cell_id)
            st.session_state["matrix_focus_cell"] = cell_id

    st.title("Матрица")
    components.render_path_wizard("Матрица")

    focus_cell = st.session_state.get("matrix_focus_cell")
    if focus_cell and st.session_state.get("selected_cell") != focus_cell:
        components.set_selected_cell(focus_cell)

    selected_cell_id = st.session_state.get("selected_cell_id")
    defaults = _axis_defaults(filters, selected_cell_id)
    _sync_axis_state(defaults, selected_cell_id)

    with st.container(border=True):
        st.markdown("### Координаты мира")
        axis_cols = st.columns([1, 1, 1, 1.3])
        axis_cols[0].radio(
            "Риск",
            ["low", "high"],
            key="matrix_axis_risk",
            horizontal=True,
            format_func=lambda value: components.axis_label("risk", value),
        )
        axis_cols[1].radio(
            "Активность",
            ["active", "passive"],
            key="matrix_axis_activity",
            horizontal=True,
            format_func=lambda value: components.axis_label("activity", value),
        )
        axis_cols[2].radio(
            "Масштаб",
            ["linear", "scalable"],
            key="matrix_axis_scalability",
            horizontal=True,
            format_func=lambda value: components.axis_label("scalability", value),
        )
        with axis_cols[3]:
            derived_cell = components.axes_to_cell_id(
                st.session_state["matrix_axis_risk"],
                st.session_state["matrix_axis_activity"],
                st.session_state["matrix_axis_scalability"],
            )
            badge = derived_cell or "—"
            st.markdown(f"**Выбрана ячейка: {badge}**")
            st.button(
                "Сбросить переход",
                key="matrix-reset-transition",
                help="Очистить выбранный переход и мост.",
                on_click=_clear_transition_state,
                use_container_width=True,
            )

    risk = st.session_state["matrix_axis_risk"]
    activity = st.session_state["matrix_axis_activity"]
    scalability = st.session_state["matrix_axis_scalability"]
    derived_cell = components.axes_to_cell_id(risk, activity, scalability)
    if derived_cell and derived_cell != selected_cell_id:
        _select_cell(derived_cell)
        _queue_global_filter_updates(risk, activity, scalability)

    ways_by_cell = _index_by_cell(data.taxonomy)
    paths_by_cell = _index_paths_by_cell(data.paths)
    bridges_by_from, bridges_by_transition = _index_bridges_by_from(data.bridges)

    grid_cols = st.columns(2)
    for idx, (risk_key, risk_label) in enumerate(
        [("low", "Низкий риск"), ("high", "Высокий риск")],
    ):
        with grid_cols[idx]:
            with st.container(border=True):
                st.markdown(f"#### {risk_label}")
                for activity_key, activity_label in [("active", "Активно"), ("passive", "Пассивно")]:
                    row = st.columns(2)
                    for col_idx, scale_key in enumerate(["linear", "scalable"]):
                        cell = components.axes_to_cell_id(risk_key, activity_key, scale_key)
                        if not cell:
                            continue
                        cell_data = components.cell_lookup(data).get(cell)
                        if not cell_data:
                            continue
                        selected = cell_data.id == st.session_state.get("selected_cell_id")
                        with row[col_idx]:
                            with st.container(border=selected):
                                st.markdown(f"### {cell_data.id}")
                                st.caption(cell_data.label)
                                ways_count = len(ways_by_cell.get(cell_data.id, []))
                                bridges_count = len(bridges_by_from.get(cell_data.id, []))
                                routes_count = len(paths_by_cell.get(cell_data.id, []))
                                variants_count = len(data.variants_by_cell_id.get(cell_data.id, []))
                                st.caption(
                                    f"💠 {ways_count}  🌉 {bridges_count}  🧭 {routes_count}  🧩 {variants_count}",
                                )
                                if st.button(
                                    f"Выбрать {cell_data.id}",
                                    key=f"matrix-cell-{cell_data.id}",
                                    use_container_width=True,
                                ):
                                    axes = components.cell_to_axes(cell_data.id) or {}
                                    st.session_state["request_selected_cell_id"] = cell_data.id
                                    st.session_state["request_matrix_axis_risk"] = axes.get("risk", risk_key)
                                    st.session_state["request_matrix_axis_activity"] = axes.get("activity", activity_key)
                                    st.session_state["request_matrix_axis_scalability"] = axes.get(
                                        "scalability",
                                        scale_key,
                                    )
                                    st.session_state["request_filter_risk"] = axes.get("risk", risk_key)
                                    st.session_state["request_filter_activity"] = axes.get("activity", activity_key)
                                    st.session_state["request_filter_scalability"] = axes.get(
                                        "scalability",
                                        scale_key,
                                    )
                                    _clear_transition_state()
                                    st.rerun()

    selected_id = st.session_state.get("selected_cell_id")
    if not selected_id:
        st.info("Выберите ячейку, чтобы увидеть детали.")
        return

    cell = components.cell_lookup(data).get(selected_id)
    if not cell:
        st.warning("Выбранная ячейка не найдена.")
        return

    related_ways = sorted(ways_by_cell.get(cell.id, []), key=lambda item: item.name)
    outgoing_transitions = sorted({bridge.to_cell for bridge in bridges_by_from.get(cell.id, [])})
    selected_transition = st.session_state.get("selected_transition")
    if selected_transition and not selected_transition.startswith(f"{cell.id}->"):
        selected_transition = None
        st.session_state["selected_transition"] = None
        st.session_state["selected_bridge_id"] = None

    with st.container(border=True):
        st.markdown(f"### {cell.id} · {cell.label}")
        st.caption("Смысл")
        st.write(cell.short)

        st.markdown("#### Связанные способы")
        if not related_ways:
            st.caption("Нет связанных способов.")
        else:
            max_items = 6
            displayed = related_ways[:max_items]
            chip_cols = st.columns(min(4, len(displayed)))
            for idx, item in enumerate(displayed):
                with chip_cols[idx % len(chip_cols)]:
                    if st.button(
                        item.name,
                        key=f"matrix-way-{cell.id}-{item.id}",
                        use_container_width=True,
                    ):
                        go_to_section(
                            "ways",
                            way_id=item.id,
                            open_tab="directory",
                        )
            if len(related_ways) > max_items:
                with st.expander("ещё"):
                    for item in related_ways[max_items:]:
                        if st.button(
                            item.name,
                            key=f"matrix-way-extra-{cell.id}-{item.id}",
                        ):
                            go_to_section(
                                "ways",
                                way_id=item.id,
                                open_tab="directory",
                            )

        st.markdown("#### Куда можно перейти")
        if not outgoing_transitions:
            st.caption("Нет исходящих переходов.")
        else:
            transition_cols = st.columns(min(4, len(outgoing_transitions)))
            for idx, to_cell in enumerate(outgoing_transitions[:4]):
                label = f"{cell.id} → {to_cell}"
                with transition_cols[idx % len(transition_cols)]:
                    if st.button(label, key=f"matrix-transition-{cell.id}-{to_cell}"):
                        st.session_state["selected_transition"] = f"{cell.id}->{to_cell}"
                        st.session_state["selected_bridge_id"] = None
                        st.rerun()

        if selected_transition:
            from_cell, to_cell = selected_transition.split("->", maxsplit=1)
            st.caption(f"Мосты для перехода {from_cell} → {to_cell}")
            bridges = bridges_by_transition.get((from_cell, to_cell), [])
            if not bridges:
                st.caption("Нет мостов для выбранного перехода.")
            else:
                bridge_cols = st.columns(min(3, len(bridges[:6])))
                for idx, bridge in enumerate(bridges[:6]):
                    with bridge_cols[idx % len(bridge_cols)]:
                        if st.button(
                            bridge.name,
                            key=f"matrix-bridge-{bridge.id}",
                            use_container_width=True,
                        ):
                            st.session_state["selected_bridge_id"] = bridge.id
                            st.rerun()
                if st.session_state.get("selected_bridge_id"):
                    if st.button(
                        "Показать конкретику по мосту",
                        key="matrix-cta-bridge",
                        use_container_width=True,
                    ):
                        go_to_section(
                            "variants",
                            cell_id=cell.id,
                            transition=selected_transition,
                            bridge_id=st.session_state.get("selected_bridge_id"),
                        )

        if st.button(
            "Показать конкретику",
            key="matrix-cta-variants",
            use_container_width=True,
        ):
            go_to_section(
                "variants",
                cell_id=cell.id,
                transition=selected_transition,
                bridge_id=st.session_state.get("selected_bridge_id"),
            )

        if st.session_state.get("nav_mode") == "Конструктор пути" and selected_id:
            if st.button(
                "Дальше → Классификатор",
                key="matrix-next-classifier",
                use_container_width=True,
            ):
                st.session_state["nav_step_next"] = "Классификатор"
                request_nav("Классификатор")
