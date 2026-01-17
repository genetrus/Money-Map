from __future__ import annotations

import streamlit as st

from money_map.core.model import AppData
from money_map.ui import components


def render(data: AppData) -> None:
    st.title("Таксономия")
    st.markdown("Выберите механизм дохода слева, чтобы увидеть детали справа.")

    left, right = st.columns([1, 2])

    with left:
        query = st.text_input("Поиск по названию", key="taxonomy_search")
        items = sorted(data.taxonomy, key=lambda item: item.name)
        if query:
            items = [item for item in items if query.lower() in item.name.lower()]
        for item in items:
            if st.button(
                f"{item.name}",
                key=f"taxonomy-item-{item.id}",
                use_container_width=True,
            ):
                components.set_selected_taxonomy(item.id)

    selected_id = st.session_state.get("selected_taxonomy")
    if not selected_id:
        with right:
            st.info("Выберите механизм дохода.")
        return

    item = components.taxonomy_lookup(data).get(selected_id)
    if not item:
        with right:
            st.warning("Механизм не найден.")
        return

    with right:
        st.subheader(item.name)
        st.write(item.description)
        st.markdown("**Продаём:** " + (", ".join(item.sell) or "—"))
        st.markdown("**Кому:** " + (", ".join(item.to_whom) or "—"))
        st.markdown("**Мера ценности:** " + (", ".join(item.value) or "—"))
        st.markdown("**Типовые ячейки:** " + components.format_cells_inline(item.typical_cells))
        st.markdown("**Вне рынка:** " + ("да" if item.outside_market else "нет"))
        st.markdown("**Риск:** " + (item.risk_notes or "—"))
        st.markdown("**Примеры:**")
        for example in item.examples:
            st.write(f"- {example}")

        st.markdown("#### Связанные мосты")
        bridges = components.taxonomy_related_bridges(data, item)
        if not bridges:
            st.caption("Нет связанных мостов.")
        else:
            for bridge in bridges:
                if st.button(
                    f"{bridge.name} ({bridge.from_cell} → {bridge.to_cell})",
                    key=f"tax-bridge-{item.id}-{bridge.id}",
                ):
                    components.set_selected_bridge(bridge.id)
                    components.set_page("Мосты")

        st.markdown("#### Связанные маршруты")
        paths = components.taxonomy_related_paths(data, item)
        if not paths:
            st.caption("Нет связанных маршрутов.")
        else:
            for path in paths:
                if st.button(
                    f"{path.name} ({components.ascii_path(path)})",
                    key=f"tax-path-{item.id}-{path.id}",
                ):
                    components.set_selected_path(path.id)
                    components.set_page("Маршруты")
