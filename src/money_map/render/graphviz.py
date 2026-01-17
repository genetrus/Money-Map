from __future__ import annotations

from typing import List

from money_map.core.model import AppData
from money_map.core.taxonomy_graph import build_taxonomy_star


def render_graphviz(data: AppData) -> str:
    rankdir = data.diagrams.diagrams.get("graphviz", {}).get("rankdir", "LR")
    lines: List[str] = ["digraph MoneyMap {", f"  rankdir={rankdir};"]
    for cell in sorted(data.cells, key=lambda item: item.id):
        color = "lightgreen" if cell.risk == "low" else "lightcoral"
        lines.append(
            f"  {cell.id} [label=\"{cell.id}\\n{cell.short}\", style=filled, fillcolor={color}];"
        )
    for bridge in sorted(data.bridges, key=lambda item: item.id):
        lines.append(f"  {bridge.from_cell} -> {bridge.to_cell} [label=\"{bridge.name}\"]; ")
    lines.append("}")
    return "\n".join(lines)


def render_taxonomy_graphviz(
    data: AppData,
    include_tags: bool = True,
    outside_only: bool = False,
) -> str:
    graph = build_taxonomy_star(data, include_tags=include_tags, outside_only=outside_only)
    lines: List[str] = [
        "digraph TaxonomyStar {",
        "  graph [splines=true, overlap=false];",
        "  node [shape=circle, fontname=\"Helvetica\"];",
    ]
    for node_id, attrs in graph.nodes(data=True):
        label = (attrs.get("label", node_id)).replace("\n", "\\n").replace('"', '\\"')
        shape = "doublecircle" if node_id == "root" else "ellipse"
        pos = ""
        if "x" in attrs and "y" in attrs:
            pos = f", pos=\"{attrs['x']},{attrs['y']}!\""
        lines.append(f"  \"{node_id}\" [label=\"{label}\", shape={shape}{pos}];")
    for source, target, attrs in graph.edges(data=True):
        color = "gray" if attrs.get("kind") == "tag" else "black"
        lines.append(f"  \"{source}\" -> \"{target}\" [color={color}];")
    lines.append("}")
    return "\n".join(lines)
