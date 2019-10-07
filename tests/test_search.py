from source.search import get_search_term, filter_by_search_term
from starlette.datastructures import URL
from dataclasses import dataclass


def test_search_term():
    url = URL("/?search=foo+bar")
    search_term = get_search_term(url=url)
    assert search_term == "foo bar"


@dataclass
class ExampleRecord:
    pk: int
    username: str
    email: str

    def __getitem__(self, item):
        return getattr(self, item)


def test_filter_by_search_term():
    queryset = [
        ExampleRecord(0, username="tom", email="tom@example.com"),
        ExampleRecord(1, username="lucy", email="lucy@example.com"),
        ExampleRecord(2, username="mia", email="mia@example.com"),
    ]
    results = filter_by_search_term(queryset, "mia", attributes=["username", "email"])
    assert results == [ExampleRecord(2, username="mia", email="mia@example.com")]


def test_filter_by_no_search_term():
    queryset = [
        ExampleRecord(0, username="tom", email="tom@example.com"),
        ExampleRecord(1, username="lucy", email="lucy@example.com"),
        ExampleRecord(2, username="mia", email="mia@example.com"),
    ]
    results = filter_by_search_term(queryset, "", attributes=["username", "email"])
    assert results == [
        ExampleRecord(0, username="tom", email="tom@example.com"),
        ExampleRecord(1, username="lucy", email="lucy@example.com"),
        ExampleRecord(2, username="mia", email="mia@example.com"),
    ]
