from __future__ import annotations

from typing import Dict, List

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
    st.title("Варианты (конкретика)")
    st.markdown("Фильтруйте варианты по способам, ячейкам и типам конкретики.")

    way_lookup = {item.id: item.name for item in data.taxonomy}
    way_options = ["all"] + sorted(way_lookup.keys())
    kind_options = ["all"] + sorted({variant.kind for variant in data.variants})
    cell_options = ["all"] + sorted({cell.id for cell in data.cells})

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
    filtered_variants = _filter_variants(filtered_variants, way_id, kind, cell_id, outside_only)

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
