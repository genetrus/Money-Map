from __future__ import annotations

import streamlit as st

from money_map.core.model import AppData, BridgeItem
from money_map.ui import components
from money_map.ui.state import go_to_section


def _transition_label(sequence: list[str]) -> list[str]:
    return [f"{sequence[idx]}->{sequence[idx + 1]}" for idx in range(len(sequence) - 1)]


def _short_summary(text: str) -> str:
    if not text:
        return "Короткое описание недоступно."
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "Короткое описание недоступно."
    return lines[0]


def _bridge_ids(bridges: list[BridgeItem]) -> list[str]:
    return [bridge.id for bridge in bridges]


def _build_route_view_models(data: AppData) -> list[dict[str, object]]:
    bridges_by_transition: dict[str, list[BridgeItem]] = {}
    for bridge in data.bridges:
        transition = f"{bridge.from_cell}->{bridge.to_cell}"
        bridges_by_transition.setdefault(transition, []).append(bridge)

    routes = []
    for path in data.paths:
        transitions = _transition_label(path.sequence)
        recommended_by_transition = {
            transition: _bridge_ids(sorted(bridges_by_transition.get(transition, []), key=lambda item: item.name))
            for transition in transitions
        }
        linked_way_ids = {
            way_id
            for transition in transitions
            for bridge in bridges_by_transition.get(transition, [])
            for way_id in bridge.linked_way_ids
        }
        routes.append(
            {
                "route_id": path.id,
                "name": path.name,
                "cells": path.sequence,
                "transitions": transitions,
                "short_summary": _short_summary(path.note),
                "recommended_bridges_by_transition": recommended_by_transition,
                "linked_way_ids": sorted(linked_way_ids),
            }
        )
    return routes


def _filter_routes(
    routes: list[dict[str, object]],
    *,
    start_cell: str | None,
    target_cell: str | None,
    allowed_cells: set[str],
    apply_global_filter: bool,
) -> list[dict[str, object]]:
    filtered = routes
    if start_cell:
        filtered = [
            route
            for route in filtered
            if route["cells"] and route["cells"][0] == start_cell
        ]
    if target_cell:
        filtered = [
            route
            for route in filtered
            if route["cells"] and route["cells"][-1] == target_cell
        ]
    if apply_global_filter:
        filtered = [
            route
            for route in filtered
            if any(cell in allowed_cells for cell in route["cells"])
        ]
    return filtered


def render(data: AppData, filters: components.Filters) -> None:
    st.title("Маршруты")

    cell_lookup = components.cell_lookup(data)
    bridge_lookup = {bridge.id: bridge for bridge in data.bridges}
    way_lookup = components.taxonomy_lookup(data)
    routes = _build_route_view_models(data)

    selected_cell_id = st.session_state.get("selected_cell_id")
    if st.session_state.get("route_filters_start_cell") is None and selected_cell_id:
        st.session_state["route_filters_start_cell"] = selected_cell_id

    allowed_cells = components.get_allowed_cells_from_global_filters(data, filters)
    apply_global_filter = len(allowed_cells) != len(data.cells)

    def _reset_routes() -> None:
        st.session_state["route_filters_start_cell"] = None
        st.session_state["route_filters_target_cell"] = None
        st.session_state["selected_route_id"] = None
        st.session_state["selected_path"] = None
        st.session_state["selected_transition"] = None
        st.session_state["selected_bridge_id"] = None
        st.session_state["chosen_bridges_by_transition"] = {}

    def _on_route_change() -> None:
        route_id = st.session_state.get("routes_selected_route")
        st.session_state["selected_route_id"] = route_id
        st.session_state["selected_path"] = route_id
        st.session_state["selected_transition"] = None
        st.session_state["selected_bridge_id"] = None
        st.session_state["chosen_bridges_by_transition"] = {}

    def _select_transition(transition: str) -> None:
        st.session_state["selected_transition"] = transition

    def _choose_bridge(transition: str, bridge_id: str) -> None:
        selections = dict(st.session_state.get("chosen_bridges_by_transition", {}))
        selections[transition] = bridge_id
        st.session_state["chosen_bridges_by_transition"] = selections
        st.session_state["selected_bridge_id"] = bridge_id
        st.session_state["selected_transition"] = transition

    def _reset_chosen_bridges() -> None:
        st.session_state["chosen_bridges_by_transition"] = {}

    top_cols = st.columns([2, 2, 4, 1])
    cell_ids = [None] + sorted(cell_lookup.keys())

    top_cols[0].selectbox(
        "Стартовая ячейка",
        cell_ids,
        key="route_filters_start_cell",
        format_func=lambda value: "Все" if value is None else value,
    )
    top_cols[1].selectbox(
        "Целевая ячейка",
        cell_ids,
        key="route_filters_target_cell",
        format_func=lambda value: "Все" if value is None else value,
    )

    filtered_routes = _filter_routes(
        routes,
        start_cell=st.session_state.get("route_filters_start_cell"),
        target_cell=st.session_state.get("route_filters_target_cell"),
        allowed_cells=allowed_cells,
        apply_global_filter=apply_global_filter,
    )

    if not filtered_routes:
        top_cols[2].selectbox(
            "Маршрут",
            ["—"],
            key="routes_selected_route",
            disabled=True,
        )
        top_cols[3].button("Сбросить", key="routes-reset-empty", on_click=_reset_routes)
        st.info("Нет маршрутов для выбранных условий. Попробуйте сбросить фильтры.")
        return

    available_route_ids = [route["route_id"] for route in filtered_routes]
    selected_id = st.session_state.get("selected_route_id")
    if selected_id not in available_route_ids:
        st.session_state["selected_route_id"] = None
        st.session_state["selected_path"] = None
        selected_id = None

    if st.session_state.get("routes_selected_route") != selected_id:
        st.session_state["routes_selected_route"] = selected_id

    def _route_label(route_id: str | None) -> str:
        if route_id is None:
            return "Выберите маршрут"
        route = next((item for item in filtered_routes if item["route_id"] == route_id), None)
        if not route:
            return route_id
        cells = " → ".join(route["cells"])
        return f"{cells} · {route['name']}"

    top_cols[2].selectbox(
        "Маршрут",
        [None] + available_route_ids,
        key="routes_selected_route",
        format_func=_route_label,
        on_change=_on_route_change,
    )
    top_cols[3].button("Сбросить", key="routes-reset", on_click=_reset_routes)

    if not selected_id:
        st.info("Выберите маршрут, чтобы увидеть шаги.")
        return

    route = next((item for item in filtered_routes if item["route_id"] == selected_id), None)
    if not route:
        st.warning("Маршрут не найден.")
        return

    if st.session_state.get("selected_transition") not in route["transitions"]:
        st.session_state["selected_transition"] = None

    st.markdown("### Линия маршрута")
    line_cols = st.columns(len(route["cells"]) * 2 - 1)
    for idx, cell_id in enumerate(route["cells"]):
        cell = cell_lookup.get(cell_id)
        with line_cols[idx * 2]:
            with st.container(border=True):
                st.markdown(f"**{cell_id}**")
                st.caption(cell.short if cell else "—")
        if idx < len(route["cells"]) - 1:
            transition = route["transitions"][idx]
            with line_cols[idx * 2 + 1]:
                st.button(
                    "→",
                    key=f"route-transition-{route['route_id']}-{transition}",
                    on_click=_select_transition,
                    args=(transition,),
                    use_container_width=True,
                )
                st.caption(transition)

    body_cols = st.columns([3, 2])
    with body_cols[0]:
        st.markdown("#### Шаги и мосты")
        selected_transition = st.session_state.get("selected_transition")
        selected_bridge_by_transition = st.session_state.get("chosen_bridges_by_transition", {})
        for transition in route["transitions"]:
            bridges_for_transition = route["recommended_bridges_by_transition"].get(transition, [])
            bridge_objects = [bridge_lookup.get(bridge_id) for bridge_id in bridges_for_transition]
            bridge_objects = [bridge for bridge in bridge_objects if bridge]
            if len(bridge_objects) > 6:
                primary_bridges = bridge_objects[:6]
                extra_bridges = bridge_objects[6:]
            else:
                primary_bridges = bridge_objects
                extra_bridges = []

            with st.container(border=True):
                header_cols = st.columns([4, 1])
                header_cols[0].markdown(f"**{transition.replace('->', ' → ')}**")
                if selected_transition != transition:
                    header_cols[1].button(
                        "Выбрать",
                        key=f"route-transition-select-{route['route_id']}-{transition}",
                        on_click=_select_transition,
                        args=(transition,),
                    )
                else:
                    header_cols[1].caption("Выбран")

                if not bridge_objects:
                    st.caption("Нет рекомендованных мостов.")
                else:
                    chip_cols = st.columns(min(len(primary_bridges), 3))
                    for index, bridge in enumerate(primary_bridges):
                        with chip_cols[index % len(chip_cols)]:
                            st.button(
                                bridge.name,
                                key=f"route-bridge-{route['route_id']}-{transition}-{bridge.id}",
                                on_click=_choose_bridge,
                                args=(transition, bridge.id),
                                type="primary"
                                if selected_bridge_by_transition.get(transition) == bridge.id
                                else "secondary",
                                use_container_width=True,
                            )
                    if extra_bridges:
                        with st.expander("Ещё мосты"):
                            for bridge in extra_bridges:
                                st.button(
                                    bridge.name,
                                    key=f"route-bridge-extra-{route['route_id']}-{transition}-{bridge.id}",
                                    on_click=_choose_bridge,
                                    args=(transition, bridge.id),
                                    type="primary"
                                    if selected_bridge_by_transition.get(transition) == bridge.id
                                    else "secondary",
                                    use_container_width=True,
                                )

    with body_cols[1]:
        with st.container(border=True):
            st.markdown(f"### {route['name']}")
            st.caption(route["short_summary"])
            st.markdown("**Шаги маршрута**")
            for transition in route["transitions"]:
                bridge_id = st.session_state.get("chosen_bridges_by_transition", {}).get(transition)
                bridge_name = bridge_lookup.get(bridge_id).name if bridge_id and bridge_lookup.get(bridge_id) else "—"
                st.markdown(f"- {transition.replace('->', ' → ')} · мост: {bridge_name}")

            linked_way_ids = route.get("linked_way_ids", [])
            if linked_way_ids:
                st.markdown("**Связанные способы**")
                way_cols = st.columns(min(len(linked_way_ids), 2))
                for idx, way_id in enumerate(linked_way_ids[:8]):
                    way = way_lookup.get(way_id)
                    label = way.name if way else way_id
                    with way_cols[idx % len(way_cols)]:
                        st.button(
                            label,
                            key=f"route-way-{route['route_id']}-{way_id}",
                            on_click=go_to_section,
                            args=("ways",),
                            kwargs={"way_id": way_id, "open_tab": "directory"},
                            use_container_width=True,
                        )

            st.button(
                "Показать конкретику по маршруту",
                key=f"route-open-variants-{route['route_id']}",
                on_click=go_to_section,
                args=("variants",),
                kwargs={"route_id": route["route_id"]},
                use_container_width=True,
                type="primary",
            )

            if st.session_state.get("selected_transition"):
                st.button(
                    f"Открыть мосты для шага {st.session_state['selected_transition'].replace('->', ' → ')}",
                    key=f"route-open-bridges-{route['route_id']}",
                    on_click=go_to_section,
                    args=("bridges",),
                    kwargs={"transition": st.session_state["selected_transition"]},
                    use_container_width=True,
                )
            st.button(
                "Сбросить выбор мостов",
                key=f"route-reset-bridges-{route['route_id']}",
                on_click=_reset_chosen_bridges,
                use_container_width=True,
            )
