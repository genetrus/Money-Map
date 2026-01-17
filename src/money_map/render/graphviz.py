from __future__ import annotations

from typing import List

from money_map.core.model import AppData


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
