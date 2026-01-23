from __future__ import annotations

from typing import Optional

import streamlit as st


def go_to_section(
    section_name: str,
    *,
    way_id: Optional[str] = None,
    cell_id: Optional[str] = None,
    transition: Optional[str] = None,
    bridge_id: Optional[str] = None,
    route_id: Optional[str] = None,
    variant_id: Optional[str] = None,
    classifier: Optional[object] = None,
    tab: Optional[str] = None,
    open_tab: Optional[str] = None,
    variant_cell_filter: Optional[str] = None,
) -> None:
    section_aliases = {
        "matrix": "Матрица",
        "ways": "Способы получения денег",
        "variants": "Варианты (конкретика)",
        "bridges": "Мосты",
        "paths": "Маршруты",
        "routes": "Маршруты",
        "overview": "Обзор",
        "graph": "Граф",
        "search": "Поиск",
        "classifier": "Классификатор",
    }
    tab_aliases = {
        "directory": "Справочник",
        "map": "Карта",
    }
    target_section = section_aliases.get(section_name, section_name)
    target_tab = tab
    if open_tab is not None:
        target_tab = tab_aliases.get(open_tab, open_tab)

    payload: dict[str, object] = {"section": target_section}
    if way_id is not None:
        payload["way_id"] = way_id
    if cell_id is not None:
        payload["cell_id"] = cell_id
    if transition is not None:
        payload["transition"] = transition
    if bridge_id is not None:
        payload["bridge_id"] = bridge_id
    if route_id is not None:
        payload["route_id"] = route_id
    if variant_id is not None:
        payload["variant_id"] = variant_id
    if classifier is not None:
        payload["classifier"] = classifier
    if variant_cell_filter is not None:
        payload["variant_cell_filter"] = variant_cell_filter
    if target_tab is not None:
        payload["tab"] = target_tab
    params = dict(payload)
    params.pop("section", None)
    st.session_state["pending_nav"] = {"section": target_section, "params": params}
    st.rerun()
