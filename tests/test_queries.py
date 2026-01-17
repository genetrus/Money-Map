from money_map.core.load import load_app_data
from money_map.core.query import get_cell, list_bridges, list_taxonomy


def test_query_cell() -> None:
    data = load_app_data()
    cell = get_cell(data, "A1")
    assert cell is not None
    assert "Активно" in cell.label


def test_list_taxonomy() -> None:
    data = load_app_data()
    items = list_taxonomy(data)
    assert any(item.id == "salary" for item in items)


def test_list_bridges() -> None:
    data = load_app_data()
    bridges = list_bridges(data, from_cell="A1", to_cell="A2")
    assert bridges
