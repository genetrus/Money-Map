from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from money_map.core.classify import classify_by_tags, classify_by_text
from money_map.core.graph import build_graph, outgoing_bridges, shortest_path
from money_map.core.load import load_app_data
from money_map.core.query import (
    get_cell,
    get_path,
    get_taxonomy,
    list_axes,
    list_bridges,
    list_cells,
    list_paths,
    list_taxonomy,
    search_text,
)
from money_map.core.validate import validate_app_data
from money_map.render.ascii import render_full_ascii
from money_map.render.graphviz import render_graphviz, render_taxonomy_graphviz
from money_map.render.json_export import write_index_json
from money_map.render.markdown import (
    render_bridges_md,
    render_full_summary_md,
    render_matrix_md,
    render_paths_md,
    render_taxonomy_md,
)
from money_map.render.taxonomy_graph import render_taxonomy_graph_html

app = typer.Typer(help="Money Map CLI")
console = Console()


@app.command()
def validate() -> None:
    """Проверить целостность данных."""
    data = load_app_data()
    errors = validate_app_data(data)
    if errors:
        console.print("[red]Найдены ошибки данных:[/red]")
        for err in errors:
            console.print(f"- {err}")
        raise typer.Exit(code=1)
    console.print("[green]Данные корректны.[/green]")


@app.command()
def axes() -> None:
    data = load_app_data()
    table = Table(title="Оси")
    table.add_column("ID")
    table.add_column("Значения")
    table.add_column("Метки")
    for axis in list_axes(data):
        values = ", ".join(axis["values"])
        labels = ", ".join([f"{key}:{value}" for key, value in axis["labels"].items()])
        table.add_row(axis["id"], values, labels)
    console.print(table)


@app.command()
def cells() -> None:
    data = load_app_data()
    table = Table(title="Ячейки")
    table.add_column("ID")
    table.add_column("Описание")
    table.add_column("Примеры")
    for cell in list_cells(data):
        table.add_row(cell.id, cell.short, ", ".join(cell.examples))
    console.print(table)


@app.command()
def cell(cell_id: str) -> None:
    data = load_app_data()
    cell_item = get_cell(data, cell_id)
    if not cell_item:
        console.print(f"[red]Ячейка {cell_id} не найдена.[/red]")
        raise typer.Exit(code=1)
    console.print(f"[bold]{cell_item.label}[/bold]")
    console.print(cell_item.short)
    console.print("Примеры:")
    for example in cell_item.examples:
        console.print(f"- {example}")


@app.command()
def taxonomy() -> None:
    data = load_app_data()
    table = Table(title="Таксономия")
    table.add_column("ID")
    table.add_column("Название")
    for item in list_taxonomy(data):
        table.add_row(item.id, item.name)
    console.print(table)


@app.command()
def tax(item_id: str) -> None:
    data = load_app_data()
    item = get_taxonomy(data, item_id)
    if not item:
        console.print(f"[red]Механизм {item_id} не найден.[/red]")
        raise typer.Exit(code=1)
    console.print(f"[bold]{item.name}[/bold]")
    console.print(item.description)
    console.print(f"sell: {', '.join(item.sell) or '—'}")
    console.print(f"to_whom: {', '.join(item.to_whom) or '—'}")
    console.print(f"value: {', '.join(item.value) or '—'}")
    console.print(f"typical_cells: {', '.join(item.typical_cells)}")
    console.print(f"outside_market: {'да' if item.outside_market else 'нет'}")
    console.print(f"risk_notes: {item.risk_notes}")
    console.print("Примеры:")
    for example in item.examples:
        console.print(f"- {example}")


@app.command()
def bridges(from_cell: Optional[str] = None, to_cell: Optional[str] = None) -> None:
    data = load_app_data()
    items = list_bridges(data, from_cell=from_cell, to_cell=to_cell)
    table = Table(title="Мосты")
    table.add_column("ID")
    table.add_column("От")
    table.add_column("К")
    table.add_column("Название")
    for bridge in items:
        table.add_row(bridge.id, bridge.from_cell, bridge.to_cell, bridge.name)
    console.print(table)


@app.command()
def paths() -> None:
    data = load_app_data()
    table = Table(title="Маршруты")
    table.add_column("ID")
    table.add_column("Название")
    table.add_column("Последовательность")
    for item in list_paths(data):
        table.add_row(item.id, item.name, " → ".join(item.sequence))
    console.print(table)


@app.command()
def path(path_id: str) -> None:
    data = load_app_data()
    item = get_path(data, path_id)
    if not item:
        console.print(f"[red]Маршрут {path_id} не найден.[/red]")
        raise typer.Exit(code=1)
    console.print(f"[bold]{item.name}[/bold]")
    console.print(f"Путь: {' → '.join(item.sequence)}")
    console.print(f"Заметка: {item.note}")


@app.command()
def search(text: str) -> None:
    data = load_app_data()
    results = search_text(data, text)
    console.print(f"Поиск по: {text}")
    for key, values in results.items():
        console.print(f"{key}: {', '.join(values) if values else '—'}")


@app.command()
def classify(
    text: Optional[str] = None,
    sell: List[str] = typer.Option(None, "--sell"),
    to: List[str] = typer.Option(None, "--to"),
    value: List[str] = typer.Option(None, "--value"),
) -> None:
    data = load_app_data()
    if text:
        result = classify_by_text(data, text)
    else:
        result = classify_by_tags(data, sell or [], to or [], value or [])

    console.print("[bold]Теги[/bold]")
    console.print(result.tags)
    console.print("[bold]Таксономия[/bold]")
    for item_id, score in result.taxonomy_scores:
        console.print(f"- {item_id}: {score}")
    console.print("[bold]Ячейки[/bold]")
    for cell_id, score in result.cell_scores:
        console.print(f"- {cell_id}: {score}")
    console.print(f"Уверенность: {result.confidence}")
    for line in result.explanation:
        console.print(f"Совпадения: {line}")


@app.command()
def render(format: str = typer.Argument(...)) -> None:
    data = load_app_data()
    if format == "ascii":
        console.print(render_full_ascii(data))
    elif format == "md":
        console.print(render_full_summary_md(data))
    elif format == "dot":
        console.print(render_graphviz(data))
    else:
        console.print("[red]Неизвестный формат рендера.[/red]")
        raise typer.Exit(code=1)


@app.command()
def export(command: str = typer.Argument(...)) -> None:
    data = load_app_data()
    export_dir = Path(__file__).resolve().parents[3] / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    if command == "taxonomy-graph":
        _export_taxonomy_graph(data, export_dir)
        console.print(f"Экспорт графа таксономии сохранён в {export_dir}")
        return
    if command != "all":
        console.print("[red]Поддерживаются только export all или export taxonomy-graph.[/red]")
        raise typer.Exit(code=1)

    (export_dir / "matrix.md").write_text(render_matrix_md(data), encoding="utf-8")
    (export_dir / "bridges.md").write_text(render_bridges_md(data), encoding="utf-8")
    (export_dir / "paths.md").write_text(render_paths_md(data), encoding="utf-8")
    (export_dir / "taxonomy.md").write_text(render_taxonomy_md(data), encoding="utf-8")
    (export_dir / "full_summary.md").write_text(render_full_summary_md(data), encoding="utf-8")
    (export_dir / "map_ascii.txt").write_text(render_full_ascii(data), encoding="utf-8")
    (export_dir / "graph.dot").write_text(render_graphviz(data), encoding="utf-8")
    _export_taxonomy_graph(data, export_dir)
    write_index_json(data, export_dir / "index.json")

    console.print(f"Экспорт сохранён в {export_dir}")


@app.command()
def graph(command: str, start: Optional[str] = None, end: Optional[str] = None) -> None:
    data = load_app_data()
    if command == "show":
        graph_data = build_graph(data)
        console.print("Рёбра:")
        for source, target in graph_data.edges():
            console.print(f"- {source} -> {target}")
        return
    if command == "shortest":
        if not start or not end:
            console.print("[red]Нужно указать start и end.[/red]")
            raise typer.Exit(code=1)
        path = shortest_path(data, start, end)
        console.print(" → ".join(path))
        return
    if command == "outgoing":
        if not start:
            console.print("[red]Нужно указать start.[/red]")
            raise typer.Exit(code=1)
        items = outgoing_bridges(data, start)
        for bridge in items:
            console.print(f"- {bridge.name} ({bridge.to_cell})")
        return

    console.print("[red]Команда графа не распознана.[/red]")
    raise typer.Exit(code=1)


@app.command()
def ui() -> None:
    """Запустить Streamlit-интерфейс."""
    if importlib.util.find_spec("streamlit") is None:
        console.print(
            "[red]Streamlit не установлен.[/red] Установите зависимости: pip install -e \".[ui]\""
        )
        raise typer.Exit(code=1)

    import money_map.ui.app as ui_app

    app_path = Path(ui_app.__file__).resolve()
    command = build_streamlit_command(app_path)
    console.print(
        "Запускаю UI Streamlit... Откроется браузер. Если нет — открой http://localhost:8501"
    )
    console.print(" ".join(command))
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        raise typer.Exit(code=exc.returncode) from exc


def build_streamlit_command(
    app_path: Path,
    extra_args: Optional[List[str]] = None,
) -> List[str]:
    command = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    if extra_args:
        command.extend(extra_args)
    return command


def _export_taxonomy_graph(data, export_dir: Path) -> None:
    try:
        html = render_taxonomy_graph_html(data, include_tags=True, outside_only=False)
    except ModuleNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    (export_dir / "taxonomy_graph.html").write_text(html, encoding="utf-8")
    (export_dir / "taxonomy_graph.dot").write_text(
        render_taxonomy_graphviz(data, include_tags=True, outside_only=False),
        encoding="utf-8",
    )
