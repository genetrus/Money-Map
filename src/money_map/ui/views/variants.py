from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import streamlit as st

from money_map.core.model import AppData
from money_map.ui import components
from money_map.ui.logic.variants_filter import (
    MatchResult,
    NormalizedVariant,
    apply_global_filters,
    data_coverage_score,
    explain_match,
    match_score,
    normalize_variant,
)
from money_map.ui.state import go_to_section


@dataclass(frozen=True)
class SelectionContext:
    selected_matrix_cell: str | None
    selected_transition: str | None
    selected_mechanism_ids: list[str]
    selected_classifiers: dict[str, list[str]]
    selected_route_id: str | None
    selected_route_cells: list[str] | None
    selected_bridge_ids: list[str]
    selected_profile_id: str | None
    selected_subprofile_id: str | None
    selected_work_formats: list[str]
    selected_entry_levels: list[str]
    include_untagged: bool


VARIANT_MODES = ("Подбор", "Библиотека", "Сравнение")


def _apply_nav_payload(data: AppData) -> None:
    payload = components.consume_nav_intent("Варианты (конкретика)")
    if not isinstance(payload, dict):
        return

    way_id = payload.get("way_id")
    cell_id = payload.get("cell_id")
    variant_cell_filter = payload.get("variant_cell_filter")
    bridge_id = payload.get("bridge_id")
    route_id = payload.get("route_id")
    transition = payload.get("transition")
    classifier = payload.get("classifier")
    variant_id = payload.get("variant_id")
    profile_id = payload.get("profile_id")
    subprofile_id = payload.get("subprofile_id")
    work_format_ids = payload.get("work_format_ids")
    entry_level_ids = payload.get("entry_level_ids")

    if isinstance(way_id, str):
        st.session_state["selected_way_id"] = way_id
        st.session_state["selected_tax_id"] = way_id
        st.session_state["ways_selected_way_id"] = way_id
    if isinstance(cell_id, str):
        components.set_selected_cell(cell_id)
    if isinstance(variant_cell_filter, str):
        components.set_selected_cell(variant_cell_filter)
    if isinstance(bridge_id, str):
        st.session_state["selected_bridge_id"] = bridge_id
    if isinstance(route_id, str):
        st.session_state["selected_route_id"] = route_id
        st.session_state["selected_path"] = route_id
    if isinstance(transition, str):
        st.session_state["selected_transition"] = transition
    if classifier is not None:
        components.apply_classifier_filter_request(classifier)
    if isinstance(variant_id, str):
        st.session_state["selected_variant_id"] = variant_id
    if isinstance(profile_id, str):
        st.session_state["variants_profile_id"] = profile_id
    if isinstance(subprofile_id, str):
        st.session_state["variants_subprofile_id"] = subprofile_id
    if isinstance(work_format_ids, list):
        st.session_state["variants_work_formats"] = work_format_ids
    if isinstance(entry_level_ids, list):
        st.session_state["variants_entry_levels"] = entry_level_ids


def _apply_pending_local_requests() -> None:
    request_mode = st.session_state.pop("request_variants_mode", None)
    if isinstance(request_mode, str) and request_mode in VARIANT_MODES:
        st.session_state["variants_mode"] = request_mode


def _selection_context(data: AppData) -> SelectionContext:
    selection = components.sync_selection_context()
    selected_route_id = selection.get("selected_route_id")
    route = next((item for item in data.paths if item.id == selected_route_id), None)
    return SelectionContext(
        selected_matrix_cell=selection.get("selected_matrix_cell"),
        selected_transition=selection.get("selected_transition"),
        selected_mechanism_ids=selection.get("selected_mechanism_ids", []),
        selected_classifiers=selection.get(
            "selected_classifiers",
            {"sell": [], "to_whom": [], "measure": []},
        ),
        selected_route_id=selected_route_id,
        selected_route_cells=route.sequence if route else None,
        selected_bridge_ids=selection.get("selected_bridge_ids", []),
        selected_profile_id=selection.get("selected_profile_id"),
        selected_subprofile_id=selection.get("selected_subprofile_id"),
        selected_work_formats=selection.get("selected_work_formats", []),
        selected_entry_levels=selection.get("selected_entry_levels", []),
        include_untagged=bool(selection.get("include_untagged", True)),
    )


def _label_tags(values: Iterable[str], lookup: dict[str, str]) -> list[str]:
    return [lookup.get(value, value) for value in values]


def _profile_lookup(data: AppData) -> dict[str, str]:
    return {item.id: item.title_ru for item in data.activity_profiles}


def _subprofile_lookup(data: AppData) -> dict[str, str]:
    return {item.id: item.title_ru for item in data.activity_subprofiles}


def _work_format_lookup(data: AppData) -> dict[str, str]:
    return {item.id: item.title_ru for item in data.work_formats}


def _entry_level_lookup(data: AppData) -> dict[str, str]:
    return {item.id: item.title_ru for item in data.entry_levels}


def _render_path_panel(data: AppData, context: SelectionContext) -> None:
    mechanisms = {item.id: item.name for item in data.taxonomy}
    bridges = {item.id: item.name for item in data.bridges}
    routes = {item.id: item.name for item in data.paths}
    classifier_labels = {
        "sell": {key: item.label for key, item in data.mappings.sell_items.items()},
        "to_whom": {key: item.label for key, item in data.mappings.to_whom_items.items()},
        "measure": {key: item.label for key, item in data.mappings.value_measures.items()},
    }

    def _chip_line(label: str, values: Iterable[str]) -> str:
        return f"**{label}:** {components.chips(values) if values else '`не выбрано`'}"

    with st.container(border=True):
        st.markdown("### Панель пути")
        st.markdown(
            _chip_line(
                "Матрица",
                [context.selected_matrix_cell] if context.selected_matrix_cell else [],
            ),
        )

        classifier_lines = []
        if context.selected_classifiers.get("sell"):
            classifier_lines.append(
                _chip_line(
                    "Что продаём",
                    _label_tags(context.selected_classifiers["sell"], classifier_labels["sell"]),
                ),
            )
        if context.selected_classifiers.get("to_whom"):
            classifier_lines.append(
                _chip_line(
                    "Кому",
                    _label_tags(context.selected_classifiers["to_whom"], classifier_labels["to_whom"]),
                ),
            )
        if context.selected_classifiers.get("measure"):
            classifier_lines.append(
                _chip_line(
                    "Как меряется",
                    _label_tags(context.selected_classifiers["measure"], classifier_labels["measure"]),
                ),
            )
        if classifier_lines:
            st.markdown("\n".join(classifier_lines))
        else:
            st.markdown("**Классификаторы:** `не выбрано`")

        mechanism_names = [mechanisms.get(item, item) for item in context.selected_mechanism_ids]
        st.markdown(_chip_line("Способы", mechanism_names))

        if context.selected_route_id:
            st.markdown(_chip_line("Маршрут", [routes.get(context.selected_route_id, context.selected_route_id)]))
        else:
            st.markdown("**Маршрут:** `не выбрано`")

        if context.selected_bridge_ids:
            bridge_labels = [bridges.get(item, item) for item in context.selected_bridge_ids]
            st.markdown(_chip_line("Мосты", bridge_labels))
        else:
            st.markdown("**Мосты:** `не выбрано`")

        profile_labels = _profile_lookup(data)
        subprofile_labels = _subprofile_lookup(data)
        work_format_labels = _work_format_lookup(data)
        entry_level_labels = _entry_level_lookup(data)

        profile_value = (
            [profile_labels.get(context.selected_profile_id, context.selected_profile_id)]
            if context.selected_profile_id
            else []
        )
        st.markdown(_chip_line("Профиль деятельности", profile_value))

        subprofile_value = (
            [subprofile_labels.get(context.selected_subprofile_id, context.selected_subprofile_id)]
            if context.selected_subprofile_id
            else []
        )
        st.markdown(_chip_line("Специализация", subprofile_value))

        st.markdown(
            _chip_line(
                "Формат",
                [work_format_labels.get(item, item) for item in context.selected_work_formats],
            ),
        )
        st.markdown(
            _chip_line(
                "Уровень входа",
                [entry_level_labels.get(item, item) for item in context.selected_entry_levels],
            ),
        )


def _render_shortlist_panel(data: AppData, variants: dict[str, NormalizedVariant]) -> None:
    shortlist = st.session_state.get("shortlist", {})
    with st.container(border=True):
        st.markdown(f"### Шорт-лист ({len(shortlist)})")
        if not shortlist:
            st.caption("Добавьте 1–5 вариантов для сравнения.")
            return
        for variant_id, meta in shortlist.items():
            variant = variants.get(variant_id)
            if not variant:
                continue
            status_key = f"shortlist-status-{variant_id}"
            st.session_state.setdefault(status_key, meta.get("status", "candidate"))

            def _update_status(variant_id: str, key: str) -> None:
                shortlist_local = dict(st.session_state.get("shortlist", {}))
                if variant_id in shortlist_local:
                    shortlist_local[variant_id]["status"] = st.session_state.get(key)
                st.session_state["shortlist"] = shortlist_local

            name_cols = st.columns([3, 1])
            name_cols[0].markdown(f"**{variant.title}**")
            name_cols[1].button(
                "Убрать",
                key=f"shortlist-remove-{variant_id}",
                on_click=_remove_from_shortlist,
                args=(variant_id,),
            )
            st.selectbox(
                "Статус",
                ["candidate", "finalist"],
                key=status_key,
                format_func=lambda value: "Кандидат" if value == "candidate" else "Финалист",
                on_change=_update_status,
                args=(variant_id, status_key),
            )
            st.button(
                "Сравнить",
                key=f"shortlist-compare-{variant_id}",
                on_click=_request_variants_mode,
                args=("Сравнение",),
                use_container_width=True,
            )

        st.button(
            "Перейти в сравнение",
            key="shortlist-to-compare",
            on_click=_request_variants_mode,
            args=("Сравнение",),
            use_container_width=True,
        )


def _add_to_shortlist(variant_id: str) -> None:
    shortlist = dict(st.session_state.get("shortlist", {}))
    if variant_id not in shortlist and len(shortlist) >= 5:
        st.session_state["shortlist_notice"] = "Можно добавить не больше 5 вариантов."
        return
    shortlist.setdefault(variant_id, {"status": "candidate", "note": ""})
    st.session_state["shortlist"] = shortlist


def _remove_from_shortlist(variant_id: str) -> None:
    shortlist = dict(st.session_state.get("shortlist", {}))
    shortlist.pop(variant_id, None)
    st.session_state["shortlist"] = shortlist


def _request_variants_mode(mode: str) -> None:
    st.session_state["request_variants_mode"] = mode


def _ensure_activity_profile_state() -> None:
    st.session_state.setdefault("variants_filter_way_id", "all")
    st.session_state.setdefault("variants_profile_id", None)
    st.session_state.setdefault("variants_subprofile_id", None)
    st.session_state.setdefault("variants_work_formats", [])
    st.session_state.setdefault("variants_entry_levels", [])
    st.session_state.setdefault("variants_include_untagged", True)


def _sync_way_filter() -> None:
    selected = st.session_state.get("variants_filter_way_id", "all")
    if selected == "all":
        st.session_state["selected_way_id"] = None
        st.session_state["selected_tax_id"] = None
        st.session_state["ways_selected_way_id"] = None
    else:
        st.session_state["selected_way_id"] = selected
        st.session_state["selected_tax_id"] = selected
        st.session_state["ways_selected_way_id"] = selected


def _render_activity_profile_filter(data: AppData) -> None:
    _ensure_activity_profile_state()
    profiles_lookup = _profile_lookup(data)
    subprofiles = [item for item in data.activity_subprofiles]
    work_formats = _work_format_lookup(data)
    entry_levels = _entry_level_lookup(data)

    way_options = ["all"] + [item.id for item in data.taxonomy]
    way_label = {item.id: item.name for item in data.taxonomy}
    if st.session_state.get("selected_way_id") in way_label:
        st.session_state["variants_filter_way_id"] = st.session_state.get("selected_way_id")

    with st.container(border=True):
        st.markdown("### Фильтры деятельности")
        st.caption(
            "Последовательно уточняйте профиль, специализацию и условия работы.",
        )
        st.selectbox(
            "Способ получения денег",
            way_options,
            key="variants_filter_way_id",
            format_func=lambda value: "Все" if value == "all" else way_label.get(value, value),
            on_change=_sync_way_filter,
        )

        selected_way = st.session_state.get("variants_filter_way_id")
        if selected_way == "all":
            allowed_profiles = list(profiles_lookup.keys())
        else:
            allowed_profiles = data.money_way_profile_map.get(selected_way, [])

        profile_options = [None, *allowed_profiles]
        st.selectbox(
            "Профиль деятельности",
            profile_options,
            key="variants_profile_id",
            format_func=lambda value: "—" if value is None else profiles_lookup.get(value, value),
        )

        selected_profile = st.session_state.get("variants_profile_id")
        available_subprofiles = [
            item for item in subprofiles if item.parent_profile_id == selected_profile
        ]
        if selected_profile:
            st.selectbox(
                "Специализация (subprofile)",
                [None, *[item.id for item in available_subprofiles]],
                key="variants_subprofile_id",
                format_func=lambda value: "—"
                if value is None
                else _subprofile_lookup(data).get(value, value),
            )
        else:
            st.session_state["variants_subprofile_id"] = None
            st.caption("Выберите профиль, чтобы увидеть специализации.")

        st.multiselect(
            "Формат работы",
            list(work_formats.keys()),
            key="variants_work_formats",
            format_func=lambda value: work_formats.get(value, value),
        )
        st.multiselect(
            "Уровень входа",
            list(entry_levels.keys()),
            key="variants_entry_levels",
            format_func=lambda value: entry_levels.get(value, value),
        )
        st.checkbox(
            "Показывать неразмеченные варианты",
            key="variants_include_untagged",
        )


def _render_variant_card(
    variant: NormalizedVariant,
    *,
    match: MatchResult | None,
    data: AppData,
    label_lookups: dict[str, dict[str, str]],
) -> None:
    mechanisms = {item.id: item.name for item in data.taxonomy}
    bridges = {item.id: item.name for item in data.bridges}
    profile_labels = _profile_lookup(data)
    subprofile_labels = _subprofile_lookup(data)
    work_format_labels = _work_format_lookup(data)
    entry_level_labels = _entry_level_lookup(data)

    header_cols = st.columns([4, 2])
    with header_cols[0]:
        st.markdown(f"**{variant.title}**")
        st.caption(variant.kind)
    with header_cols[1]:
        in_shortlist = variant.id in st.session_state.get("shortlist", {})
        if in_shortlist:
            st.button(
                "Удалить",
                key=f"variant-remove-{variant.id}",
                on_click=_remove_from_shortlist,
                args=(variant.id,),
                use_container_width=True,
            )
        else:
            st.button(
                "⭐ В шорт-лист",
                key=f"variant-shortlist-{variant.id}",
                on_click=_add_to_shortlist,
                args=(variant.id,),
                use_container_width=True,
            )
        if st.session_state.get("nav_mode") == "Сравнение":
            if st.button(
                "+ В сравнение",
                key=f"variant-compare-{variant.id}",
                use_container_width=True,
            ):
                components.add_compare_item(
                    {
                        "type": "variant",
                        "id": variant.id,
                        "name": variant.title,
                        "cell_id": variant.matrix_cell,
                        "classifier_tags": [
                            *variant.classifiers.get("sell", []),
                            *variant.classifiers.get("to_whom", []),
                            *variant.classifiers.get("measure", []),
                        ],
                    },
                )
        if st.session_state.get("nav_mode") == "Конструктор пути":
            if st.button(
                "Сохранить выбор",
                key=f"variant-select-{variant.id}",
                use_container_width=True,
            ):
                st.session_state["selected_variant_id"] = variant.id

    st.markdown(
        f"**Способ:** {mechanisms.get(variant.mechanism_id, variant.mechanism_id)}"
        f" · **Матрица:** {variant.matrix_cell or '—'}",
    )
    profile_label = profile_labels.get(variant.profile_id, "Неразмечено")
    st.markdown(f"**Профиль:** {profile_label}")
    badges = []
    if variant.subprofile_id:
        badges.append(subprofile_labels.get(variant.subprofile_id, variant.subprofile_id))
    if variant.work_format_ids:
        badges.extend([work_format_labels.get(item, item) for item in variant.work_format_ids])
    if variant.entry_level_ids:
        badges.extend([entry_level_labels.get(item, item) for item in variant.entry_level_ids])
    if badges:
        st.caption(" ".join(f"`{item}`" for item in badges))

    tag_cols = st.columns(3)
    with tag_cols[0]:
        st.caption("Что продаёшь")
        st.markdown(components.chips(_label_tags(variant.classifiers["sell"], label_lookups["sell"])))
    with tag_cols[1]:
        st.caption("Кому")
        st.markdown(components.chips(_label_tags(variant.classifiers["to_whom"], label_lookups["to_whom"])))
    with tag_cols[2]:
        st.caption("Как меряется")
        st.markdown(components.chips(_label_tags(variant.classifiers["measure"], label_lookups["measure"])))

    st.markdown(f"**На практике:** {variant.summary}")

    if match:
        reasons = explain_match(match)
        st.caption("Почему здесь: " + ", ".join(reasons))
        with st.expander("Debug"):
            st.markdown(f"- match_score: {match.score:.1f}")
            st.markdown(f"- заполненность: {match.data_coverage}/5")
            st.markdown(
                f"- классификаторы: {match.classifier_match_count}/{match.classifier_group_count}",
            )

    if variant.linked_bridges:
        bridge_labels = [bridges.get(item, item) for item in variant.linked_bridges]
        st.markdown(f"**Мосты:** {components.chips(bridge_labels)}")

    jump_cols = st.columns([1, 1, 1, 1])
    jump_cols[0].button(
        "Способ",
        key=f"variant-jump-way-{variant.id}",
        on_click=go_to_section,
        args=("Способы получения денег",),
        kwargs={"way_id": variant.mechanism_id, "tab": "Справочник"},
        use_container_width=True,
    )
    if variant.matrix_cell:
        jump_cols[1].button(
            "Матрица",
            key=f"variant-jump-cell-{variant.id}",
            on_click=go_to_section,
            args=("Матрица",),
            kwargs={"cell_id": variant.matrix_cell},
            use_container_width=True,
        )
    else:
        jump_cols[1].button("Матрица", key=f"variant-jump-cell-disabled-{variant.id}", disabled=True)
    if variant.linked_bridges:
        jump_cols[2].button(
            "Мосты",
            key=f"variant-jump-bridge-{variant.id}",
            on_click=go_to_section,
            args=("Мосты",),
            kwargs={"bridge_id": variant.linked_bridges[0]},
            use_container_width=True,
        )
    else:
        jump_cols[2].button("Мосты", key=f"variant-jump-bridge-disabled-{variant.id}", disabled=True)
    if variant.linked_route:
        jump_cols[3].button(
            "Маршрут",
            key=f"variant-jump-route-{variant.id}",
            on_click=go_to_section,
            args=("Маршруты",),
            kwargs={"route_id": variant.linked_route},
            use_container_width=True,
        )
    else:
        jump_cols[3].button("Маршрут", key=f"variant-jump-route-disabled-{variant.id}", disabled=True)

    expanded = st.session_state.get("selected_variant_id") == variant.id
    with st.expander("🔎 Детали", expanded=expanded):
        st.markdown("**Суть**")
        st.write(variant.description)
        st.markdown("**Как выглядит на практике**")
        st.write(variant.summary)
        st.markdown("**Почему подходит под текущий выбор**")
        if match:
            for reason in match.reasons:
                st.markdown(f"- {reason}")
        else:
            st.markdown("- Совпадает по общему профилю фильтров.")
        st.markdown("**Связи**")
        st.markdown(
            f"- Способ: {mechanisms.get(variant.mechanism_id, variant.mechanism_id)}",
        )
        st.markdown(f"- Профиль: {profile_labels.get(variant.profile_id, 'Неразмечено')}")
        if variant.subprofile_id:
            st.markdown(
                f"- Специализация: {subprofile_labels.get(variant.subprofile_id, variant.subprofile_id)}",
            )
        if variant.work_format_ids:
            st.markdown(
                f"- Формат: {', '.join(work_format_labels.get(item, item) for item in variant.work_format_ids)}",
            )
        if variant.entry_level_ids:
            st.markdown(
                f"- Уровень входа: {', '.join(entry_level_labels.get(item, item) for item in variant.entry_level_ids)}",
            )
        if variant.matrix_cell:
            st.markdown(f"- Матрица: {variant.matrix_cell}")
        if variant.linked_bridges:
            bridge_labels = [bridges.get(item, item) for item in variant.linked_bridges]
            st.markdown(f"- Мосты: {', '.join(bridge_labels)}")
        if variant.linked_route:
            st.markdown(f"- Маршрут: {variant.linked_route}")
        st.markdown("**Пакет выбора**")
        if variant.hints_fit:
            st.markdown("Подходит если:")
            for hint in variant.hints_fit:
                st.markdown(f"- {hint}")
        else:
            st.caption("Нет данных по условиям, когда подходит.")
        if variant.hints_not_fit:
            st.markdown("Не подходит если:")
            for hint in variant.hints_not_fit:
                st.markdown(f"- {hint}")
        else:
            st.caption("Нет данных по условиям, когда не подходит.")
        st.markdown("**Первые шаги**")
        if variant.first_steps:
            for step in variant.first_steps:
                st.markdown(f"- {step}")
        else:
            st.caption("Нет данных.")
        st.markdown("**Типовые ошибки**")
        if variant.common_mistakes:
            for item in variant.common_mistakes:
                st.markdown(f"- {item}")
        else:
            st.caption("Нет данных.")


def _render_comparison(
    data: AppData,
    normalized_variants: dict[str, NormalizedVariant],
    matches: dict[str, MatchResult],
) -> None:
    shortlist = st.session_state.get("shortlist", {})
    if len(shortlist) < 2:
        st.info("Добавьте минимум два варианта для сравнения.")
        return

    selected_variants = [
        normalized_variants[variant_id]
        for variant_id in shortlist.keys()
        if variant_id in normalized_variants
    ]
    if len(selected_variants) > 5:
        selected_variants = selected_variants[:5]

    mechanisms = {item.id: item.name for item in data.taxonomy}
    bridges = {item.id: item.name for item in data.bridges}
    profile_labels = _profile_lookup(data)
    subprofile_labels = _subprofile_lookup(data)

    rows = []
    for variant in selected_variants:
        match = matches.get(variant.id)
        reasons = explain_match(match) if match else ["Совпадает по общему профилю."]
        rows.append(
            {
                "Вариант": variant.title,
                "Способ": mechanisms.get(variant.mechanism_id, variant.mechanism_id),
                "Матрица": variant.matrix_cell or "—",
                "Классификаторы": ", ".join(
                    [
                        *variant.classifiers.get("sell", []),
                        *variant.classifiers.get("to_whom", []),
                        *variant.classifiers.get("measure", []),
                    ],
                ),
                "Профиль": profile_labels.get(variant.profile_id, "Неразмечено"),
                "Специализация": subprofile_labels.get(variant.subprofile_id, "—")
                if variant.subprofile_id
                else "—",
                "Маршрут": variant.linked_route or "—",
                "Мосты": ", ".join([bridges.get(item, item) for item in variant.linked_bridges]) or "—",
                "Краткая суть": variant.summary,
                "Почему подходит": "; ".join(reasons),
            },
        )

    st.dataframe(rows, use_container_width=True)

    for variant in selected_variants:
        st.button(
            f"Убрать {variant.title}",
            key=f"compare-remove-{variant.id}",
            on_click=_remove_from_shortlist,
            args=(variant.id,),
        )


def render(data: AppData, filters: components.Filters) -> None:
    _apply_nav_payload(data)
    _apply_pending_local_requests()

    st.title("Варианты (конкретика)")
    st.markdown(
        "Финальная точка, где абстракции превращаются в конкретные профессии, "
        "проекты, форматы сделок и виды бизнеса.",
    )
    components.render_path_wizard("Варианты")

    _ensure_activity_profile_state()
    context = _selection_context(data)
    _render_path_panel(data, context)

    _render_activity_profile_filter(data)

    if st.session_state.get("nav_mode") == "Конструктор пути":
        if st.button(
            "Добавить в кандидаты",
            key="variants-save-candidate",
            use_container_width=True,
            disabled=not bool(st.session_state.get("selected_variant_id")),
        ):
            st.session_state["compare_selected_id"] = st.session_state.get("selected_variant_id")

    mode_cols = st.columns([3, 2, 3])
    with mode_cols[0]:
        st.radio(
            "Режим",
            VARIANT_MODES,
            key="variants_mode",
            horizontal=True,
        )
    with mode_cols[1]:
        st.radio(
            "Совпадение",
            ["strict", "wide"],
            key="variants_scope",
            format_func=lambda value: "Строго" if value == "strict" else "Мягко",
            horizontal=True,
        )
    with mode_cols[2]:
        st.caption("Строго = полное совпадение, Мягко = частичные совпадения с ранжированием.")

    normalized = [normalize_variant(variant) for variant in data.variants]
    filtered_global = apply_global_filters(
        normalized,
        risk=filters.risk,
        activity=filters.activity,
        scalability=filters.scalability,
    )

    label_lookups = {
        "sell": {key: item.label for key, item in data.mappings.sell_items.items()},
        "to_whom": {key: item.label for key, item in data.mappings.to_whom_items.items()},
        "measure": {key: item.label for key, item in data.mappings.value_measures.items()},
    }

    scope = st.session_state.get("variants_scope", "strict")
    strict = scope == "strict"

    matches: list[MatchResult] = []
    match_lookup: dict[str, MatchResult] = {}
    for variant in filtered_global:
        result = match_score(
            variant,
            selected_mechanism_ids=context.selected_mechanism_ids,
            selected_matrix_cell=context.selected_matrix_cell,
            selected_classifiers=context.selected_classifiers,
            selected_route_cells=context.selected_route_cells,
            selected_bridge_ids=context.selected_bridge_ids,
            selected_profile_id=context.selected_profile_id,
            selected_subprofile_id=context.selected_subprofile_id,
            selected_work_formats=context.selected_work_formats,
            selected_entry_levels=context.selected_entry_levels,
            include_untagged=context.include_untagged,
            strict=strict,
        )
        if result is not None:
            matches.append(result)
            match_lookup[variant.id] = result

    total_after_global = len(filtered_global)
    hidden_count = max(total_after_global - len(matches), 0)

    current_mode = st.session_state.get("variants_mode", "Подбор")
    if current_mode == "Подбор":
        matches.sort(
            key=lambda item: (-item.score, -item.data_coverage, item.variant.title),
        )
        header = st.columns([3, 1])
        header[0].markdown(f"**Найдено вариантов:** {len(matches)}")
        if hidden_count:
            header[1].caption(f"Скрыто фильтрами: {hidden_count}")

        if strict and context.selected_profile_id and not matches:
            st.warning(
                "По выбранному профилю нет вариантов. Переключитесь на 'Шире' или выберите другой профиль.",
            )

        if not context.selected_profile_id and len(matches) > 40:
            st.info("Слишком много вариантов. Выберите профиль деятельности, чтобы сузить список.")

        if st.session_state.pop("shortlist_notice", None):
            st.warning("Можно добавить не больше 5 вариантов.")

        list_col, shortlist_col = st.columns([3, 1])
        with list_col:
            if not matches:
                st.info("Нет подходящих вариантов по текущему выбору.")
            top_matches = matches[:15]
            rest_matches = matches[15:]
            if top_matches:
                st.markdown("#### Топ-15")
            for match in top_matches:
                with st.container(border=True):
                    _render_variant_card(
                        match.variant,
                        match=match,
                        data=data,
                        label_lookups=label_lookups,
                    )
            if rest_matches:
                with st.expander(f"Остальные варианты ({len(rest_matches)})", expanded=False):
                    for match in rest_matches:
                        with st.container(border=True):
                            _render_variant_card(
                                match.variant,
                                match=match,
                                data=data,
                                label_lookups=label_lookups,
                            )
        with shortlist_col:
            variants_lookup = {item.id: item for item in normalized}
            _render_shortlist_panel(data, variants_lookup)

    elif current_mode == "Библиотека":
        catalog_col, shortlist_col = st.columns([3, 1])
        with catalog_col:
            search_term = st.text_input(
                "Поиск по названию или описанию",
                key="variants_library_search",
            )
            filter_cols = st.columns(3)
            mechanisms = {item.id: item.name for item in data.taxonomy}
            mechanism_options = ["all"] + sorted(mechanisms.keys())
            kind_options = ["all"] + sorted({variant.kind for variant in normalized})
            cell_options = ["all"] + sorted({cell.id for cell in data.cells})
            filter_cols[0].selectbox(
                "Способ",
                mechanism_options,
                key="variants_library_mechanism",
                format_func=lambda value: "Все" if value == "all" else mechanisms.get(value, value),
            )
            filter_cols[1].selectbox(
                "Тип",
                kind_options,
                key="variants_library_kind",
                format_func=lambda value: "Все" if value == "all" else value,
            )
            filter_cols[2].selectbox(
                "Ячейка",
                cell_options,
                key="variants_library_cell",
                format_func=lambda value: "Все" if value == "all" else value,
            )

            filtered = list(filtered_global)
            mechanism_filter = st.session_state.get("variants_library_mechanism", "all")
            kind_filter = st.session_state.get("variants_library_kind", "all")
            cell_filter = st.session_state.get("variants_library_cell", "all")
            if mechanism_filter != "all":
                filtered = [item for item in filtered if item.mechanism_id == mechanism_filter]
            if kind_filter != "all":
                filtered = [item for item in filtered if item.kind == kind_filter]
            if cell_filter != "all":
                filtered = [item for item in filtered if cell_filter in item.matrix_cells]
            if search_term:
                search = search_term.lower()
                filtered = [
                    item
                    for item in filtered
                    if search in item.title.lower() or search in item.summary.lower()
                ]

            sort_choice = st.selectbox(
                "Сортировка",
                ["title", "coverage"],
                key="variants_library_sort",
                format_func=lambda value: "По названию" if value == "title" else "По заполненности",
            )
            if sort_choice == "coverage":
                filtered.sort(key=lambda item: (-data_coverage_score(item), item.title))
            else:
                filtered.sort(key=lambda item: item.title)

            st.markdown(f"**Всего в библиотеке:** {len(filtered)}")
            for variant in filtered:
                with st.container(border=True):
                    _render_variant_card(
                        variant,
                        match=match_lookup.get(variant.id),
                        data=data,
                        label_lookups=label_lookups,
                    )
        with shortlist_col:
            variants_lookup = {item.id: item for item in normalized}
            _render_shortlist_panel(data, variants_lookup)

    else:
        variants_lookup = {item.id: item for item in normalized}
        _render_comparison(data, variants_lookup, match_lookup)
