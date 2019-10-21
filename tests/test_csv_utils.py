from source.csv_utils import normalize_table


def test_normalize_rows():
    rows = [
        ["", "", ""],
        ["a", "b", "", "c"],
        ["1", "foo", "", "bar"],
        ["2", "foo", "", "baz"],
        ["3", "foo"],
        ["4", "foo", "", "bar"],
        ["5", "foo", "", "bar", ""],
    ]
    expected_rows = [
        ["a", "b", "c"],
        ["1", "foo", "bar"],
        ["2", "foo", "baz"],
        ["3", "foo", ""],
        ["4", "foo", "bar"],
        ["5", "foo", "bar"],
    ]
    assert normalize_table(rows) == expected_rows
