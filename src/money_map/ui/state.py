from __future__ import annotations

from typing import Optional

import streamlit as st


def go_to_section(
    section_name: str,
    *,
    way_id: Optional[str] = None,
    cell_id: Optional[str] = None,
    variant_id: Optional[str] = None,
    tab: Optional[str] = None,
    variant_cell_filter: Optional[str] = None,
) -> None:
    st.session_state["request_nav_section"] = section_name
    if way_id is not None:
        st.session_state["request_selected_way_id"] = way_id
    if cell_id is not None:
        st.session_state["request_selected_cell_id"] = cell_id
        st.session_state["request_matrix_focus_cell"] = cell_id
    if variant_id is not None:
        st.session_state["request_selected_variant_id"] = variant_id
    if variant_cell_filter is not None:
        st.session_state["request_variant_cell_filter"] = variant_cell_filter
    if tab is not None:
        st.session_state["request_tab"] = tab
    st.rerun()
