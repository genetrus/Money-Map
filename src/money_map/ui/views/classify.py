from __future__ import annotations

import streamlit as st

from money_map.core.classify import classify_by_tags, classify_by_text
from money_map.core.model import AppData


def _render_results(result) -> None:
    st.markdown("### Результаты")
    st.write("**Теги:**", result.tags)

    st.markdown("**Таксономия:**")
    if not result.taxonomy_scores:
        st.caption("Совпадений нет.")
    else:
        for item_id, score in result.taxonomy_scores:
            st.write(f"- {item_id}: {score}")

    st.markdown("**Ячейки:**")
    if not result.cell_scores:
        st.caption("Совпадений нет.")
    else:
        for cell_id, score in result.cell_scores:
            st.write(f"- {cell_id}: {score}")

    st.markdown("**Объяснение:**")
    if result.explanation:
        for line in result.explanation:
            st.write(f"- {line}")
    else:
        st.caption("Нет объяснений.")

    st.markdown(f"**Уверенность:** {result.confidence}")


def render(data: AppData) -> None:
    st.title("Классификатор")
    st.markdown("Сопоставьте описание с таксономией и ячейками матрицы.")

    tab_structured, tab_text = st.tabs(["Структурированные теги", "Текстовый режим"])

    sell_tags = sorted(data.mappings.sell_items.keys())
    to_tags = sorted(data.mappings.to_whom_items.keys())
    value_tags = sorted(data.mappings.value_measures.keys())

    with tab_structured:
        st.markdown("Выберите теги и запустите классификацию.")
        sell = st.multiselect("Что продаём", sell_tags)
        to_whom = st.multiselect("Кому", to_tags)
        value = st.multiselect("Мера ценности", value_tags)
        top_n = st.slider("Топ-N результатов", min_value=3, max_value=10, value=5)

        if st.button("Классифицировать", key="classify-structured"):
            result = classify_by_tags(data, sell=sell, to_whom=to_whom, value=value, top_n=top_n)
            _render_results(result)

    with tab_text:
        st.markdown("Введите текст, чтобы подобрать подходящие теги.")
        text = st.text_area("Описание", height=150)
        top_n_text = st.slider("Топ-N результатов", min_value=3, max_value=10, value=5, key="topn-text")
        if st.button("Классифицировать текст", key="classify-text"):
            if not text.strip():
                st.warning("Введите текст для классификации.")
            else:
                result = classify_by_text(data, text, top_n=top_n_text)
                _render_results(result)
