from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import streamlit as st

from money_map.core.model import AppData, Variant
from money_map.ui import components
from money_map.ui.state import go_to_section


def _filter_variants(
    variants: List[Variant],
    way_id: str,
    kind: str,
    cell_id: str,
    outside_only: bool,
    transition: Optional[Tuple[str, str]],
    bridge_id: Optional[str],
    bridge_filter_available: bool,
    classifier_selections: Optional[Dict[str, set[str]]] = None,
    route_cells: Optional[List[str]] = None,
    chosen_bridge_ids: Optional[List[str]] = None,
) -> List[Variant]:
    filtered = variants
    if way_id != "all":
        filtered = [variant for variant in filtered if variant.primary_way_id == way_id]
    if kind != "all":
        filtered = [variant for variant in filtered if variant.kind == kind]
    if cell_id != "all":
        filtered = [
            variant for variant in filtered if cell_id in variant.matrix_cells
        ]
    if outside_only:
        filtered = [variant for variant in filtered if variant.outside_market]
    if bridge_id and bridge_filter_available:
        filtered = [variant for variant in filtered if bridge_id in variant.bridge_ids]
    elif transition:
        from_cell, to_cell = transition
        filtered = [
            variant
            for variant in filtered
            if from_cell in variant.matrix_cells and to_cell in variant.matrix_cells
        ]
    if route_cells:
        # Fallback when variants don't store explicit routes: match start + target cells.
        start_cell = route_cells[0]
        target_cell = route_cells[-1]
        filtered = [
            variant
            for variant in filtered
            if start_cell in variant.matrix_cells and target_cell in variant.matrix_cells
        ]
    if chosen_bridge_ids and bridge_filter_available:
        filtered = [
            variant
            for variant in filtered
            if any(bridge_id in variant.bridge_ids for bridge_id in chosen_bridge_ids)
        ]
    if classifier_selections and any(classifier_selections.values()):
        scored: List[Tuple[float, Variant]] = []
        for variant in filtered:
            score = components.score_variant_against_classifiers(variant, classifier_selections)
            if score is not None:
                scored.append((score, variant))
        scored.sort(key=lambda item: (-item[0], item[1].title))
        filtered = [variant for _, variant in scored]
    return filtered


def _variant_card(variant: Variant, way_lookup: Dict[str, str]) -> None:
    header_cols = st.columns([4, 2])
    with header_cols[0]:
        st.markdown(f"**{variant.title}**")
        st.caption(variant.kind)
    with header_cols[1]:
        if st.button("Открыть", key=f"variant-open-{variant.id}"):
            st.session_state["selected_variant_id"] = variant.id
            st.rerun()

    st.markdown(f"**Способ:** {way_lookup.get(variant.primary_way_id, variant.primary_way_id)}")
    if variant.matrix_cells:
        cell_cols = st.columns(len(variant.matrix_cells))
        for idx, cell_id in enumerate(variant.matrix_cells):
            with cell_cols[idx]:
                if st.button(cell_id, key=f"variant-cell-{variant.id}-{cell_id}"):
                    go_to_section("Матрица", cell_id=cell_id)

    tag_cols = st.columns(3)
    with tag_cols[0]:
        st.caption("Что продаёшь")
        st.markdown(components.chips(variant.sell_tags))
    with tag_cols[1]:
        st.caption("Кому")
        st.markdown(components.chips(variant.to_whom_tags))
    with tag_cols[2]:
        st.caption("Как меряется")
        st.markdown(components.chips(variant.value_tags))

    with st.expander("Требования и первые шаги", expanded=False):
        st.markdown("**Требования**")
        for item in variant.requirements:
            st.markdown(f"- {item}")
        st.markdown("**Первые шаги**")
        for step in variant.first_steps:
            st.markdown(f"- {step}")



def render(data: AppData, filters: components.Filters) -> None:
    def _request_clear_context() -> None:
        st.session_state["request_clear_variants_context"] = True

    def _clear_classifier_filters() -> None:
        components.clear_classifier_selections()

    payload = st.session_state.get("nav_payload")
    if isinstance(payload, dict) and payload.get("section") == "Варианты (конкретика)":
        way_id = payload.get("way_id")
        cell_id = payload.get("cell_id")
        classifier = payload.get("classifier")
        variant_cell_filter = payload.get("variant_cell_filter")
        if isinstance(way_id, str):
            st.session_state["selected_way_id"] = way_id
        if isinstance(cell_id, str):
            st.session_state["selected_cell_id"] = cell_id
        if isinstance(variant_cell_filter, str):
            st.session_state["variants_filter_cell"] = variant_cell_filter
        if classifier is not None:
            components.apply_classifier_filter_request(classifier)
        st.session_state["nav_payload"] = None

    if "request_clear_variants_context" in st.session_state:
        st.session_state.pop("request_clear_variants_context")
        st.session_state["selected_cell_id"] = None
        st.session_state["selected_transition"] = None
        st.session_state["selected_bridge_id"] = None
        st.session_state["selected_route_id"] = None
        st.session_state["selected_way_id"] = None
        st.session_state["chosen_bridges_by_transition"] = {}
        st.session_state["variants_filter_cell"] = "all"

    selected_cell_id = st.session_state.get("selected_cell_id")
    selected_transition = st.session_state.get("selected_transition")
    selected_bridge_id = st.session_state.get("selected_bridge_id")
    selected_route_id = st.session_state.get("selected_route_id")
    selected_way_id = st.session_state.get("selected_way_id")
    chosen_bridges_by_transition = st.session_state.get("chosen_bridges_by_transition", {})
    classifier_selections = components.get_classifier_selection_state()
    bridge_filter_available = any(variant.bridge_ids for variant in data.variants)
    transition_pair = None
    if selected_transition and "->" in selected_transition:
        from_cell, to_cell = selected_transition.split("->", maxsplit=1)
        transition_pair = (from_cell, to_cell)
    route = next((item for item in data.paths if item.id == selected_route_id), None)

    st.title("Варианты (конкретика)")
    st.markdown("Фильтруйте варианты по способам, ячейкам и типам конкретики.")

    way_lookup = {item.id: item.name for item in data.taxonomy}
    way_options = ["all"] + sorted(way_lookup.keys())
    kind_options = ["all"] + sorted({variant.kind for variant in data.variants})
    cell_options = ["all"] + sorted({cell.id for cell in data.cells})

    if selected_cell_id and st.session_state.get("variants_filter_cell") != selected_cell_id:
        st.session_state["variants_filter_cell"] = selected_cell_id
    if selected_way_id and st.session_state.get("variants_filter_way") != selected_way_id:
        st.session_state["variants_filter_way"] = selected_way_id

    if selected_cell_id or selected_transition or selected_bridge_id or route or selected_way_id:
        axis_labels = []
        if selected_cell_id:
            axes = components.cell_to_axes(selected_cell_id) or {}
            axis_labels = [
                selected_cell_id,
                components.axis_label("risk", axes.get("risk", "low")),
                components.axis_label("activity", axes.get("activity", "active")),
                components.axis_label("scalability", axes.get("scalability", "linear")),
            ]
        chip_row = st.columns([4, 1])
        if selected_cell_id:
            chip_row[0].markdown(f"**Контекст:** {' · '.join(axis_labels)}")
        context_chips = []
        if selected_transition:
            context_chips.append(f"`{selected_transition}`")
        if selected_bridge_id:
            bridge_lookup = {bridge.id: bridge for bridge in data.bridges}
            bridge = bridge_lookup.get(selected_bridge_id)
            if bridge:
                context_chips.append(f"`Мост: {bridge.name}`")
        if selected_way_id:
            context_chips.append(f"`Способ: {way_lookup.get(selected_way_id, selected_way_id)}`")
        if route:
            route_line = " → ".join(route.sequence)
            context_chips.append(f"`Маршрут: {route.name} ({route_line})`")
        if chosen_bridges_by_transition:
            bridge_lookup = {bridge.id: bridge for bridge in data.bridges}
            for transition, bridge_id in chosen_bridges_by_transition.items():
                bridge = bridge_lookup.get(bridge_id)
                if bridge:
                    context_chips.append(f"`{transition}: {bridge.name}`")
        if context_chips:
            prefix = "**Контекст:** " if not selected_cell_id else ""
            chip_row[0].markdown(f"{prefix}{' '.join(context_chips)}")
        chip_row[1].button(
            "Сбросить",
            key="variants-clear-context",
            on_click=_request_clear_context,
        )

    classifier_lines = []
    mappings = {
        "what_sell": data.mappings.sell_items,
        "to_whom": data.mappings.to_whom_items,
        "value_measure": data.mappings.value_measures,
    }
    group_titles = {
        "what_sell": "Что продаём",
        "to_whom": "Кому",
        "value_measure": "Мера ценности",
    }
    for group, values in classifier_selections.items():
        if not values:
            continue
        labels = []
        for value in sorted(values):
            label = mappings.get(group, {}).get(value)
            labels.append(label.label if label else value)
        classifier_lines.append(f"**{group_titles.get(group, group)}:** {components.chips(labels)}")
    if classifier_lines:
        classifier_row = st.columns([4, 1])
        classifier_row[0].markdown("\n\n".join(classifier_lines))
        classifier_row[1].button(
            "Сбросить фильтры классификатора",
            key="variants-clear-classifiers",
            on_click=_clear_classifier_filters,
        )

    filter_cols = st.columns(4)
    way_id = filter_cols[0].selectbox(
        "Способ",
        way_options,
        key="variants_filter_way",
        format_func=lambda value: "Все" if value == "all" else way_lookup.get(value, value),
    )
    kind = filter_cols[1].selectbox(
        "Тип",
        kind_options,
        key="variants_filter_kind",
        format_func=lambda value: "Все" if value == "all" else value,
    )
    cell_id = filter_cols[2].selectbox(
        "Ячейка",
        cell_options,
        key="variants_filter_cell",
        format_func=lambda value: "Все" if value == "all" else value,
    )
    outside_only = filter_cols[3].checkbox(
        "Только вне рынка",
        key="variants_filter_outside",
    )

    filtered_variants = components.apply_global_filters_to_variants(data.variants, filters)
    filtered_variants = _filter_variants(
        filtered_variants,
        way_id,
        kind,
        cell_id,
        outside_only,
        transition_pair,
        selected_bridge_id,
        bridge_filter_available,
        classifier_selections=classifier_selections,
        route_cells=route.sequence if route else None,
        chosen_bridge_ids=list(chosen_bridges_by_transition.values()) if chosen_bridges_by_transition else None,
    )

    if not filtered_variants:
        st.info("Ничего не найдено по фильтрам.")
        return

    list_col, detail_col = st.columns([2, 1])

    with list_col:
        st.markdown(f"**Найдено вариантов:** {len(filtered_variants)}")
        for variant in filtered_variants:
            with st.container(border=True):
                _variant_card(variant, way_lookup)

    with detail_col:
        st.markdown("### Детали выбранного варианта")
        selected_id = st.session_state.get("selected_variant_id")
        selected = data.variant_by_id.get(selected_id) if selected_id else None
        if not selected:
            st.caption("Выберите вариант слева.")
        else:
            st.markdown(f"**{selected.title}**")
            st.caption(selected.kind)
            st.markdown("**Первые шаги**")
            for step in selected.first_steps:
                st.markdown(f"- {step}")
            st.markdown("**Метрики успеха**")
            for metric in selected.success_metrics:
                st.markdown(f"- {metric}")
            if selected.related_variant_ids:
                st.markdown("**Связанные варианты**")
                for rel_id in selected.related_variant_ids:
                    rel = data.variant_by_id.get(rel_id)
                    if rel:
                        if st.button(rel.title, key=f"variant-related-{selected.id}-{rel_id}"):
                            st.session_state["selected_variant_id"] = rel_id
                            st.rerun()
            st.markdown("**Навигация**")
            if st.button("Открыть способ", key=f"variant-open-way-{selected.id}"):
                go_to_section("Способы получения денег", way_id=selected.primary_way_id, tab="Справочник")
            if selected.matrix_cells:
                if st.button("Открыть ячейку матрицы", key=f"variant-open-cell-{selected.id}"):
                    go_to_section("Матрица", cell_id=selected.matrix_cells[0])
