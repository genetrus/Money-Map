from __future__ import annotations

import streamlit as st

from money_map.core.model import AppData
from money_map.ui import components


def render(data: AppData) -> None:
    st.title("Обзор карты доходов")
    st.markdown(
        """
        **Money Map** — это карта способов заработка, которая объединяет формулу
        _что продаём / кому / за какую меру ценности_, матрицу 2×2×2 и таксономию
        механизмов дохода. Этот интерфейс помогает быстро найти ячейки, маршруты
        и мосты переходов между ними.
        """
    )

    st.subheader("Ключевые показатели")
    cols = st.columns(4)
    cols[0].metric("Ячейки", len(data.cells))
    cols[1].metric("Таксономия", len(data.taxonomy))
    cols[2].metric("Мосты", len(data.bridges))
    cols[3].metric("Маршруты", len(data.paths))

    st.subheader("Быстрая навигация")
    st.markdown("Выберите раздел или используйте кнопки ниже:")
    nav_cols = st.columns(4)
    if nav_cols[0].button("Матрица", use_container_width=True):
        components.set_page("Матрица")
    if nav_cols[1].button("Таксономия", use_container_width=True):
        components.set_page("Таксономия")
    if nav_cols[2].button("Мосты", use_container_width=True):
        components.set_page("Мосты")
    if nav_cols[3].button("Граф", use_container_width=True):
        components.set_page("Граф")

    st.subheader("Типовой коридор")
    st.markdown(
        """
        Ниже пример «типового коридора», который показывает переход
        от активного линейного дохода к более масштабируемым стратегиям.
        """
    )
    st.code("A1 → A2 → P1 → P2", language="text")
