from __future__ import annotations

import time

import streamlit as st
from st_cytoscape import cytoscape

from money_map.core.graph_model import GraphEdge, GraphModel, GraphNode, build_base_graph
from money_map.core.model import AppData
from money_map.ui import components
from money_map.ui.state import go_to_section

NODE_TYPES = ["way", "classifier", "cell", "bridge", "route", "variant"]
EDGE_TYPES = [
    "has_classifier",
    "maps_to_cell",
    "transition",
    "bridge_for_transition",
    "route_contains",
    "route_uses_bridge",
    "variant_of_way",
    "variant_fits_cell",
    "variant_uses_bridge",
]


def ensure_graph_state_defaults() -> None:
    st.session_state.setdefault("graph_tab", "Обзор")
    st.session_state.setdefault("graph_selected_node_id", None)
    st.session_state.setdefault("graph_selected_edge_id", None)
    st.session_state.setdefault("graph_last_click_node_id", None)
    st.session_state.setdefault("graph_last_click_ts", 0.0)
    st.session_state.setdefault("graph_depth", 1)
    st.session_state.setdefault("graph_max_nodes", 60)
    st.session_state.setdefault("graph_node_type_filters", {})
    st.session_state.setdefault("graph_edge_type_filters", {})
    st.session_state.setdefault("graph_layout_name", "fcose")
    st.session_state.setdefault("graph_expand_depth_override", False)
    st.session_state.setdefault("graph_search_query", "")
    st.session_state.setdefault("graph_search_selected_id", None)
    st.session_state.setdefault("graph_path_route_id", None)
    st.session_state.setdefault("graph_path_show_related", False)

    if not st.session_state["graph_node_type_filters"]:
        st.session_state["graph_node_type_filters"] = {node_type: True for node_type in NODE_TYPES}
    if not st.session_state["graph_edge_type_filters"]:
        st.session_state["graph_edge_type_filters"] = {edge_type: True for edge_type in EDGE_TYPES}

    for node_type in NODE_TYPES:
        key = f"graph_node_filter_{node_type}"
        st.session_state.setdefault(key, st.session_state["graph_node_type_filters"].get(node_type, True))
    for edge_type in EDGE_TYPES:
        key = f"graph_edge_filter_{edge_type}"
        st.session_state.setdefault(key, st.session_state["graph_edge_type_filters"].get(edge_type, True))


def _sync_node_filters() -> None:
    st.session_state["graph_node_type_filters"] = {
        node_type: bool(st.session_state.get(f"graph_node_filter_{node_type}", False))
        for node_type in NODE_TYPES
    }


def _sync_edge_filters() -> None:
    st.session_state["graph_edge_type_filters"] = {
        edge_type: bool(st.session_state.get(f"graph_edge_filter_{edge_type}", False))
        for edge_type in EDGE_TYPES
    }


def _get_graph_model(data: AppData) -> GraphModel:
    return build_base_graph(data)


def _extract_selected_ids(selected: object) -> tuple[str | None, str | None]:
    if not isinstance(selected, dict):
        return None, None

    def _extract_node_id(payload: object) -> str | None:
        if isinstance(payload, str):
            return payload or None
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, dict):
                node_id = data.get("id")
                return node_id if isinstance(node_id, str) else None
            node_id = payload.get("id")
            return node_id if isinstance(node_id, str) else None
        return None

    node_id = None
    edge_id = None

    for key in ("nodes", "selectedNodes", "selected_nodes"):
        payload = selected.get(key)
        if isinstance(payload, list) and payload:
            node_id = _extract_node_id(payload[0])
            break
        if isinstance(payload, dict):
            node_id = _extract_node_id(payload)
            break

    for key in ("edges", "selectedEdges", "selected_edges"):
        payload = selected.get(key)
        if isinstance(payload, list) and payload:
            edge_id = _extract_node_id(payload[0])
            break
        if isinstance(payload, dict):
            edge_id = _extract_node_id(payload)
            break

    return node_id, edge_id


def _make_node_element(node: GraphNode, selected: bool = False) -> dict[str, object]:
    classes = [node.type]
    if node.type == "classifier":
        group = node.meta.get("group")
        if isinstance(group, str):
            classes.append(group)
    return {
        "data": {"id": node.id, "label": node.label, "type": node.type},
        "classes": " ".join(classes),
        "selected": selected,
    }


def _make_edge_element(edge: GraphEdge, highlighted: bool = False, selected: bool = False) -> dict[str, object]:
    classes = [edge.type]
    if highlighted:
        classes.append("highlight")
    return {
        "data": {
            "id": edge.id,
            "source": edge.source,
            "target": edge.target,
            "label": edge.label,
            "type": edge.type,
        },
        "classes": " ".join(classes),
        "selected": selected,
    }


def _build_subgraph(
    model: GraphModel,
    selected_id: str,
    node_type_filters: dict[str, bool],
    edge_type_filters: dict[str, bool],
    depth: int,
    max_nodes: int,
) -> tuple[list[dict[str, object]], set[str], set[str]]:
    if selected_id not in model.nodes_by_id:
        return [], set(), set()

    allowed_node_types = {node for node, allowed in node_type_filters.items() if allowed}
    allowed_edge_types = {edge for edge, allowed in edge_type_filters.items() if allowed}

    visited: set[str] = set()
    queue: list[tuple[str, int]] = [(selected_id, 0)]

    while queue:
        node_id, dist = queue.pop(0)
        if node_id in visited:
            continue
        node = model.nodes_by_id.get(node_id)
        if not node or node.type not in allowed_node_types:
            continue
        visited.add(node_id)
        if dist >= depth:
            continue
        for edge_id in model.incident_edges.get(node_id, set()):
            edge = model.edges_by_id[edge_id]
            if edge.type not in allowed_edge_types:
                continue
            neighbor = edge.target if edge.source == node_id else edge.source
            if neighbor not in visited:
                queue.append((neighbor, dist + 1))

    if not visited:
        visited.add(selected_id)

    if len(visited) > max_nodes:
        first_neighbors = {
            neighbor
            for edge_id in model.incident_edges.get(selected_id, set())
            if model.edges_by_id[edge_id].type in allowed_edge_types
            for neighbor in (
                model.edges_by_id[edge_id].target
                if model.edges_by_id[edge_id].source == selected_id
                else model.edges_by_id[edge_id].source,
            )
            if model.nodes_by_id.get(neighbor) and model.nodes_by_id[neighbor].type in allowed_node_types
        }
        prioritized = {selected_id} | first_neighbors
        if len(prioritized) > max_nodes:
            ranked = sorted(
                first_neighbors,
                key=lambda node_id: len(model.adjacency.get(node_id, set())),
                reverse=True,
            )
            visited = {selected_id} | set(ranked[: max_nodes - 1])
        else:
            remaining = list(visited - prioritized)
            ranked = sorted(
                remaining,
                key=lambda node_id: len(model.adjacency.get(node_id, set())),
                reverse=True,
            )
            visited = set(list(prioritized) + ranked[: max_nodes - len(prioritized)])

    highlight_edges = {
        edge_id
        for edge_id in model.incident_edges.get(selected_id, set())
        if model.edges_by_id[edge_id].type in allowed_edge_types
    }

    nodes = [
        _make_node_element(model.nodes_by_id[node_id], selected=(node_id == selected_id))
        for node_id in visited
    ]
    edges = [
        _make_edge_element(
            edge,
            highlighted=edge.id in highlight_edges,
            selected=edge.id == st.session_state.get("graph_selected_edge_id"),
        )
        for edge in model.edges
        if edge.source in visited
        and edge.target in visited
        and edge.type in allowed_edge_types
    ]

    return nodes + edges, visited, highlight_edges


def _stylesheet() -> list[dict[str, object]]:
    return [
        {
            "selector": "node",
            "style": {
                "label": "data(label)",
                "font-size": 10,
                "text-wrap": "wrap",
                "text-max-width": 80,
                "text-valign": "center",
                "text-halign": "center",
            },
        },
        {"selector": ".way", "style": {"background-color": "#2563EB", "color": "#ffffff"}},
        {"selector": ".classifier", "style": {"background-color": "#F59E0B", "color": "#111827"}},
        {"selector": ".what_sell", "style": {"background-color": "#FBBF24"}},
        {"selector": ".to_whom", "style": {"background-color": "#34D399"}},
        {"selector": ".value_measure", "style": {"background-color": "#A78BFA"}},
        {"selector": ".cell", "style": {"background-color": "#E5E7EB", "color": "#111827"}},
        {"selector": ".bridge", "style": {"background-color": "#F97316", "color": "#111827"}},
        {"selector": ".route", "style": {"background-color": "#14B8A6", "color": "#0f172a"}},
        {"selector": ".variant", "style": {"background-color": "#FDE68A", "color": "#111827"}},
        {
            "selector": "edge",
            "style": {
                "curve-style": "bezier",
                "target-arrow-shape": "triangle",
                "line-color": "#9CA3AF",
                "target-arrow-color": "#9CA3AF",
                "font-size": 8,
                "label": "data(label)",
                "text-rotation": "autorotate",
            },
        },
        {
            "selector": ".highlight",
            "style": {
                "line-color": "#16A34A",
                "target-arrow-color": "#16A34A",
                "width": 4,
            },
        },
    ]


def _legend() -> None:
    st.markdown(
        """
        **Легенда:**
        - 🟦 Способы
        - 🟨 Классификаторы
        - ⬜ Ячейки
        - 🟧 Мосты
        - 🟩 Маршруты
        - 🟨 Варианты
        """,
    )


def _render_node_details(node: GraphNode) -> None:
    st.markdown(f"### {node.label}")
    st.caption(f"Тип: {node.type}")
    if node.type == "way":
        st.button(
            "Открыть в разделе «Способы»",
            key=f"graph-open-way-{node.id}",
            on_click=go_to_section,
            kwargs={"section_name": "ways", "way_id": node.meta.get("way_id"), "open_tab": "directory"},
        )
    elif node.type == "classifier":
        classifier_request = {
            "group": node.meta.get("group"),
            "id": node.meta.get("classifier_id"),
        }
        st.button(
            "Открыть в классификаторе",
            key=f"graph-open-classifier-{node.id}",
            on_click=go_to_section,
            kwargs={"section_name": "classifier", "open_tab": "panel", "classifier": classifier_request},
        )
    elif node.type == "cell":
        cell_id = node.meta.get("cell_id")
        st.button(
            "Открыть в матрице",
            key=f"graph-open-cell-{node.id}",
            on_click=go_to_section,
            kwargs={"section_name": "matrix", "cell_id": cell_id},
        )
    elif node.type == "bridge":
        bridge_id = node.meta.get("bridge_id")
        st.button(
            "Открыть мост",
            key=f"graph-open-bridge-{node.id}",
            on_click=go_to_section,
            kwargs={"section_name": "bridges", "bridge_id": bridge_id},
        )
    elif node.type == "route":
        route_id = node.meta.get("route_id")
        st.button(
            "Открыть маршрут",
            key=f"graph-open-route-{node.id}",
            on_click=go_to_section,
            kwargs={"section_name": "routes", "route_id": route_id},
        )
    elif node.type == "variant":
        variant_id = node.meta.get("variant_id")
        st.button(
            "Открыть вариант",
            key=f"graph-open-variant-{node.id}",
            on_click=go_to_section,
            kwargs={"section_name": "variants", "variant_id": variant_id},
        )


def _render_edge_details(edge: GraphEdge) -> None:
    st.markdown(f"### {edge.label}")
    st.caption(f"Тип ребра: {edge.type}")
    st.write(f"{edge.source} → {edge.target}")


def _build_route_elements(
    data: AppData,
    route_id: str,
    show_related: bool,
) -> list[dict[str, object]]:
    path = next((item for item in data.paths if item.id == route_id), None)
    if not path:
        return []

    elements: list[dict[str, object]] = []
    cell_lookup = components.cell_lookup(data)
    for cell_id in path.sequence:
        cell = cell_lookup.get(cell_id)
        label = f"{cell_id} {cell.label}" if cell else cell_id
        elements.append(
            {
                "data": {"id": f"cell:{cell_id}", "label": label, "type": "cell"},
                "classes": "cell",
            }
        )

    transition_ids = []
    for idx in range(len(path.sequence) - 1):
        from_cell = path.sequence[idx]
        to_cell = path.sequence[idx + 1]
        edge_id = f"transition:{from_cell}->{to_cell}"
        transition_ids.append(edge_id)
        elements.append(
            {
                "data": {
                    "id": edge_id,
                    "source": f"cell:{from_cell}",
                    "target": f"cell:{to_cell}",
                    "label": f"{from_cell} → {to_cell}",
                    "type": "transition",
                },
                "classes": "transition",
            }
        )

    bridges_by_transition: dict[str, list[str]] = {}
    for bridge in data.bridges:
        transition = f"{bridge.from_cell}->{bridge.to_cell}"
        bridges_by_transition.setdefault(transition, []).append(bridge.id)

    for transition in transition_ids:
        transition_key = transition.removeprefix("transition:")
        for bridge_id in bridges_by_transition.get(transition_key, []):
            bridge = next((item for item in data.bridges if item.id == bridge_id), None)
            if not bridge:
                continue
            elements.append(
                {
                    "data": {
                        "id": f"bridge:{bridge_id}",
                        "label": bridge.name,
                        "type": "bridge",
                    },
                    "classes": "bridge",
                }
            )
            elements.append(
                {
                    "data": {
                        "id": f"bridge_for_transition:{bridge_id}:{bridge.from_cell}",
                        "source": f"bridge:{bridge_id}",
                        "target": f"cell:{bridge.from_cell}",
                        "label": "из",
                        "type": "bridge_for_transition",
                    },
                    "classes": "bridge_for_transition",
                }
            )
            elements.append(
                {
                    "data": {
                        "id": f"bridge_for_transition:{bridge_id}:{bridge.to_cell}",
                        "source": f"bridge:{bridge_id}",
                        "target": f"cell:{bridge.to_cell}",
                        "label": "в",
                        "type": "bridge_for_transition",
                    },
                    "classes": "bridge_for_transition",
                }
            )

    if show_related:
        way_lookup = components.taxonomy_lookup(data)
        linked_way_ids = {
            way_id
            for bridge in data.bridges
            for way_id in bridge.linked_way_ids
            if any(
                bridge.from_cell == cell_id or bridge.to_cell == cell_id
                for cell_id in path.sequence
            )
        }
        for way_id in linked_way_ids:
            way = way_lookup.get(way_id)
            if not way:
                continue
            elements.append(
                {
                    "data": {"id": f"way:{way_id}", "label": way.name, "type": "way"},
                    "classes": "way",
                }
            )
            for cell_id in way.typical_cells:
                if cell_id not in path.sequence:
                    continue
                elements.append(
                    {
                        "data": {
                            "id": f"maps_to_cell:{way_id}:{cell_id}",
                            "source": f"way:{way_id}",
                            "target": f"cell:{cell_id}",
                            "label": "типичная ячейка",
                            "type": "maps_to_cell",
                        },
                        "classes": "maps_to_cell",
                    }
                )

        for variant in data.variants:
            if variant.primary_way_id not in linked_way_ids:
                continue
            elements.append(
                {
                    "data": {
                        "id": f"variant:{variant.id}",
                        "label": variant.title,
                        "type": "variant",
                    },
                    "classes": "variant",
                }
            )
            elements.append(
                {
                    "data": {
                        "id": f"variant_of_way:{variant.id}:{variant.primary_way_id}",
                        "source": f"variant:{variant.id}",
                        "target": f"way:{variant.primary_way_id}",
                        "label": "вариант",
                        "type": "variant_of_way",
                    },
                    "classes": "variant_of_way",
                }
            )

    return elements


def _overview_elements(data: AppData) -> list[dict[str, object]]:
    overview_nodes = [
        ("overview:ways", f"Способы ({len(data.taxonomy)})", "way"),
        ("overview:classifiers", "Классификаторы (3 группы)", "classifier"),
        ("overview:cells", f"Ячейки ({len(data.cells)})", "cell"),
        ("overview:bridges", f"Мосты ({len(data.bridges)})", "bridge"),
        ("overview:routes", f"Маршруты ({len(data.paths)})", "route"),
        ("overview:variants", f"Варианты ({len(data.variants)})", "variant"),
    ]
    elements: list[dict[str, object]] = []
    for node_id, label, node_type in overview_nodes:
        elements.append(
            {
                "data": {"id": node_id, "label": label, "type": node_type},
                "classes": node_type,
            }
        )
    edges = [
        ("overview:ways", "overview:classifiers", "связано"),
        ("overview:ways", "overview:cells", "типичные ячейки"),
        ("overview:cells", "overview:bridges", "мосты"),
        ("overview:bridges", "overview:routes", "маршруты"),
        ("overview:routes", "overview:variants", "варианты"),
        ("overview:variants", "overview:ways", "возврат"),
    ]
    for idx, (source, target, label) in enumerate(edges):
        elements.append(
            {
                "data": {
                    "id": f"overview-edge-{idx}",
                    "source": source,
                    "target": target,
                    "label": label,
                    "type": "overview",
                },
                "classes": "transition",
            }
        )
    return elements


def _overview_click_target(data: AppData, overview_id: str) -> str | None:
    if overview_id == "overview:ways" and data.taxonomy:
        return f"way:{data.taxonomy[0].id}"
    if overview_id == "overview:classifiers":
        first = next(iter(data.mappings.sell_items.keys()), None)
        if first:
            return f"classifier:what_sell.{first}"
    if overview_id == "overview:cells" and data.cells:
        return f"cell:{data.cells[0].id}"
    if overview_id == "overview:bridges" and data.bridges:
        return f"bridge:{data.bridges[0].id}"
    if overview_id == "overview:routes" and data.paths:
        return f"route:{data.paths[0].id}"
    if overview_id == "overview:variants" and data.variants:
        return f"variant:{data.variants[0].id}"
    return None


def render_overview_tab(data: AppData) -> None:
    st.subheader("Обзор")
    st.markdown("Кликните тип, чтобы перейти к исследованию связей.")
    _legend()
    elements = _overview_elements(data)
    selected = cytoscape(
        elements,
        _stylesheet(),
        layout={"name": "circle"},
        height="420px",
        selection_type="single",
    )
    node_id, _ = _extract_selected_ids(selected)
    if node_id and node_id.startswith("overview:"):
        target = _overview_click_target(data, node_id)
        if target:
            st.session_state["graph_selected_node_id"] = target
            st.session_state["graph_tab"] = "Исследование"
            st.rerun()


def render_explore_tab(data: AppData, filters: components.Filters) -> None:
    st.subheader("Исследование")

    model = _get_graph_model(data)
    selected_node_id = st.session_state.get("graph_selected_node_id")

    if not selected_node_id:
        if st.session_state.get("selected_way_id"):
            selected_node_id = f"way:{st.session_state['selected_way_id']}"
        elif st.session_state.get("selected_cell_id"):
            selected_node_id = f"cell:{st.session_state['selected_cell_id']}"
        elif data.taxonomy:
            selected_node_id = f"way:{data.taxonomy[0].id}"
        st.session_state["graph_selected_node_id"] = selected_node_id

    left_col, center_col, right_col = st.columns([1.2, 2.4, 1.2])

    with left_col:
        st.markdown("#### Поиск")
        st.text_input("Запрос", key="graph_search_query")

        query = st.session_state.get("graph_search_query", "").strip().lower()
        matching_nodes = [
            node
            for node in model.nodes
            if query in node.label.lower() or query in node.id.lower()
        ]
        matching_nodes = matching_nodes[:50]

        def _format_node(node_id: str | None) -> str:
            if node_id is None:
                return "—"
            node = model.nodes_by_id.get(node_id)
            return f"{node.label} ({node.type})" if node else node_id

        def _on_search_select() -> None:
            selected = st.session_state.get("graph_search_selected_id")
            if selected:
                st.session_state["graph_selected_node_id"] = selected

        options = [None] + [node.id for node in matching_nodes]
        st.selectbox(
            "Результаты",
            options,
            key="graph_search_selected_id",
            format_func=_format_node,
            on_change=_on_search_select,
        )

        st.markdown("#### Параметры")
        st.selectbox("Глубина", [1, 2], key="graph_depth")
        st.slider("Макс. узлов", 20, 120, key="graph_max_nodes")
        st.selectbox("Layout", ["fcose", "breadthfirst", "concentric"], key="graph_layout_name")

        st.markdown("#### Фильтры узлов")
        for node_type in NODE_TYPES:
            st.checkbox(
                node_type,
                key=f"graph_node_filter_{node_type}",
                on_change=_sync_node_filters,
            )

        st.markdown("#### Фильтры связей")
        for edge_type in EDGE_TYPES:
            st.checkbox(
                edge_type,
                key=f"graph_edge_filter_{edge_type}",
                on_change=_sync_edge_filters,
            )

        st.button(
            "Сбросить подсветку",
            key="graph-clear-selection",
            on_click=lambda: st.session_state.update(
                {"graph_selected_node_id": None, "graph_selected_edge_id": None}
            ),
        )

    with center_col:
        _legend()
        depth = int(st.session_state.get("graph_depth", 1))
        if st.session_state.get("graph_expand_depth_override"):
            depth = min(2, depth + 1)
        elements, included_nodes, _ = _build_subgraph(
            model,
            selected_node_id or "",
            st.session_state.get("graph_node_type_filters", {}),
            st.session_state.get("graph_edge_type_filters", {}),
            depth,
            int(st.session_state.get("graph_max_nodes", 60)),
        )
        layout = {"name": st.session_state.get("graph_layout_name", "fcose"), "animate": False}
        selected = cytoscape(
            elements,
            _stylesheet(),
            layout=layout,
            height="600px",
            selection_type="single",
        )
        node_id, edge_id = _extract_selected_ids(selected)
        if node_id:
            st.session_state["graph_selected_node_id"] = node_id
            st.session_state["graph_selected_edge_id"] = None
        elif edge_id:
            st.session_state["graph_selected_edge_id"] = edge_id
        if node_id:
            now = time.monotonic()
            last_node = st.session_state.get("graph_last_click_node_id")
            last_ts = st.session_state.get("graph_last_click_ts", 0.0)
            if node_id == last_node and (now - last_ts) <= 0.45:
                st.session_state["graph_expand_depth_override"] = True
                st.rerun()
            st.session_state["graph_last_click_node_id"] = node_id
            st.session_state["graph_last_click_ts"] = now

        if st.session_state.get("graph_expand_depth_override"):
            st.session_state["graph_expand_depth_override"] = False

        if not included_nodes:
            st.info("Выберите узел, чтобы увидеть его окружение.")

    with right_col:
        st.markdown("#### Детали")
        node_id = st.session_state.get("graph_selected_node_id")
        edge_id = st.session_state.get("graph_selected_edge_id")
        if node_id and node_id in model.nodes_by_id:
            _render_node_details(model.nodes_by_id[node_id])
            st.button(
                "Раскрыть связи",
                key="graph-expand-node",
                on_click=lambda: st.session_state.update({"graph_expand_depth_override": True}),
            )
        elif edge_id and edge_id in model.edges_by_id:
            _render_edge_details(model.edges_by_id[edge_id])
        else:
            st.caption("Кликните на узел или ребро, чтобы увидеть подробности.")


def render_path_tab(data: AppData) -> None:
    st.subheader("Путь")
    st.markdown("Визуализация выбранного маршрута и его переходов.")

    route_options = [path.id for path in data.paths]
    if not route_options:
        st.info("Маршруты пока не добавлены.")
        return

    def _route_label(route_id: str | None) -> str:
        if route_id is None:
            return "Выберите маршрут"
        path = next((item for item in data.paths if item.id == route_id), None)
        if not path:
            return route_id
        return " → ".join(path.sequence)

    cols = st.columns([2, 1])
    cols[0].selectbox(
        "Маршрут",
        [None] + route_options,
        key="graph_path_route_id",
        format_func=_route_label,
    )
    cols[1].checkbox("Показать способы и варианты", key="graph_path_show_related")

    selected_route = st.session_state.get("graph_path_route_id")
    if not selected_route:
        st.info("Выберите маршрут, чтобы построить путь.")
        return

    elements = _build_route_elements(
        data,
        selected_route,
        st.session_state.get("graph_path_show_related", False),
    )
    layout = {"name": "breadthfirst", "directed": True, "padding": 10}
    cytoscape(
        elements,
        _stylesheet(),
        layout=layout,
        height="520px",
        selection_type="single",
    )


def render(data: AppData, filters: components.Filters) -> None:
    st.title("Граф")
    st.markdown("Интерактивная карта связей между сущностями Money Map.")

    ensure_graph_state_defaults()

    tab_labels = ["Обзор", "Исследование", "Путь"]
    current = st.session_state.get("graph_tab", "Обзор")
    if current not in tab_labels:
        current = "Обзор"
    st.radio(
        "Раздел графа",
        tab_labels,
        horizontal=True,
        key="graph_tab",
    )

    active_tab = st.session_state.get("graph_tab", "Обзор")
    if active_tab == "Обзор":
        render_overview_tab(data)
    elif active_tab == "Исследование":
        render_explore_tab(data, filters)
    else:
        render_path_tab(data)
