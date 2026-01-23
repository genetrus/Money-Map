from __future__ import annotations

from collections import defaultdict

import streamlit as st

from money_map.core.model import AppData, BridgeItem, Cell, PathItem, TaxonomyItem, Variant
from money_map.ui import components
from money_map.ui.state import go_to_section


def _bridge_effects(bridge: BridgeItem) -> list[str]:
    if bridge.effects:
        return bridge.effects
    if bridge.checks:
        return bridge.checks
    if bridge.mechanisms:
        return [item.replace("_", " ").capitalize() for item in bridge.mechanisms]
    return []


def _bridge_summary(bridge: BridgeItem) -> str:
    return bridge.short_summary or bridge.notes or "—"


def _bridge_matches_filters(
    bridge: BridgeItem,
    lookup: dict[str, Cell],
    filters: components.Filters,
) -> bool:
    if bridge.from_cell not in lookup or bridge.to_cell not in lookup:
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


def _index_bridges(
    bridges: list[BridgeItem],
    lookup: dict[str, Cell],
    filters: components.Filters,
) -> tuple[dict[str, list[BridgeItem]], dict[str, list[str]]]:
    bridges_by_transition: dict[str, list[BridgeItem]] = defaultdict(list)
    outgoing_by_cell: dict[str, list[str]] = defaultdict(list)
    for bridge in bridges:
        if not _bridge_matches_filters(bridge, lookup, filters):
            continue
        transition = f"{bridge.from_cell}->{bridge.to_cell}"
        bridges_by_transition[transition].append(bridge)
    for transition in sorted(bridges_by_transition):
        from_cell = transition.split("->", maxsplit=1)[0]
        outgoing_by_cell[from_cell].append(transition)
    return bridges_by_transition, outgoing_by_cell


def _index_ways_by_cell(items: list[TaxonomyItem]) -> dict[str, list[TaxonomyItem]]:
    grouped: dict[str, list[TaxonomyItem]] = defaultdict(list)
    for item in items:
        for cell_id in item.typical_cells:
            grouped[cell_id].append(item)
    return grouped


def _index_ways_by_bridge(
    bridges: list[BridgeItem],
    ways_by_cell: dict[str, list[TaxonomyItem]],
) -> dict[str, list[TaxonomyItem]]:
    by_bridge: dict[str, list[TaxonomyItem]] = {}
    for bridge in bridges:
        related = ways_by_cell.get(bridge.from_cell, []) + ways_by_cell.get(bridge.to_cell, [])
        unique = {item.id: item for item in related}
        by_bridge[bridge.id] = sorted(unique.values(), key=lambda item: item.name)
    return by_bridge


def _index_routes_by_bridge(
    bridges: list[BridgeItem],
    paths: list[PathItem],
) -> dict[str, list[PathItem]]:
    by_bridge: dict[str, list[PathItem]] = defaultdict(list)
    for bridge in bridges:
        for path in paths:
            if bridge.from_cell in path.sequence and bridge.to_cell in path.sequence:
                if path.sequence.index(bridge.from_cell) < path.sequence.index(bridge.to_cell):
                    by_bridge[bridge.id].append(path)
        by_bridge[bridge.id] = sorted(by_bridge[bridge.id], key=lambda item: item.name)
    return by_bridge


def _index_variants_by_transition(variants: list[Variant]) -> dict[str, list[Variant]]:
    grouped: dict[str, list[Variant]] = defaultdict(list)
    for variant in variants:
        cells = variant.matrix_cells
        for idx, from_cell in enumerate(cells):
            for to_cell in cells[idx + 1 :]:
                grouped[f"{from_cell}->{to_cell}"].append(variant)
                grouped[f"{to_cell}->{from_cell}"].append(variant)
    return grouped


def render(data: AppData, filters: components.Filters) -> None:
    def _on_transition_change() -> None:
        st.session_state["selected_transition"] = st.session_state.get("bridges_transition_select")
        st.session_state["selected_bridge_id"] = None

    def _clear_bridge_selection() -> None:
        st.session_state["selected_bridge_id"] = None

    st.title("Мосты")
    st.markdown("Выберите переход и разберите мосты как визуальную панель управления.")

    lookup = components.cell_lookup(data)
    bridges_by_transition, outgoing_by_cell = _index_bridges(data.bridges, lookup, filters)
    filtered_ways = components.apply_global_filters_to_ways(data.taxonomy, filters, data)
    ways_by_cell = _index_ways_by_cell(filtered_ways)
    ways_by_bridge_id = _index_ways_by_bridge(data.bridges, ways_by_cell)
    routes_by_bridge_id = _index_routes_by_bridge(data.bridges, data.paths)
    filtered_variants = components.apply_global_filters_to_variants(data.variants, filters)
    variants_by_transition = _index_variants_by_transition(filtered_variants)

    transitions = sorted(bridges_by_transition.keys())
    selected_cell_id = st.session_state.get("selected_cell_id")

    if "bridges_only_outgoing" not in st.session_state:
        st.session_state["bridges_only_outgoing"] = bool(selected_cell_id)

    only_outgoing = st.session_state.get("bridges_only_outgoing", False)
    available_transitions = transitions
    if only_outgoing and selected_cell_id:
        available_transitions = outgoing_by_cell.get(selected_cell_id, [])

    if not available_transitions:
        st.warning("Нет доступных переходов по текущим фильтрам.")
        return

    selected_transition = st.session_state.get("selected_transition")
    if selected_transition not in available_transitions:
        selected_transition = None
        st.session_state["selected_transition"] = None
        st.session_state["selected_bridge_id"] = None

    if not selected_transition and selected_cell_id and available_transitions:
        selected_transition = available_transitions[0]
        st.session_state["selected_transition"] = selected_transition

    if not selected_transition and available_transitions:
        selected_transition = available_transitions[0]
        st.session_state["selected_transition"] = selected_transition

    if st.session_state.get("bridges_transition_select") != selected_transition:
        st.session_state["bridges_transition_select"] = selected_transition

    with st.container(border=True):
        st.markdown("### Переход")
        controls = st.columns([3, 2, 1])
        with controls[0]:
            label = "Переход"
            if selected_cell_id:
                label = f"Переход (от {selected_cell_id})"
            st.selectbox(
                label,
                available_transitions,
                format_func=lambda value: _transition_label(value, lookup),
                key="bridges_transition_select",
                on_change=_on_transition_change,
            )
        with controls[1]:
            if selected_cell_id:
                st.checkbox(
                    f"Только исходящие из {selected_cell_id}",
                    key="bridges_only_outgoing",
                )
            else:
                st.caption("Выберите ячейку в матрице, чтобы фильтровать переходы.")
        controls[2].button(
            "Сбросить мост",
            key="bridges-reset-bridge",
            on_click=_clear_bridge_selection,
        )

    if not selected_transition:
        st.info("Выберите переход (A1 → A2), чтобы увидеть мосты.")
        return

    from_cell, to_cell = selected_transition.split("->", maxsplit=1)
    bridges = sorted(bridges_by_transition.get(selected_transition, []), key=lambda item: item.name)
    selected_bridge_id = st.session_state.get("selected_bridge_id")
    if selected_bridge_id and all(bridge.id != selected_bridge_id for bridge in bridges):
        st.session_state["selected_bridge_id"] = None
        selected_bridge_id = None

    with st.container(border=True):
        ribbon_cols = st.columns([1.1, 3, 1.1])
        with ribbon_cols[0]:
            _render_cell_card(
                lookup.get(from_cell),
                bridges_count=len(bridges),
                variants_count=len(variants_by_transition.get(selected_transition, [])),
            )
        with ribbon_cols[1]:
            st.markdown("#### Мосты перехода")
            if not bridges:
                st.caption("Для этого перехода мосты пока не описаны.")
            else:
                _render_bridge_tiles(
                    bridges,
                    selected_bridge_id,
                    routes_by_bridge_id,
                    ways_by_bridge_id,
                    variants_by_transition.get(selected_transition, []),
                )
        with ribbon_cols[2]:
            _render_cell_card(
                lookup.get(to_cell),
                bridges_count=len(bridges),
                variants_count=len(variants_by_transition.get(selected_transition, [])),
            )

    st.button(
        "Показать конкретику по переходу",
        key="bridges-cta-transition",
        use_container_width=True,
        on_click=lambda: go_to_section(
            "variants",
            transition=selected_transition,
            bridge_id=None,
            cell_id=from_cell,
        ),
    )

    if selected_bridge_id:
        bridge_lookup = {bridge.id: bridge for bridge in data.bridges}
        bridge = bridge_lookup.get(selected_bridge_id)
        if bridge:
            _render_bridge_details(
                bridge,
                ways_by_bridge_id.get(bridge.id, []),
                routes_by_bridge_id.get(bridge.id, []),
                selected_transition,
            )


def _transition_label(transition: str, lookup: dict[str, Cell]) -> str:
    if "->" not in transition:
        return transition
    from_cell, to_cell = transition.split("->", maxsplit=1)
    from_label = lookup.get(from_cell).label if lookup.get(from_cell) else "—"
    to_label = lookup.get(to_cell).label if lookup.get(to_cell) else "—"
    return f"{from_cell} → {to_cell} ({from_label} → {to_label})"


def _render_cell_card(cell: Cell | None, bridges_count: int, variants_count: int) -> None:
    if not cell:
        st.caption("—")
        return
    with st.container(border=True):
        st.markdown(f"### {cell.id}")
        st.caption(cell.label)
        st.markdown(cell.short or "—")
        st.caption(f"🌉 {bridges_count}  🧩 {variants_count}")


def _render_bridge_tiles(
    bridges: list[BridgeItem],
    selected_bridge_id: str | None,
    routes_by_bridge_id: dict[str, list[PathItem]],
    ways_by_bridge_id: dict[str, list[TaxonomyItem]],
    transition_variants: list[Variant],
) -> None:
    max_visible = 8
    displayed = bridges[:max_visible]
    remaining = bridges[max_visible:]
    _render_bridge_tile_grid(
        displayed,
        selected_bridge_id,
        routes_by_bridge_id,
        ways_by_bridge_id,
        transition_variants,
    )
    if remaining:
        with st.expander("Показать ещё"):
            _render_bridge_tile_grid(
                remaining,
                selected_bridge_id,
                routes_by_bridge_id,
                ways_by_bridge_id,
                transition_variants,
            )


def _render_bridge_tile_grid(
    bridges: list[BridgeItem],
    selected_bridge_id: str | None,
    routes_by_bridge_id: dict[str, list[PathItem]],
    ways_by_bridge_id: dict[str, list[TaxonomyItem]],
    transition_variants: list[Variant],
) -> None:
    if not bridges:
        return
    columns = st.columns(min(3, len(bridges)))
    variants_count = len(transition_variants)
    for idx, bridge in enumerate(bridges):
        selected = bridge.id == selected_bridge_id
        with columns[idx % len(columns)]:
            with st.container(border=selected):
                st.markdown(f"**{bridge.name}**")
                st.caption(_bridge_summary(bridge))
                routes_count = len(routes_by_bridge_id.get(bridge.id, []))
                ways_count = len(ways_by_bridge_id.get(bridge.id, []))
                st.caption(f"🧩 {variants_count}  🧭 {routes_count}  💠 {ways_count}")
                st.button(
                    "Открыть",
                    key=f"bridge-tile-{bridge.id}",
                    use_container_width=True,
                    on_click=lambda bridge_id=bridge.id: _select_bridge(bridge_id),
                )


def _select_bridge(bridge_id: str) -> None:
    st.session_state["selected_bridge_id"] = bridge_id


def _render_bridge_details(
    bridge: BridgeItem,
    ways: list[TaxonomyItem],
    routes: list[PathItem],
    selected_transition: str,
) -> None:
    from_cell, _ = selected_transition.split("->", maxsplit=1)
    with st.container(border=True):
        st.markdown(f"### {bridge.name}")
        st.caption(_bridge_summary(bridge))

        st.markdown("**Что меняет**")
        effects = _bridge_effects(bridge)
        displayed_effects = effects[:3]
        for effect in displayed_effects:
            st.markdown(f"- {effect}")
        if len(effects) > 3:
            with st.expander("ещё"):
                for effect in effects[3:]:
                    st.markdown(f"- {effect}")

        st.markdown("**Связанные способы**")
        if not ways:
            st.caption("Нет связанных способов.")
        else:
            _render_way_chips(ways)

        st.markdown("**Связанные маршруты**")
        if not routes:
            st.caption("Нет связанных маршрутов.")
        else:
            for path in routes[:3]:
                st.button(
                    path.name,
                    key=f"bridge-route-{bridge.id}-{path.id}",
                    on_click=lambda route_id=path.id: go_to_section("routes", route_id=route_id),
                    use_container_width=True,
                )
            if len(routes) > 3:
                st.button(
                    "Все маршруты",
                    key=f"bridge-route-all-{bridge.id}",
                    use_container_width=True,
                    on_click=lambda: go_to_section(
                        "routes",
                        bridge_id=bridge.id,
                    ),
                )

        cta_cols = st.columns(2)
        cta_cols[0].button(
            "Показать конкретику по этому мосту",
            key=f"bridge-cta-{bridge.id}",
            use_container_width=True,
            on_click=lambda: go_to_section(
                "variants",
                transition=selected_transition,
                bridge_id=bridge.id,
                cell_id=from_cell,
            ),
        )
        cta_cols[1].button(
            "Показать конкретику по переходу",
            key=f"bridge-cta-transition-{bridge.id}",
            use_container_width=True,
            on_click=lambda: go_to_section(
                "variants",
                transition=selected_transition,
                bridge_id=None,
                cell_id=from_cell,
            ),
        )


def _render_way_chips(ways: list[TaxonomyItem]) -> None:
    max_items = 8
    displayed = ways[:max_items]
    columns = st.columns(min(4, len(displayed)))
    for idx, item in enumerate(displayed):
        with columns[idx % len(columns)]:
            st.button(
                item.name,
                key=f"bridge-way-{item.id}",
                use_container_width=True,
                on_click=lambda way_id=item.id: go_to_section(
                    "ways",
                    way_id=way_id,
                    open_tab="directory",
                ),
            )
    if len(ways) > max_items:
        with st.expander("ещё"):
            for item in ways[max_items:]:
                st.button(
                    item.name,
                    key=f"bridge-way-extra-{item.id}",
                    on_click=lambda way_id=item.id: go_to_section(
                        "ways",
                        way_id=way_id,
                        open_tab="directory",
                    ),
                )
