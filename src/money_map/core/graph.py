from __future__ import annotations

from typing import List

import networkx as nx

from money_map.core.model import AppData, BridgeItem


def build_graph(data: AppData) -> nx.DiGraph:
    graph = nx.DiGraph()
    for cell in data.cells:
        graph.add_node(cell.id, label=cell.label)
    for bridge in data.bridges:
        graph.add_edge(bridge.from_cell, bridge.to_cell, id=bridge.id, name=bridge.name)
    return graph


def outgoing_bridges(data: AppData, cell_id: str) -> List[BridgeItem]:
    return [bridge for bridge in data.bridges if bridge.from_cell == cell_id]


def shortest_path(data: AppData, start: str, end: str) -> List[str]:
    graph = build_graph(data)
    return nx.shortest_path(graph, start, end)
