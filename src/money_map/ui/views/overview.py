from __future__ import annotations

import streamlit as st

from money_map.core.model import AppData
from money_map.ui import components
from money_map.ui.state import go_to_section


def render(data: AppData) -> None:
    st.title("Обзор карты доходов")
    st.markdown(
        """
        **Money Map** — это карта способов заработка, которая объединяет формулу
        _что продаём / кому / за какую меру ценности_, матрицу 2×2×2 и способы
        получения денег. Этот интерфейс помогает быстро найти ячейки, маршруты
        и мосты переходов между ними, а также перейти к конкретным вариантам.
        """
    )

    st.subheader("Ключевые показатели")
    cols = st.columns(4)
    cols[0].metric("Ячейки", len(data.cells))
    cols[1].metric("Способы получения денег", len(data.taxonomy))
    cols[2].metric("Мосты", len(data.bridges))
    cols[3].metric("Маршруты", len(data.paths))

    st.subheader("Быстрая навигация")
    st.markdown("Выберите раздел или используйте кнопки ниже:")
    nav_cols = st.columns(4)
    if nav_cols[0].button("Матрица", use_container_width=True):
        go_to_section("Матрица")
    if nav_cols[1].button("Способы получения денег", use_container_width=True):
        go_to_section("Способы получения денег")
    if nav_cols[2].button("Мосты", use_container_width=True):
        go_to_section("Мосты")
    if nav_cols[3].button("Граф", use_container_width=True):
        go_to_section("Граф")

    st.subheader("Инструкция: как выбрать и прийти к цели")
    st.markdown(
        """
        **1. Определи режим (Матрица 2×2×2)**  
        A1/A2/P1/P2/A3/A4/P3/P4 — это 8 режимов по риску, активности и масштабируемости.  
        Выбор по цели:
        1. **Стабильный кэш** → A1 (и P1 как вторая опора).
        2. **Рост без лотереи** → A2 + P2.
        3. **Пассивная база** → P1.
        4. **Выстрел/лотерея** → A4/P4 (с осознанным риском).

        **2. Выбери 1–2 способа из 14**  
        Перейди в раздел **«Способы получения денег»** и выбери базовые механизмы.

        **3. Перейди к конкретике: «Варианты»**  
        Вариант = конкретная работа/бизнес/услуга/актив. Фильтруй:
        1. по ячейке матрицы,
        2. по способу,
        3. по kind,
        4. по «вне рынка».

        **4. Если нужен рост — выбери мосты**  
        Мост = «что поменять», чтобы перейти из клетки в клетку (A1 → A2 и т.д.).

        **5. Собери маршрут**  
        Маршрут = цепочка мостов, то есть план перехода.

        **6. Сформируй план действий на 7 дней**  
        День 1: выбрать клетку + 2 способа.  
        День 2: выбрать 3–5 вариантов.  
        День 3: выбрать 1 мост и прописать действия.  
        День 4–7: выполнить шаги first_steps из выбранного варианта.
        """
    )

    st.subheader("Мини-мастер выбора")
    goal = st.radio(
        "Моя цель",
        ["Стабильность", "Рост", "Пассивная база", "Эксперимент"],
        key="overview_goal",
        horizontal=True,
    )
    if st.button("Показать рекомендуемые клетки", key="overview_show_cells"):
        st.session_state["overview_show_cells"] = True

    recommended = {
        "Стабильность": ["A1", "P1"],
        "Рост": ["A2", "P2"],
        "Пассивная база": ["P1"],
        "Эксперимент": ["A4", "P4"],
    }[goal]

    if st.session_state.get("overview_show_cells"):
        st.markdown("**Рекомендуемые клетки:** " + ", ".join(recommended))
        action_cols = st.columns(3)
        if action_cols[0].button("Открыть Матрицу", use_container_width=True):
            go_to_section("Матрица", cell_id=recommended[0])
        if action_cols[1].button("Открыть Способы получения денег", use_container_width=True):
            go_to_section("Способы получения денег")
        if action_cols[2].button("Открыть Варианты (конкретика)", use_container_width=True):
            go_to_section(
                "Варианты (конкретика)",
                variant_cell_filter=recommended[0],
            )

    st.subheader("Типовой коридор")
    st.markdown(
        """
        Ниже пример «типового коридора», который показывает переход
        от активного линейного дохода к более масштабируемым стратегиям.
        """
    )
    st.code("A1 → A2 → P1 → P2", language="text")
