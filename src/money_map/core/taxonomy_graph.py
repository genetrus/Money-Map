from __future__ import annotations

import math
from typing import Dict, Iterable, List, Tuple

import networkx as nx

from money_map.core.model import AppData, TaxonomyItem

TAG_GROUPS: Dict[str, List[str]] = {
    "sell": ["time", "result", "risk", "access", "attention", "capital", "property"],
    "to": ["single_client", "many_people", "market", "state", "platform"],
    "value": ["rate", "price", "percent", "rent", "payout", "appreciation"],
}


def layout_star_positions(
    taxonomy_nodes: Iterable[str],
    tag_nodes_by_group: Dict[str, List[str]],
    radius_taxonomy: float = 300,
    radius_tag: float = 520,
) -> Dict[str, Tuple[float, float]]:
    positions: Dict[str, Tuple[float, float]] = {"root": (0.0, 0.0)}
    taxonomy_nodes_list = list(taxonomy_nodes)
    if taxonomy_nodes_list:
        step = 2 * math.pi / len(taxonomy_nodes_list)
        for index, node_id in enumerate(taxonomy_nodes_list):
            angle = step * index - math.pi / 2
            positions[node_id] = (
                radius_taxonomy * math.cos(angle),
                radius_taxonomy * math.sin(angle),
            )

    tag_nodes: List[str] = []
    for group in ("sell", "to", "value"):
        tag_nodes.extend(tag_nodes_by_group.get(group, []))
    if tag_nodes:
        step = 2 * math.pi / len(tag_nodes)
        for index, node_id in enumerate(tag_nodes):
            angle = step * index - math.pi / 2
            positions[node_id] = (
                radius_tag * math.cos(angle),
                radius_tag * math.sin(angle),
            )
    return positions


def build_taxonomy_star(
    app_data: AppData,
    include_tags: bool,
    outside_only: bool,
    allowed_taxonomy_ids: set[str] | None = None,
) -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_node(
        "root",
        label="Способы\nполучения денег",
        kind="root",
        title="Способы получения денег",
    )

    taxonomy_items = [
        item
        for item in app_data.taxonomy
        if (not outside_only or item.outside_market)
        and (allowed_taxonomy_ids is None or item.id in allowed_taxonomy_ids)
    ]
    taxonomy_nodes = [f"tax:{item.id}" for item in taxonomy_items]

    tag_nodes_by_group: Dict[str, List[str]] = {}
    if include_tags:
        tag_nodes_by_group = _collect_tag_nodes(taxonomy_items)

    positions = layout_star_positions(taxonomy_nodes, tag_nodes_by_group)
    for node_id, (x, y) in positions.items():
        if node_id in graph.nodes:
            graph.nodes[node_id]["x"] = x
            graph.nodes[node_id]["y"] = y

    for item in taxonomy_items:
        node_id = f"tax:{item.id}"
        x, y = positions.get(node_id, (0.0, 0.0))
        graph.add_node(
            node_id,
            label=item.name,
            title=_taxonomy_tooltip(item),
            kind="taxonomy",
            outside_market=item.outside_market,
            x=x,
            y=y,
        )
        graph.add_edge("root", node_id, kind="root", width=2)

    if include_tags:
        _add_tag_nodes(
            graph=graph,
            app_data=app_data,
            taxonomy_items=taxonomy_items,
            tag_nodes_by_group=tag_nodes_by_group,
            positions=positions,
        )

    return graph


def _taxonomy_tooltip(item: TaxonomyItem) -> str:
    return (
        f"{item.name}<br>"
        f"{item.description}<br>"
        f"Продаём: {', '.join(item.sell) or '—'}<br>"
        f"Кому: {', '.join(item.to_whom) or '—'}<br>"
        f"Мера ценности: {', '.join(item.value) or '—'}<br>"
        f"Типовые ячейки: {', '.join(item.typical_cells) or '—'}<br>"
        f"Вне рынка: {'Да' if item.outside_market else 'Нет'}"
    )


def _collect_tag_nodes(taxonomy_items: Iterable[TaxonomyItem]) -> Dict[str, List[str]]:
    used_tags = {
        "sell": set(),
        "to": set(),
        "value": set(),
    }
    for item in taxonomy_items:
        used_tags["sell"].update(item.sell)
        used_tags["to"].update(item.to_whom)
        used_tags["value"].update(item.value)

    tag_nodes_by_group: Dict[str, List[str]] = {}
    for group, tag_ids in TAG_GROUPS.items():
        included = [tag_id for tag_id in tag_ids if tag_id in used_tags[group]]
        tag_nodes_by_group[group] = [f"{group}:{tag_id}" for tag_id in included]
    return tag_nodes_by_group


def _tag_label(app_data: AppData, group: str, tag_id: str) -> str:
    if group == "sell":
        mapping = app_data.mappings.sell_items.get(tag_id)
    elif group == "to":
        mapping = app_data.mappings.to_whom_items.get(tag_id)
    else:
        mapping = app_data.mappings.value_measures.get(tag_id)
    return mapping.label if mapping else tag_id


def _add_tag_nodes(
    graph: nx.DiGraph,
    app_data: AppData,
    taxonomy_items: Iterable[TaxonomyItem],
    tag_nodes_by_group: Dict[str, List[str]],
    positions: Dict[str, Tuple[float, float]],
) -> None:
    tag_nodes_set = {node_id for nodes in tag_nodes_by_group.values() for node_id in nodes}
    for node_id in tag_nodes_set:
        group, tag_id = node_id.split(":", 1)
        label = _tag_label(app_data, group, tag_id)
        x, y = positions.get(node_id, (0.0, 0.0))
        graph.add_node(
            node_id,
            label=label,
            title=label,
            kind="tag",
            group=group,
            x=x,
            y=y,
        )

    for item in taxonomy_items:
        source_id = f"tax:{item.id}"
        for tag_id in item.sell:
            _add_tag_edge(graph, source_id, f"sell:{tag_id}")
        for tag_id in item.to_whom:
            _add_tag_edge(graph, source_id, f"to:{tag_id}")
        for tag_id in item.value:
            _add_tag_edge(graph, source_id, f"value:{tag_id}")


def _add_tag_edge(graph: nx.DiGraph, source: str, target: str) -> None:
    if target not in graph.nodes:
        return
    graph.add_edge(source, target, kind="tag", width=1)
