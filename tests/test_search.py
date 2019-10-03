from source.search import get_search_term, filter_by_search_term
from starlette.datastructures import URL
from dataclasses import dataclass


def test_search_term():
    url = URL("/?search=foo+bar")
    search_term = get_search_term(url=url)
    assert search_term == "foo bar"


@dataclass
class ExampleItem:
    pk: int
    username: str
    email: str


def test_filter_by_search_term():
    queryset = [
        ExampleItem(0, username="tom", email="tom@example.com"),
        ExampleItem(1, username="lucy", email="lucy@example.com"),
        ExampleItem(2, username="mia", email="mia@example.com"),
    ]
    results = filter_by_search_term(queryset, "mia", attributes=["username", "email"])
    assert results == [ExampleItem(2, username="mia", email="mia@example.com")]


def test_filter_by_no_search_term():
    queryset = [
        ExampleItem(0, username="tom", email="tom@example.com"),
        ExampleItem(1, username="lucy", email="lucy@example.com"),
        ExampleItem(2, username="mia", email="mia@example.com"),
    ]
    results = filter_by_search_term(queryset, "", attributes=["username", "email"])
    assert results == [
        ExampleItem(0, username="tom", email="tom@example.com"),
        ExampleItem(1, username="lucy", email="lucy@example.com"),
        ExampleItem(2, username="mia", email="mia@example.com"),
    ]
