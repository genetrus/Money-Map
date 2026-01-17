from __future__ import annotations

import streamlit as st

from money_map.core.model import AppData
from money_map.ui import components


def _match(text: str, needle: str) -> bool:
    return needle in text.lower()


def render(data: AppData) -> None:
    st.title("Поиск")
    st.markdown("Поиск по таксономии, мостам, ячейкам и маршрутам.")

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

    st.markdown(
        f"**Результаты:** Таксономия ({len(taxonomy_results)}), "
        f"Мосты ({len(bridge_results)}), "
        f"Ячейки ({len(cell_results)}), "
        f"Маршруты ({len(path_results)})"
    )

    with st.expander(f"Таксономия ({len(taxonomy_results)})", expanded=True):
        if not taxonomy_results:
            st.caption("Ничего не найдено.")
        for item in taxonomy_results:
            if st.button(
                f"{item.name} ({item.id})",
                key=f"search-tax-{item.id}",
                use_container_width=True,
            ):
                components.set_selected_taxonomy(item.id)
                components.set_page("Таксономия")

    with st.expander(f"Мосты ({len(bridge_results)})", expanded=False):
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

    with st.expander(f"Ячейки ({len(cell_results)})", expanded=False):
        if not cell_results:
            st.caption("Ничего не найдено.")
        for cell in cell_results:
            if st.button(
                f"{cell.id} — {cell.label}",
                key=f"search-cell-{cell.id}",
                use_container_width=True,
            ):
                components.set_selected_cell(cell.id)
                components.set_page("Матрица")

    with st.expander(f"Маршруты ({len(path_results)})", expanded=False):
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
