from __future__ import annotations

import streamlit as st

from money_map.ui import components
from money_map.ui.views import (
    bridges,
    classify,
    graph,
    matrix,
    overview,
    paths,
    search,
    variants,
    ways_money,
)


def _sidebar_status(data) -> None:
    st.sidebar.success("Данные загружены")
    st.sidebar.markdown(f"**Способы получения денег:** {len(data.taxonomy)}")
    st.sidebar.markdown(f"**Варианты:** {len(data.variants)}")
    st.sidebar.markdown(f"**Мосты:** {len(data.bridges)}")
    st.sidebar.markdown(f"**Маршруты:** {len(data.paths)}")


def main() -> None:
    st.set_page_config(page_title="Money Map — интерфейс", layout="wide")
    components.init_session_state()
    components.apply_pending_navigation()
    components.load_css()

    data, errors = components.load_data()
    if errors:
        st.error("Данные содержат ошибки. Исправьте их перед работой с UI.")
        for err in errors:
            st.write(f"- {err}")
        st.stop()

    if "nav_intent" in st.session_state:
        intent = st.session_state.pop("nav_intent")
        if isinstance(intent, dict):
            section = intent.get("section")
            payload = intent.get("payload")
            if isinstance(section, str):
                st.session_state["nav_section"] = section
            if isinstance(payload, dict):
                st.session_state["nav_payload"] = payload

    st.sidebar.title("Money Map")
    if st.sidebar.button("Обновить данные"):
        components.reset_cache()
        st.experimental_rerun()

    _sidebar_status(data)

    if "request_nav_section" in st.session_state:
        requested = st.session_state.pop("request_nav_section")
        st.session_state["nav_section"] = requested
        if requested in components.PAGES:
            components.set_page(requested)
    if "request_selected_way_id" in st.session_state:
        way_id = st.session_state.pop("request_selected_way_id")
        st.session_state["selected_way_id"] = way_id
        st.session_state["selected_tax_id"] = way_id
        st.session_state["selected_taxonomy"] = way_id
    if "request_selected_cell_id" in st.session_state:
        cell_id = st.session_state.pop("request_selected_cell_id")
        components.set_selected_cell(cell_id)
        st.session_state["matrix_focus_cell"] = cell_id
    if "request_matrix_focus_cell" in st.session_state:
        focus_cell = st.session_state.pop("request_matrix_focus_cell")
        st.session_state["matrix_focus_cell"] = focus_cell
        components.set_selected_cell(focus_cell)
    if "request_selected_variant_id" in st.session_state:
        variant_id = st.session_state.pop("request_selected_variant_id")
        st.session_state["selected_variant_id"] = variant_id
    if "request_variant_cell_filter" in st.session_state:
        cell_id = st.session_state.pop("request_variant_cell_filter")
        st.session_state["variants_filter_cell"] = cell_id
    if "request_selected_transition" in st.session_state:
        st.session_state["selected_transition"] = st.session_state.pop("request_selected_transition")
    if "request_selected_bridge_id" in st.session_state:
        st.session_state["selected_bridge_id"] = st.session_state.pop("request_selected_bridge_id")
    if "request_selected_route_id" in st.session_state:
        route_id = st.session_state.pop("request_selected_route_id")
        st.session_state["selected_route_id"] = route_id
        st.session_state["selected_path"] = route_id
    if "request_classifier_filters" in st.session_state:
        request = st.session_state.pop("request_classifier_filters")
        components.apply_classifier_filter_request(request)
    if "request_filter_risk" in st.session_state:
        st.session_state["filter_risk"] = st.session_state.pop("request_filter_risk")
    if "request_filter_activity" in st.session_state:
        st.session_state["filter_activity"] = st.session_state.pop("request_filter_activity")
    if "request_filter_scalability" in st.session_state:
        st.session_state["filter_scalability"] = st.session_state.pop("request_filter_scalability")
    if "request_matrix_axis_risk" in st.session_state:
        st.session_state["matrix_axis_risk"] = st.session_state.pop("request_matrix_axis_risk")
    if "request_matrix_axis_activity" in st.session_state:
        st.session_state["matrix_axis_activity"] = st.session_state.pop("request_matrix_axis_activity")
    if "request_matrix_axis_scalability" in st.session_state:
        st.session_state["matrix_axis_scalability"] = st.session_state.pop("request_matrix_axis_scalability")

    st.sidebar.markdown("### Навигация")
    current_page = st.session_state.get("nav_section", components.DEFAULT_PAGE)
    if current_page not in components.PAGES:
        current_page = components.DEFAULT_PAGE
        st.session_state["nav_section"] = current_page
    page = st.sidebar.radio(
        "Разделы",
        components.PAGES,
        index=components.PAGES.index(current_page),
        key="nav_section",
    )
    components.set_page(page)

    filters = components.sidebar_filters()

    if page == "Обзор":
        overview.render(data)
    elif page == "Матрица":
        matrix.render(data, filters)
    elif page == "Мосты":
        bridges.render(data, filters)
    elif page == "Маршруты":
        paths.render(data, filters)
    elif page == "Поиск":
        search.render(data)
    elif page == "Классификатор":
        classify.render(data)
    elif page == "Граф":
        graph.render(data, filters)
    elif page == "Способы получения денег":
        ways_money.render(data, filters)
    elif page == "Варианты (конкретика)":
        variants.render(data, filters)


if __name__ == "__main__":
    main()
