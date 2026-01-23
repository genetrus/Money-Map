from __future__ import annotations

from dataclasses import dataclass, field

from money_map.core.model import AppData


@dataclass(frozen=True)
class GraphNode:
    id: str
    label: str
    type: str
    meta: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class GraphEdge:
    id: str
    source: str
    target: str
    label: str
    type: str
    meta: dict[str, object] = field(default_factory=dict)


@dataclass
class GraphModel:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    nodes_by_id: dict[str, GraphNode]
    edges_by_id: dict[str, GraphEdge]
    adjacency: dict[str, set[str]]
    incident_edges: dict[str, set[str]]
    edges_by_type: dict[str, set[str]]
    nodes_by_type: dict[str, set[str]]


def _add_node(
    nodes: list[GraphNode],
    nodes_by_id: dict[str, GraphNode],
    nodes_by_type: dict[str, set[str]],
    node_id: str,
    label: str,
    node_type: str,
    meta: dict[str, object] | None = None,
) -> None:
    if node_id in nodes_by_id:
        return
    payload = GraphNode(id=node_id, label=label, type=node_type, meta=meta or {})
    nodes.append(payload)
    nodes_by_id[node_id] = payload
    nodes_by_type.setdefault(node_type, set()).add(node_id)


def _add_edge(
    edges: list[GraphEdge],
    edges_by_id: dict[str, GraphEdge],
    edges_by_type: dict[str, set[str]],
    adjacency: dict[str, set[str]],
    incident_edges: dict[str, set[str]],
    edge_id: str,
    source: str,
    target: str,
    label: str,
    edge_type: str,
    meta: dict[str, object] | None = None,
) -> None:
    if edge_id in edges_by_id:
        return
    payload = GraphEdge(
        id=edge_id,
        source=source,
        target=target,
        label=label,
        type=edge_type,
        meta=meta or {},
    )
    edges.append(payload)
    edges_by_id[edge_id] = payload
    edges_by_type.setdefault(edge_type, set()).add(edge_id)
    adjacency.setdefault(source, set()).add(target)
    adjacency.setdefault(target, set()).add(source)
    incident_edges.setdefault(source, set()).add(edge_id)
    incident_edges.setdefault(target, set()).add(edge_id)


def build_base_graph(data: AppData) -> GraphModel:
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    nodes_by_id: dict[str, GraphNode] = {}
    edges_by_id: dict[str, GraphEdge] = {}
    adjacency: dict[str, set[str]] = {}
    incident_edges: dict[str, set[str]] = {}
    edges_by_type: dict[str, set[str]] = {}
    nodes_by_type: dict[str, set[str]] = {}

    for cell in data.cells:
        _add_node(
            nodes,
            nodes_by_id,
            nodes_by_type,
            f"cell:{cell.id}",
            f"{cell.id} {cell.label}",
            "cell",
            {"cell_id": cell.id},
        )

    for item in data.taxonomy:
        _add_node(
            nodes,
            nodes_by_id,
            nodes_by_type,
            f"way:{item.id}",
            item.name,
            "way",
            {"way_id": item.id},
        )

    for group_key, items in (
        ("what_sell", data.mappings.sell_items),
        ("to_whom", data.mappings.to_whom_items),
        ("value_measure", data.mappings.value_measures),
    ):
        for item_id, mapping in items.items():
            _add_node(
                nodes,
                nodes_by_id,
                nodes_by_type,
                f"classifier:{group_key}.{item_id}",
                mapping.label,
                "classifier",
                {"group": group_key, "classifier_id": item_id},
            )

    for bridge in data.bridges:
        _add_node(
            nodes,
            nodes_by_id,
            nodes_by_type,
            f"bridge:{bridge.id}",
            bridge.name,
            "bridge",
            {"bridge_id": bridge.id},
        )

    for path in data.paths:
        _add_node(
            nodes,
            nodes_by_id,
            nodes_by_type,
            f"route:{path.id}",
            path.name,
            "route",
            {"route_id": path.id},
        )

    for variant in data.variants:
        _add_node(
            nodes,
            nodes_by_id,
            nodes_by_type,
            f"variant:{variant.id}",
            variant.title,
            "variant",
            {"variant_id": variant.id},
        )

    for item in data.taxonomy:
        way_id = f"way:{item.id}"
        for tag in item.sell:
            target = f"classifier:what_sell.{tag}"
            _add_edge(
                edges,
                edges_by_id,
                edges_by_type,
                adjacency,
                incident_edges,
                f"has_classifier:{item.id}:sell:{tag}",
                way_id,
                target,
                "продаёт",
                "has_classifier",
                {"group": "what_sell"},
            )
        for tag in item.to_whom:
            target = f"classifier:to_whom.{tag}"
            _add_edge(
                edges,
                edges_by_id,
                edges_by_type,
                adjacency,
                incident_edges,
                f"has_classifier:{item.id}:to:{tag}",
                way_id,
                target,
                "кому",
                "has_classifier",
                {"group": "to_whom"},
            )
        for tag in item.value:
            target = f"classifier:value_measure.{tag}"
            _add_edge(
                edges,
                edges_by_id,
                edges_by_type,
                adjacency,
                incident_edges,
                f"has_classifier:{item.id}:value:{tag}",
                way_id,
                target,
                "ценность",
                "has_classifier",
                {"group": "value_measure"},
            )
        for cell_id in item.typical_cells:
            _add_edge(
                edges,
                edges_by_id,
                edges_by_type,
                adjacency,
                incident_edges,
                f"maps_to_cell:{item.id}:{cell_id}",
                way_id,
                f"cell:{cell_id}",
                "типичная ячейка",
                "maps_to_cell",
            )

    transitions: set[tuple[str, str]] = set()
    for bridge in data.bridges:
        transitions.add((bridge.from_cell, bridge.to_cell))
    for path in data.paths:
        for idx in range(len(path.sequence) - 1):
            transitions.add((path.sequence[idx], path.sequence[idx + 1]))

    for from_cell, to_cell in sorted(transitions):
        transition_id = f"transition:{from_cell}->{to_cell}"
        _add_edge(
            edges,
            edges_by_id,
            edges_by_type,
            adjacency,
            incident_edges,
            transition_id,
            f"cell:{from_cell}",
            f"cell:{to_cell}",
            f"{from_cell} → {to_cell}",
            "transition",
        )

    for bridge in data.bridges:
        bridge_id = f"bridge:{bridge.id}"
        from_cell = f"cell:{bridge.from_cell}"
        to_cell = f"cell:{bridge.to_cell}"
        _add_edge(
            edges,
            edges_by_id,
            edges_by_type,
            adjacency,
            incident_edges,
            f"bridge_for_transition:{bridge.id}:from",
            bridge_id,
            from_cell,
            "из",
            "bridge_for_transition",
        )
        _add_edge(
            edges,
            edges_by_id,
            edges_by_type,
            adjacency,
            incident_edges,
            f"bridge_for_transition:{bridge.id}:to",
            bridge_id,
            to_cell,
            "в",
            "bridge_for_transition",
        )
        for route_id in bridge.linked_route_ids:
            _add_edge(
                edges,
                edges_by_id,
                edges_by_type,
                adjacency,
                incident_edges,
                f"route_uses_bridge:{route_id}:{bridge.id}",
                f"route:{route_id}",
                bridge_id,
                "использует",
                "route_uses_bridge",
            )

    for path in data.paths:
        route_id = f"route:{path.id}"
        for cell_id in path.sequence:
            _add_edge(
                edges,
                edges_by_id,
                edges_by_type,
                adjacency,
                incident_edges,
                f"route_contains:{path.id}:{cell_id}",
                route_id,
                f"cell:{cell_id}",
                "содержит",
                "route_contains",
            )

    for variant in data.variants:
        variant_id = f"variant:{variant.id}"
        _add_edge(
            edges,
            edges_by_id,
            edges_by_type,
            adjacency,
            incident_edges,
            f"variant_of_way:{variant.id}:{variant.primary_way_id}",
            variant_id,
            f"way:{variant.primary_way_id}",
            "вариант",
            "variant_of_way",
        )
        for cell_id in variant.matrix_cells:
            _add_edge(
                edges,
                edges_by_id,
                edges_by_type,
                adjacency,
                incident_edges,
                f"variant_fits_cell:{variant.id}:{cell_id}",
                variant_id,
                f"cell:{cell_id}",
                "подходит",
                "variant_fits_cell",
            )
        for bridge_id in variant.bridge_ids:
            _add_edge(
                edges,
                edges_by_id,
                edges_by_type,
                adjacency,
                incident_edges,
                f"variant_uses_bridge:{variant.id}:{bridge_id}",
                variant_id,
                f"bridge:{bridge_id}",
                "использует",
                "variant_uses_bridge",
            )

    return GraphModel(
        nodes=nodes,
        edges=edges,
        nodes_by_id=nodes_by_id,
        edges_by_id=edges_by_id,
        adjacency=adjacency,
        incident_edges=incident_edges,
        edges_by_type=edges_by_type,
        nodes_by_type=nodes_by_type,
    )
