from money_map.core.load import load_app_data
from money_map.core.validate import validate_app_data


def test_validate_data_ok() -> None:
    data = load_app_data()
    errors = validate_app_data(data)
    assert errors == []
