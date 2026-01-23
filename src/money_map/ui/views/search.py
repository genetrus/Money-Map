from __future__ import annotations

import streamlit as st

from money_map.core.model import AppData
from money_map.ui import components
from money_map.ui.state import go_to_section


def _match(text: str, needle: str) -> bool:
    return needle in text.lower()


def render(data: AppData) -> None:
    st.title("Поиск")
    st.markdown("Поиск по способам получения денег, мостам, ячейкам, маршрутам и вариантам.")

    query = st.text_input("Введите запрос", key="search_query")
    if not query:
        st.info("Введите текст, чтобы начать поиск.")
        return

    needle = query.lower()

    taxonomy_results = [
        item
        for item in data.taxonomy
        if _match(
            " ".join([item.name, item.description, " ".join(item.examples)]),
            needle,
        )
    ]
    bridge_results = [
        bridge
        for bridge in data.bridges
        if _match(
            " ".join(
                [
                    bridge.name,
                    bridge.notes,
                    " ".join(bridge.checks),
                    " ".join(bridge.mechanisms),
                ]
            ),
            needle,
        )
    ]
    cell_results = [
        cell
        for cell in data.cells
        if _match(" ".join([cell.label, cell.short, " ".join(cell.examples)]), needle)
    ]
    path_results = [
        path
        for path in data.paths
        if _match(
            " ".join([path.name, path.note, " ".join(path.sequence)]),
            needle,
        )
    ]
    variant_results = [
        variant
        for variant in data.variants
        if _match(
            " ".join(
                [
                    variant.title,
                    variant.kind,
                    " ".join(variant.requirements),
                    " ".join(variant.first_steps),
                    " ".join(variant.sell_tags),
                    " ".join(variant.to_whom_tags),
                    " ".join(variant.value_tags),
                ]
            ),
            needle,
        )
    ]

    st.markdown(
        f"**Результаты:** Способы ({len(taxonomy_results)}), "
        f"Мосты ({len(bridge_results)}), "
        f"Ячейки ({len(cell_results)}), "
        f"Маршруты ({len(path_results)}), "
        f"Варианты ({len(variant_results)})"
    )

    tabs = st.tabs(
        [
            f"Способы ({len(taxonomy_results)})",
            f"Варианты ({len(variant_results)})",
            f"Мосты ({len(bridge_results)})",
            f"Ячейки ({len(cell_results)})",
            f"Маршруты ({len(path_results)})",
        ]
    )

    with tabs[0]:
        if not taxonomy_results:
            st.caption("Ничего не найдено.")
        for item in taxonomy_results:
            if st.button(
                f"{item.name} ({item.id})",
                key=f"search-tax-{item.id}",
                use_container_width=True,
            ):
                go_to_section("Способы получения денег", way_id=item.id, tab="Справочник")

    with tabs[1]:
        if not variant_results:
            st.caption("Ничего не найдено.")
        for variant in variant_results:
            if st.button(
                f"{variant.title} ({variant.kind})",
                key=f"search-variant-{variant.id}",
                use_container_width=True,
            ):
                go_to_section(
                    "Варианты (конкретика)",
                    variant_id=variant.id,
                    way_id=variant.primary_way_id,
                )

    with tabs[2]:
        if not bridge_results:
            st.caption("Ничего не найдено.")
        for bridge in bridge_results:
            if st.button(
                f"{bridge.name} ({bridge.from_cell} → {bridge.to_cell})",
                key=f"search-bridge-{bridge.id}",
                use_container_width=True,
            ):
                components.set_selected_bridge(bridge.id)
                components.set_page("Мосты")

    with tabs[3]:
        if not cell_results:
            st.caption("Ничего не найдено.")
        for cell in cell_results:
            if st.button(
                f"{cell.id} — {cell.label}",
                key=f"search-cell-{cell.id}",
                use_container_width=True,
            ):
                go_to_section("Матрица", cell_id=cell.id)

    with tabs[4]:
        if not path_results:
            st.caption("Ничего не найдено.")
        for path in path_results:
            if st.button(
                f"{path.name} ({components.ascii_path(path)})",
                key=f"search-path-{path.id}",
                use_container_width=True,
            ):
                components.set_selected_path(path.id)
                components.set_page("Маршруты")
