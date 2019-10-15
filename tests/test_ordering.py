from source.ordering import (
    ColumnControl,
    get_ordering,
    sort_by_ordering,
    get_column_controls,
)
from starlette.datastructures import URL
from dataclasses import dataclass


def test_order_by_column():
    url = URL("?order=name")
    columns = {"name": "Name", "email": "Email"}
    order_column, order_reverse = get_ordering(url=url, columns=columns)
    assert order_column == "name"
    assert not order_reverse


def test_order_by_reverse_column():
    url = URL("?order=-name")
    columns = {"name": "Name", "email": "Email"}
    order_column, order_reverse = get_ordering(url=url, columns=columns)
    assert order_column == "name"
    assert order_reverse


def test_order_by_invalid_column():
    url = URL("?order=invalid")
    columns = {"name": "Name", "email": "Email"}
    order_column, order_reverse = get_ordering(url=url, columns=columns)
    assert order_column is None
    assert not order_reverse


@dataclass
class ExampleRecord:
    pk: int
    username: str
    email: str

    def __getitem__(self, item):
        return getattr(self, item)


def test_sort_by_ordering():
    queryset = [
        ExampleRecord(0, username="tom", email="tom@example.com"),
        ExampleRecord(1, username="lucy", email="lucy@example.com"),
        ExampleRecord(2, username="mia", email="mia@example.com"),
    ]
    sorted_queryset = sort_by_ordering(queryset, column="username", is_reverse=False)
    assert sorted_queryset == [
        ExampleRecord(1, username="lucy", email="lucy@example.com"),
        ExampleRecord(2, username="mia", email="mia@example.com"),
        ExampleRecord(0, username="tom", email="tom@example.com"),
    ]


def test_sort_by_reverse_ordering():
    queryset = [
        ExampleRecord(0, username="tom", email="tom@example.com"),
        ExampleRecord(1, username="lucy", email="lucy@example.com"),
        ExampleRecord(2, username="mia", email="mia@example.com"),
    ]
    sorted_queryset = sort_by_ordering(queryset, column="username", is_reverse=True)
    assert sorted_queryset == [
        ExampleRecord(0, username="tom", email="tom@example.com"),
        ExampleRecord(2, username="mia", email="mia@example.com"),
        ExampleRecord(1, username="lucy", email="lucy@example.com"),
    ]


def test_sort_without_ordering():
    queryset = [
        ExampleRecord(0, username="tom", email="tom@example.com"),
        ExampleRecord(1, username="lucy", email="lucy@example.com"),
        ExampleRecord(2, username="mia", email="mia@example.com"),
    ]
    sorted_queryset = sort_by_ordering(queryset, column=None, is_reverse=False)
    assert sorted_queryset == [
        ExampleRecord(0, username="tom", email="tom@example.com"),
        ExampleRecord(1, username="lucy", email="lucy@example.com"),
        ExampleRecord(2, username="mia", email="mia@example.com"),
    ]


def test_get_column_controls_no_current_selection():
    columns = {"username": "Username", "email": "Email"}
    url = URL("/")
    column, is_reverse = None, False

    controls = get_column_controls(url, columns, selected_column=None, is_reverse=False)

    assert controls == [
        ColumnControl(
            id="username",
            text="Username",
            url=URL("/?order=username"),
            is_forward_sorted=False,
            is_reverse_sorted=False,
        ),
        ColumnControl(
            id="email",
            text="Email",
            url=URL("/?order=email"),
            is_forward_sorted=False,
            is_reverse_sorted=False,
        ),
    ]


def test_get_column_controls_forward_current_selection():
    columns = {"username": "Username", "email": "Email"}
    url = URL("/?order=username")
    column, is_reverse = "username", False

    controls = get_column_controls(
        url, columns, selected_column="username", is_reverse=False
    )

    assert controls == [
        ColumnControl(
            id="username",
            text="Username",
            url=URL("/?order=-username"),
            is_forward_sorted=True,
            is_reverse_sorted=False,
        ),
        ColumnControl(
            id="email",
            text="Email",
            url=URL("/?order=email"),
            is_forward_sorted=False,
            is_reverse_sorted=False,
        ),
    ]


def test_get_column_controls_reverse_current_selection():
    columns = {"username": "Username", "email": "Email"}
    url = URL("/?order=-username")
    column, is_reverse = "username", True

    controls = get_column_controls(
        url=url, columns=columns, selected_column=column, is_reverse=is_reverse
    )

    assert controls == [
        ColumnControl(
            id="username",
            text="Username",
            url=URL("/"),
            is_forward_sorted=False,
            is_reverse_sorted=True,
        ),
        ColumnControl(
            id="email",
            text="Email",
            url=URL("/?order=email"),
            is_forward_sorted=False,
            is_reverse_sorted=False,
        ),
    ]
