from source.app import app
from starlette.datastructures import URL
from starlette.testclient import TestClient


def test_dashboard(client):
    """
    Ensure that the dashboard renders the 'dashboard.html' template.
    """
    url = app.url_path_for("dashboard")
    response = client.get(url)
    assert response.status_code == 200
    assert response.template.name == "dashboard.html"


def test_table(client):
    """
    Ensure that the tabular results render the 'table.html' template.
    """
    url = app.url_path_for("table", year=2017)
    response = client.get(url)
    assert response.status_code == 200
    assert response.template.name == "table.html"


def test_detail(client):
    """
    Ensure that the detail pages renders the 'detail.html' template.
    """
    url = app.url_path_for("detail", year=2017, pk=1)
    response = client.get(url)
    assert response.status_code == 200
    assert response.template.name == "detail.html"


# Actions


def test_create(client):
    """
    Test row create.
    """
    url = app.url_path_for("table", year=2017)
    response = client.post(url, allow_redirects=False)
    expected_redirect = app.url_path_for("table", year=2017)

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


def test_edit(client):
    """
    Test row edit.
    """
    url = app.url_path_for("detail", year=2017, pk=1)
    response = client.post(url, allow_redirects=False)
    expected_redirect = url

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


def test_delete(client):
    """
    Test row delete.
    """
    url = app.url_path_for("delete-row", year=2017, pk=1)
    response = client.post(url, allow_redirects=False)
    expected_redirect = app.url_path_for("table", year=2017)

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


# Filters


def test_table_with_ordering(client):
    """
    Ensure that a column ordering renders a sorted 'table.html' template.
    """
    url = app.url_path_for("table", year=2017) + "?order=votes"
    response = client.get(url)
    template_queryset = response.context["queryset"]
    rendered_votes = [item["votes"] for item in template_queryset]

    assert response.status_code == 200
    assert response.template.name == "table.html"
    assert rendered_votes == sorted(rendered_votes)


def test_table_with_search(client):
    """
    Ensure that a column ordering renders a sorted 'table.html' template.
    """
    url = app.url_path_for("table", year=2017) + "?search=tatton"
    response = client.get(url)
    template_queryset = response.context["queryset"]
    rendered_constituency = [item["constituency"] for item in template_queryset]

    assert response.status_code == 200
    assert response.template.name == "table.html"
    assert all([constituency == "Tatton" for constituency in rendered_constituency])


# Error handler cases


def test_table_404(client):
    """
    Ensure that tabular pages with an invalid year render the '404.html' template.
    """
    url = app.url_path_for("table", year=999)
    response = client.get(url)
    assert response.status_code == 404
    assert response.template.name == "404.html"


def test_detail_404(client):
    """
    Ensure that detail pages with an invalid PK render the '404.html' template.
    """
    url = app.url_path_for("detail", year=2017, pk=99999)
    response = client.get(url)
    assert response.status_code == 404
    assert response.template.name == "404.html"


def test_delete_404(client):
    """
    Ensure that delete pages with an invalid PK render the '404.html' template.
    """
    url = app.url_path_for("delete-row", year=2017, pk=99999)
    response = client.post(url)
    assert response.status_code == 404
    assert response.template.name == "404.html"


def test_404_not_found(client):
    """
    Ensure that unrouted URLs render the '404.html' template.
    """
    response = client.get("/404")  # This URL does not exist in the application.
    assert response.status_code == 404
    assert response.template.name == "404.html"


def test_500_server_error():
    """
    Ensure that exceptions in the application render the '500.html' template.
    """
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/500")  # This URL raises a deliberate exception.
    assert response.status_code == 500
    assert response.template.name == "500.html"
