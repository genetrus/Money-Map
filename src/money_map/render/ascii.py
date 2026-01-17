from __future__ import annotations

from textwrap import fill
from typing import Dict, List

from money_map.core.model import AppData, Cell


def render_matrix_ascii(data: AppData) -> str:
    low_cells = [cell for cell in data.cells if cell.risk == "low"]
    high_cells = [cell for cell in data.cells if cell.risk == "high"]
    lines: List[str] = []
    lines.append("Матрица 2×2×2 (ASCII)")
    lines.append(render_layer("Низкий риск", low_cells))
    lines.append(render_layer("Высокий риск", high_cells))
    return "\n".join(lines)


def render_layer(title: str, cells: List[Cell]) -> str:
    lookup = {cell.id: cell for cell in cells}
    mapping = {
        ("active", "linear"): _find_cell(lookup, "A1", "A3"),
        ("active", "scalable"): _find_cell(lookup, "A2", "A4"),
        ("passive", "linear"): _find_cell(lookup, "P1", "P3"),
        ("passive", "scalable"): _find_cell(lookup, "P2", "P4"),
    }

    lines = [""]
    lines.append(f"== {title} ==")
    header = "| Активность \\ Масштаб | Линейно | Масштабируемо |"
    sep = "|---|---|---|"
    lines.append(header)
    lines.append(sep)

    for activity_label, activity_key in [("Активно", "active"), ("Пассивно", "passive")]:
        row = [activity_label]
        for scale_key in ["linear", "scalable"]:
            cell = mapping[(activity_key, scale_key)]
            content = _cell_brief(cell)
            row.append(content)
        lines.append(f"| {row[0]} | {row[1]} | {row[2]} |")
    return "\n".join(lines)


def render_paths_ascii(data: AppData) -> str:
    lines = ["", "Маршруты"]
    for path in sorted(data.paths, key=lambda item: item.id):
        arrow = " → ".join(path.sequence)
        lines.append(f"- {path.name}: {arrow}")
    return "\n".join(lines)


def render_bridges_ascii(data: AppData) -> str:
    grouped: Dict[str, List[str]] = {}
    for bridge in sorted(data.bridges, key=lambda item: item.id):
        key = f"{bridge.from_cell} → {bridge.to_cell}"
        grouped.setdefault(key, []).append(f"{bridge.name}")

    lines = ["", "Мосты"]
    for key in sorted(grouped):
        lines.append(f"{key}:")
        for name in grouped[key]:
            lines.append(f"  - {name}")
    return "\n".join(lines)


def render_full_ascii(data: AppData) -> str:
    return "\n".join([render_matrix_ascii(data), render_paths_ascii(data), render_bridges_ascii(data)])


def _cell_brief(cell: Cell) -> str:
    examples = ", ".join(cell.examples[:2])
    text = f"{cell.id}: {cell.short}. Примеры: {examples}"
    return fill(text, width=40)


def _find_cell(lookup: Dict[str, Cell], primary: str, fallback: str) -> Cell:
    return lookup.get(primary) or lookup[fallback]
