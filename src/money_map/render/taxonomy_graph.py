from __future__ import annotations

from typing import Optional

import networkx as nx

from money_map.core.model import AppData
from money_map.core.taxonomy_graph import build_taxonomy_star


def build_taxonomy_pyvis(
    graph: nx.DiGraph,
    height: str = "720px",
    width: str = "100%",
    directed: bool = True,
):
    from pyvis.network import Network

    net = Network(height=height, width=width, directed=directed, bgcolor="#ffffff")
    net.toggle_physics(False)

    for node_id, attrs in graph.nodes(data=True):
        kind = attrs.get("kind")
        color = _node_color(kind)
        net.add_node(
            node_id,
            label=attrs.get("label", node_id),
            title=attrs.get("title"),
            x=attrs.get("x"),
            y=attrs.get("y"),
            fixed=True,
            color=color,
        )

    for source, target, attrs in graph.edges(data=True):
        kind = attrs.get("kind")
        net.add_edge(
            source,
            target,
            width=attrs.get("width", 1),
            color=_edge_color(kind),
            arrows="to",
        )

    return net


def render_taxonomy_graph_html(
    data: AppData,
    include_tags: bool = True,
    outside_only: bool = False,
    height: str = "720px",
    width: str = "100%",
) -> str:
    graph = build_taxonomy_star(data, include_tags=include_tags, outside_only=outside_only)
    net = build_taxonomy_pyvis(graph, height=height, width=width)
    return net.generate_html()


def _node_color(kind: Optional[str]) -> str:
    if kind == "root":
        return "#FDE68A"
    if kind == "taxonomy":
        return "#93C5FD"
    if kind == "tag":
        return "#D1D5DB"
    return "#FFFFFF"


def _edge_color(kind: Optional[str]) -> str:
    if kind == "tag":
        return "#9CA3AF"
    return "#2563EB"
