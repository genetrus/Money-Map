from __future__ import annotations

from typing import Iterable, Optional

import streamlit as st

from money_map.core.classify import classify_by_tags
from money_map.core.model import AppData, TaxonomyItem
from money_map.ui import components
from money_map.ui.state import go_to_section


GROUP_CONFIG = {
    "what_sell": {"label": "Что продаём", "color": "#2A9D8F"},
    "to_whom": {"label": "Кому", "color": "#E9C46A"},
    "value_measure": {"label": "Мера ценности", "color": "#8E6AC8"},
}

GROUP_ORDER = ("what_sell", "to_whom", "value_measure")

CLASSIFIER_DETAILS = {
    "what_sell": {
        "time": {
            "short_definition": "Оплата за время участия или присутствия.",
            "examples": ["Оклад", "Почасовая ставка"],
        },
        "result": {
            "short_definition": "Оплата за достижение результата или выполнение задачи.",
            "examples": ["Фикс за проект", "Бонус за KPI"],
        },
        "risk": {
            "short_definition": "Оплата за принятие риска или ответственности.",
            "examples": ["Процент от сделки", "Ответственность за исход"],
        },
        "access": {
            "short_definition": "Оплата за предоставление доступа к ресурсу или каналу.",
            "examples": ["Подписка", "Аренда доступа"],
        },
        "attention": {
            "short_definition": "Оплата за внимание и охваты аудитории.",
            "examples": ["Реклама", "Спонсорство"],
        },
        "capital": {
            "short_definition": "Доход за предоставление капитала или ресурсов.",
            "examples": ["Инвестиции", "Кредит"],
        },
        "property": {
            "short_definition": "Доход за использование собственности.",
            "examples": ["Аренда имущества", "Лицензия"],
        },
    },
    "to_whom": {
        "single_client": {
            "short_definition": "Сделка с одним клиентом или заказчиком.",
            "examples": ["Консалтинг", "Проектная работа"],
        },
        "many_people": {
            "short_definition": "Продажа многим людям и массовой аудитории.",
            "examples": ["Потребительский продукт", "Онлайн-курс"],
        },
        "market": {
            "short_definition": "Сделка на рынке или бирже.",
            "examples": ["Трейдинг", "Арбитраж"],
        },
        "platform": {
            "short_definition": "Сделка через платформу или маркетплейс.",
            "examples": ["Маркетплейс", "App Store"],
        },
        "state": {
            "short_definition": "Сделка с государством и госпрограммами.",
            "examples": ["Госзакупки", "Грант"],
        },
    },
    "value_measure": {
        "rate": {
            "short_definition": "Оплата по ставке за единицу времени или нормы.",
            "examples": ["Почасовая ставка", "Оклад"],
        },
        "price": {
            "short_definition": "Фиксированная цена за продукт или услугу.",
            "examples": ["Разовая продажа", "Пакет услуг"],
        },
        "percent": {
            "short_definition": "Доля или процент от результата.",
            "examples": ["Комиссия", "Роялти"],
        },
        "rent": {
            "short_definition": "Регулярная рента за пользование активом.",
            "examples": ["Аренда", "Лизинг"],
        },
        "payout": {
            "short_definition": "Выплата, купон или дивиденд.",
            "examples": ["Дивиденды", "Купон по облигации"],
        },
        "appreciation": {
            "short_definition": "Рост стоимости актива или доли.",
            "examples": ["Рост цены", "Продажа с прибылью"],
        },
    },
}


def _build_classifier_items(data: AppData) -> list[dict]:
    tag_keywords = data.keywords.keywords.get("tags", {})
    items: list[dict] = []
    group_sources = [
        ("what_sell", data.mappings.sell_items, "sell"),
        ("to_whom", data.mappings.to_whom_items, "to_whom"),
        ("value_measure", data.mappings.value_measures, "value"),
    ]
    for group, mapping, keyword_group in group_sources:
        details = CLASSIFIER_DETAILS.get(group, {})
        for item_id, item in mapping.items():
            detail = details.get(item_id, {})
            items.append(
                {
                    "id": item_id,
                    "classifier_id": f"{group}.{item_id}",
                    "group": group,
                    "name": item.label,
                    "keywords": tag_keywords.get(keyword_group, {}).get(item_id, []),
                    "short_definition": detail.get("short_definition") or item.notes or "—",
                    "examples": detail.get("examples", []),
                }
            )
    return items


def _selection_snapshot() -> dict[str, set[str]]:
    return components.get_classifier_selection_state()


def _toggle_classifier(group: str, tag_id: str) -> None:
    key = components.CLASSIFIER_SELECTION_KEYS[group]
    selected = set(st.session_state.get(key, set()))
    if tag_id in selected:
        selected.remove(tag_id)
    else:
        selected.add(tag_id)
    st.session_state[key] = selected
    components.sync_classifier_filters_from_state()


def _reset_classifier() -> None:
    components.clear_classifier_selections()


def _select_popular() -> None:
    st.session_state["classifier_selected_what_sell"] = {"time"}
    st.session_state["classifier_selected_to_whom"] = {"single_client"}
    st.session_state["classifier_selected_value_measure"] = {"rate"}
    components.sync_classifier_filters_from_state()


def _legend() -> None:
    parts = []
    for group in GROUP_ORDER:
        config = GROUP_CONFIG[group]
        color = config["color"]
        label = config["label"]
        parts.append(f"<span style='color:{color}'>●</span> {label}")
    st.markdown(" ".join(parts), unsafe_allow_html=True)


def _deal_formula_lines(selections: dict[str, set[str]], data: AppData) -> list[str]:
    mapping_lookup = {
        "what_sell": data.mappings.sell_items,
        "to_whom": data.mappings.to_whom_items,
        "value_measure": data.mappings.value_measures,
    }
    lines = []
    for group in GROUP_ORDER:
        label = GROUP_CONFIG[group]["label"]
        values = selections.get(group, set())
        if not values:
            line_value = "—"
        else:
            items = mapping_lookup.get(group, {})
            line_value = " + ".join(
                items[item_id].label if item_id in items else item_id
                for item_id in sorted(values)
            )
        lines.append(f"**{label}:** {line_value}")
    return lines


def _meaning_text(selections: dict[str, set[str]]) -> str:
    sell = selections.get("what_sell", set())
    to_whom = selections.get("to_whom", set())
    value = selections.get("value_measure", set())
    if "time" in sell and "rate" in value:
        return "Похоже на оплату за участие или время."
    if "result" in sell and "price" in value:
        return "Похоже на оплату за результат или задачу."
    if "attention" in sell and "platform" in to_whom:
        return "Похоже на монетизацию внимания через платформу."
    if "risk" in sell and "percent" in value:
        return "Похоже на участие в риске за процент."
    if "capital" in sell and "payout" in value:
        return "Похоже на доход за предоставление капитала."
    if any(selections.values()):
        return "Комбинация описывает природу сделки. Проверь совпадения ниже."
    return "Выберите чипсы, чтобы увидеть формулу сделки и совпадения."


def _score_way(item: TaxonomyItem, selections: dict[str, set[str]]) -> float:
    profile = {
        "what_sell": set(item.sell),
        "to_whom": set(item.to_whom),
        "value_measure": set(item.value),
    }
    score = 0.0
    for group, selected in selections.items():
        if not selected:
            continue
        score += len(selected.intersection(profile.get(group, set()))) * 2.0
    return score


def _top_matches(items: Iterable[TaxonomyItem], selections: dict[str, set[str]]) -> list[tuple[TaxonomyItem, float]]:
    matches = []
    for item in items:
        score = _score_way(item, selections)
        if score > 0:
            matches.append((item, score))
    matches.sort(key=lambda pair: (-pair[1], pair[0].name))
    return matches


def _render_chip_row(
    items: Iterable[tuple[str, str]],
    on_click,
    key_prefix: str,
    columns: int = 3,
    selected: Optional[set[str]] = None,
) -> None:
    row: list[tuple[str, str]] = []
    for item in items:
        row.append(item)
        if len(row) == columns:
            cols = st.columns(columns)
            for idx, (item_id, label) in enumerate(row):
                is_selected = selected and item_id in selected
                cols[idx].button(
                    label,
                    key=f"{key_prefix}-{item_id}",
                    on_click=on_click,
                    args=(item_id,),
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                )
            row = []
    if row:
        cols = st.columns(columns)
        for idx, (item_id, label) in enumerate(row):
            is_selected = selected and item_id in selected
            cols[idx].button(
                label,
                key=f"{key_prefix}-{item_id}",
                on_click=on_click,
                args=(item_id,),
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            )


def render(data: AppData) -> None:
    payload = st.session_state.get("nav_payload")
    if isinstance(payload, dict) and payload.get("section") == "Классификатор":
        request = payload.get("classifier")
        if request is not None:
            components.apply_classifier_filter_request(request)
        st.session_state["nav_payload"] = None

    components.sync_classifier_filters_from_state()
    selections = _selection_snapshot()
    classifier_items = _build_classifier_items(data)

    st.title("Классификатор")
    st.caption("1) Выбери чипсы  2) Посмотри формулу и совпадения  3) Открой конкретику")

    mode = st.radio(
        "Режим",
        ["panel", "directory"],
        key="classifier_mode",
        horizontal=True,
        format_func=lambda value: "Панель" if value == "panel" else "Справочник",
    )

    if mode == "panel":
        header_cols = st.columns([3, 1])
        with header_cols[0]:
            _legend()
        with header_cols[1]:
            st.button(
                "Сбросить",
                key="classifier-reset",
                on_click=_reset_classifier,
                use_container_width=True,
            )

        st.button(
            "Выбрать популярное",
            key="classifier-popular",
            on_click=_select_popular,
        )

        select_cols = st.columns(3)
        group_options = {
            "what_sell": sorted(data.mappings.sell_items.items(), key=lambda item: item[1].label),
            "to_whom": sorted(data.mappings.to_whom_items.items(), key=lambda item: item[1].label),
            "value_measure": sorted(data.mappings.value_measures.items(), key=lambda item: item[1].label),
        }
        for idx, group in enumerate(GROUP_ORDER):
            with select_cols[idx]:
                label = GROUP_CONFIG[group]["label"]
                color = GROUP_CONFIG[group]["color"]
                st.markdown(f"<span style='color:{color}'><b>{label}</b></span>", unsafe_allow_html=True)

                def _toggle(item_id: str, group_key: str = group) -> None:
                    _toggle_classifier(group_key, item_id)

                _render_chip_row(
                    [(item_id, item.label) for item_id, item in group_options[group]],
                    _toggle,
                    f"classifier-chip-{group}",
                    columns=2,
                    selected=selections.get(group, set()),
                )

        st.markdown("### Формула сделки")
        with st.container(border=True):
            for line in _deal_formula_lines(selections, data):
                st.markdown(line)
            st.caption(_meaning_text(selections))

        st.markdown("### Где это встречается")
        card_cols = st.columns(3)

        has_selection = any(selections.values())
        matches = _top_matches(data.taxonomy, selections) if has_selection else []
        probable_cells = []
        if has_selection:
            result = classify_by_tags(
                data,
                sell=sorted(selections.get("what_sell", set())),
                to_whom=sorted(selections.get("to_whom", set())),
                value=sorted(selections.get("value_measure", set())),
                top_n=3,
            )
            probable_cells = [cell_id for cell_id, _ in result.cell_scores[:3]]
        primary_cell = probable_cells[0] if probable_cells else None
        with card_cols[0]:
            with st.container(border=True):
                st.markdown("**Способы (14)**")
                st.caption(f"Совпадений: {len(matches)}")
                if matches:
                    top = matches[:8]
                    _render_chip_row(
                        [(item.id, item.name) for item, _ in top],
                        lambda item_id: go_to_section("ways", way_id=item_id, open_tab="directory"),
                        "classifier-way",
                        columns=2,
                    )
                    if len(matches) > len(top):
                        with st.expander("Показать все"):
                            _render_chip_row(
                                [(item.id, item.name) for item, _ in matches],
                                lambda item_id: go_to_section("ways", way_id=item_id, open_tab="directory"),
                                "classifier-way-all",
                                columns=2,
                            )
                else:
                    st.caption("Выберите чипсы, чтобы увидеть совпадения.")

        with card_cols[1]:
            with st.container(border=True):
                st.markdown("**Матрица**")
                if probable_cells:
                    _render_chip_row(
                        [(cell_id, cell_id) for cell_id in probable_cells],
                        lambda cell_id: go_to_section("matrix", cell_id=cell_id),
                        "classifier-cell",
                        columns=3,
                    )
                else:
                    st.caption("Вероятные ячейки пока не рассчитаны.")

        with card_cols[2]:
            with st.container(border=True):
                st.markdown("**Варианты (конкретика)**")
                matching_variants = []
                if any(selections.values()):
                    for variant in data.variants:
                        score = components.score_variant_against_classifiers(variant, selections)
                        if score is not None:
                            matching_variants.append(score)
                    count = len(matching_variants)
                else:
                    count = len(data.variants)
                st.caption(f"Совпадений: {count}")

                def _open_variants() -> None:
                    components.sync_classifier_filters_from_state()
                    go_to_section("variants")

                st.button(
                    "Показать конкретику",
                    key="classifier-open-variants",
                    on_click=_open_variants,
                    use_container_width=True,
                )

        nav_cols = st.columns(2)

        def _open_bridges() -> None:
            components.sync_classifier_filters_from_state()
            go_to_section("bridges", cell_id=primary_cell)

        def _open_routes() -> None:
            components.sync_classifier_filters_from_state()
            go_to_section("routes", cell_id=primary_cell)

        nav_cols[0].button(
            "Открыть мосты",
            key="classifier-open-bridges",
            on_click=_open_bridges,
            use_container_width=True,
        )
        nav_cols[1].button(
            "Открыть маршруты",
            key="classifier-open-routes",
            on_click=_open_routes,
            use_container_width=True,
        )
    else:
        st.markdown("### Справочник")
        search = st.text_input(
            "Поиск",
            key="classifier_directory_search",
            placeholder="Например: ставка, платформа, риск",
        ).strip()
        group_choice = st.selectbox(
            "Группа",
            ["all", "what_sell", "to_whom", "value_measure"],
            key="classifier_directory_group",
            format_func=lambda value: "Все" if value == "all" else GROUP_CONFIG[value]["label"],
        )

        filtered_items = []
        for item in classifier_items:
            if group_choice != "all" and item["group"] != group_choice:
                continue
            blob = " ".join(
                [
                    item["name"],
                    item["id"],
                    " ".join(item["keywords"]),
                ]
            ).lower()
            if search and search.lower() not in blob:
                continue
            filtered_items.append(item)

        if not filtered_items:
            st.info("Ничего не найдено.")
            return

        for item in filtered_items:
            group_label = GROUP_CONFIG[item["group"]]["label"]
            expander_title = f"{item['name']} · {group_label}"
            with st.expander(expander_title, expanded=False):
                st.markdown(item["short_definition"])
                if item["examples"]:
                    st.markdown("**Примеры:**")
                    for example in item["examples"]:
                        st.markdown(f"- {example}")
                if item["keywords"]:
                    st.caption(f"Ключевые слова: {', '.join(item['keywords'])}")

                def _add_item(item_id: str = item["id"], group: str = item["group"]) -> None:
                    _toggle_classifier(group, item_id)

                st.button(
                    "Добавить в выбор",
                    key=f"classifier-directory-add-{item['group']}-{item['id']}",
                    on_click=_add_item,
                )
