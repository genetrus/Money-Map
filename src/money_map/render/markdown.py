from __future__ import annotations

from typing import Dict, List

from money_map.core.model import AppData, Cell


def render_matrix_md(data: AppData) -> str:
    parts = ["# Матрица 2×2×2", ""]
    low_cells = [cell for cell in data.cells if cell.risk == "low"]
    high_cells = [cell for cell in data.cells if cell.risk == "high"]
    parts.append(_render_layer("Низкий риск", low_cells))
    parts.append(_render_layer("Высокий риск", high_cells))
    return "\n".join(parts)


def render_bridges_md(data: AppData) -> str:
    lines = ["# Мосты", ""]
    grouped: Dict[str, List[str]] = {}
    for bridge in sorted(data.bridges, key=lambda item: item.id):
        key = f"{bridge.from_cell} → {bridge.to_cell}"
        grouped.setdefault(key, []).append(f"- **{bridge.name}** — {bridge.notes}")

    for key in sorted(grouped):
        lines.append(f"## {key}")
        lines.extend(grouped[key])
        lines.append("")
    return "\n".join(lines)


def render_paths_md(data: AppData) -> str:
    lines = ["# Пути", ""]
    for path in sorted(data.paths, key=lambda item: item.id):
        arrow = " → ".join(path.sequence)
        lines.append(f"- **{path.name}**: {arrow} — {path.note}")
    lines.append("")
    return "\n".join(lines)


def render_taxonomy_md(data: AppData) -> str:
    lines = ["# Таксономия", ""]
    for item in sorted(data.taxonomy, key=lambda item: item.id):
        lines.append(f"## {item.name} (`{item.id}`)")
        lines.append(item.description)
        lines.append("")
        lines.append(f"- sell: {', '.join(item.sell) or '—'}")
        lines.append(f"- to_whom: {', '.join(item.to_whom) or '—'}")
        lines.append(f"- value: {', '.join(item.value) or '—'}")
        lines.append(f"- typical_cells: {', '.join(item.typical_cells)}")
        lines.append(f"- outside_market: {'да' if item.outside_market else 'нет'}")
        lines.append(f"- risk_notes: {item.risk_notes}")
        lines.append(f"- examples: {', '.join(item.examples)}")
        lines.append("")
    return "\n".join(lines)


def render_full_summary_md(data: AppData) -> str:
    parts = [render_matrix_md(data), render_bridges_md(data), render_paths_md(data), render_taxonomy_md(data)]
    return "\n".join(parts)


def _render_layer(title: str, cells: List[Cell]) -> str:
    lookup = {cell.id: cell for cell in cells}
    mapping = {
        ("active", "linear"): _find_cell(lookup, "A1", "A3"),
        ("active", "scalable"): _find_cell(lookup, "A2", "A4"),
        ("passive", "linear"): _find_cell(lookup, "P1", "P3"),
        ("passive", "scalable"): _find_cell(lookup, "P2", "P4"),
    }

    lines = [f"## {title}", "", "| Активность \\ Масштаб | Линейно | Масштабируемо |", "|---|---|---|"]
    for activity_label, activity_key in [("Активно", "active"), ("Пассивно", "passive")]:
        row = [activity_label]
        for scale_key in ["linear", "scalable"]:
            cell = mapping[(activity_key, scale_key)]
            row.append(_cell_md(cell))
        lines.append(f"| {row[0]} | {row[1]} | {row[2]} |")
    lines.append("")
    return "\n".join(lines)


def _cell_md(cell: Cell) -> str:
    examples = ", ".join(cell.examples[:2])
    return f"**{cell.id}** {cell.short}<br/>Примеры: {examples}"


def _find_cell(lookup: Dict[str, Cell], primary: str, fallback: str) -> Cell:
    return lookup.get(primary) or lookup[fallback]
