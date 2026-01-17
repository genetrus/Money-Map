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
    taxonomy,
    taxonomy_graph,
)


def _sidebar_status(data) -> None:
    st.sidebar.success("Данные загружены")
    st.sidebar.markdown(f"**Таксономия:** {len(data.taxonomy)}")
    st.sidebar.markdown(f"**Мосты:** {len(data.bridges)}")
    st.sidebar.markdown(f"**Маршруты:** {len(data.paths)}")


def main() -> None:
    st.set_page_config(page_title="Money Map — интерфейс", layout="wide")
    components.init_session_state()
    components.load_css()

    data, errors = components.load_data()
    if errors:
        st.error("Данные содержат ошибки. Исправьте их перед работой с UI.")
        for err in errors:
            st.write(f"- {err}")
        st.stop()

    st.sidebar.title("Money Map")
    if st.sidebar.button("Обновить данные"):
        components.reset_cache()
        st.experimental_rerun()

    _sidebar_status(data)

    st.sidebar.markdown("### Навигация")
    current_page = st.session_state.get("page", components.DEFAULT_PAGE)
    page = st.sidebar.radio(
        "Разделы",
        components.PAGES,
        index=components.PAGES.index(current_page),
    )
    components.set_page(page)

    filters = components.sidebar_filters()

    if page == "Обзор":
        overview.render(data)
    elif page == "Матрица":
        matrix.render(data, filters)
    elif page == "Таксономия":
        taxonomy.render(data)
    elif page == "Мосты":
        bridges.render(data, filters)
    elif page == "Маршруты":
        paths.render(data)
    elif page == "Поиск":
        search.render(data)
    elif page == "Классификатор":
        classify.render(data)
    elif page == "Граф: 14 способов":
        taxonomy_graph.render(data)
    elif page == "Граф":
        graph.render(data, filters)


if __name__ == "__main__":
    main()
