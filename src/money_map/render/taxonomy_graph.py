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
    selected_node: Optional[str] = None,
):
    from pyvis.network import Network

    net = Network(height=height, width=width, directed=directed, bgcolor="#ffffff")
    net.toggle_physics(False)

    for node_id, attrs in graph.nodes(data=True):
        kind = attrs.get("kind")
        color = _node_color(kind)
        node_kwargs = {
            "label": attrs.get("label", node_id),
            "title": attrs.get("title"),
            "x": attrs.get("x"),
            "y": attrs.get("y"),
            "fixed": True,
            "color": color,
        }
        if node_id == selected_node:
            node_kwargs["borderWidth"] = 4
            node_kwargs["size"] = 30
            node_kwargs["color"] = {
                "border": "#1D4ED8",
                "background": color,
                "highlight": {
                    "border": "#1D4ED8",
                    "background": color,
                },
            }
        net.add_node(node_id, **node_kwargs)

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
    selected_tax_id: Optional[str] = None,
    height: str = "720px",
    width: str = "100%",
) -> str:
    graph = build_taxonomy_star(data, include_tags=include_tags, outside_only=outside_only)
    selected_node = f"tax:{selected_tax_id}" if selected_tax_id else None
    net = build_taxonomy_pyvis(graph, height=height, width=width, selected_node=selected_node)
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
