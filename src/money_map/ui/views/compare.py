from __future__ import annotations

import streamlit as st

from money_map.core.model import AppData
from money_map.ui import components
from money_map.ui.state import request_nav


TYPE_LABELS = {
    "way": "Способ",
    "route": "Маршрут",
    "bridge": "Мост",
    "variant": "Вариант",
    "cell": "Ячейка",
}


def _open_item(item_type: str, item: dict[str, object]) -> None:
    item_id = item.get("id")
    if not isinstance(item_id, str):
        return
    if item_type == "way":
        request_nav("Способы получения денег", {"way_id": item_id, "tab": "Справочник"})
    elif item_type == "route":
        request_nav("Маршруты", {"route_id": item_id})
    elif item_type == "bridge":
        payload = {"bridge_id": item_id}
        transition = item.get("transition")
        if isinstance(transition, str):
            payload["transition"] = transition
        request_nav("Мосты", payload)
    elif item_type == "variant":
        request_nav("Варианты (конкретика)", {"variant_id": item_id})
    elif item_type == "cell":
        request_nav("Матрица", {"cell_id": item_id})


def render(data: AppData) -> None:
    st.title("Сравнение")

    items = st.session_state.get("compare_items", [])
    if not isinstance(items, list) or not items:
        st.info("Добавьте кандидатов из других разделов, чтобы сравнить.")
        return

    header_cols = st.columns([3, 1])
    header_cols[0].caption(f"Кандидатов: {len(items)}")
    header_cols[1].button(
        "Очистить всё",
        key="compare-clear",
        on_click=components.clear_compare_items,
        use_container_width=True,
    )

    for item in items:
        item_type = str(item.get("type", ""))
        item_id = str(item.get("id", ""))
        name = item.get("name") or item_id
        cell_id = item.get("cell_id") or "—"
        tags = item.get("classifier_tags") or []
        if not isinstance(tags, list):
            tags = []
        tag_lookup = {
            **{key: value.label for key, value in data.mappings.sell_items.items()},
            **{key: value.label for key, value in data.mappings.to_whom_items.items()},
            **{key: value.label for key, value in data.mappings.value_measures.items()},
        }
        tags = [tag_lookup.get(tag, tag) for tag in tags]

        with st.container(border=True):
            title_cols = st.columns([3, 1, 1])
            title_cols[0].markdown(f"**{name}**")
            title_cols[0].caption(TYPE_LABELS.get(item_type, item_type))
            title_cols[1].button(
                "Открыть",
                key=f"compare-open-{item_type}-{item_id}",
                on_click=_open_item,
                args=(item_type, item),
                use_container_width=True,
            )
            title_cols[2].button(
                "Удалить",
                key=f"compare-remove-{item_type}-{item_id}",
                on_click=components.remove_compare_item,
                args=(item_type, item_id),
                use_container_width=True,
            )

            st.caption(f"Связанная ячейка: {cell_id}")
            if tags:
                st.caption("Теги классификатора")
                st.markdown(components.chips(tags))
