from source.app import app
from starlette.datastructures import URL
from starlette.testclient import TestClient
import pytest


@pytest.fixture
def row_uuid(client):
    # This is a bit of a fudge. Because we're using a sync client & test cases
    # we can't easily query the database using our async APIs.
    # We need to determine a valid row UUID for a bunch of our test cases,
    # so we do so by making a table page request, and inspecting the returned
    # context.
    url = app.url_path_for("table", table_id="uk-general-election-2017")
    response = client.get(url)
    assert response.status_code == 200
    return response.context["queryset"][0].uuid


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
    url = app.url_path_for("table", table_id="uk-general-election-2017")
    response = client.get(url)
    assert response.status_code == 200
    assert response.template.name == "table.html"


def test_columns(client):
    """
    Ensure that the tabular column results render the 'columns.html' template.
    """
    url = app.url_path_for("columns", table_id="uk-general-election-2017")
    response = client.get(url)
    assert response.status_code == 200
    assert response.template.name == "columns.html"


def test_detail(client, row_uuid):
    """
    Ensure that the detail pages renders the 'detail.html' template.
    """
    url = app.url_path_for(
        "detail", table_id="uk-general-election-2017", row_uuid=row_uuid
    )
    response = client.get(url)
    assert response.status_code == 200
    assert response.template.name == "detail.html"


# Actions


def test_invalid_create_table(client):
    url = app.url_path_for("dashboard")
    data = {"name": ""}
    response = client.post(url, data=data, allow_redirects=False)
    expected_redirect = url

    assert response.status_code == 400
    assert response.context["form_errors"]["name"] == "Must not be blank."


def test_invalid_create_duplicate_table(client):
    url = app.url_path_for("dashboard")
    data = {"name": "UK General Election 2017"}
    response = client.post(url, data=data, allow_redirects=False)
    expected_redirect = url

    assert response.status_code == 400
    assert (
        response.context["form_errors"]["name"]
        == "A table with this name already exists."
    )


def test_valid_create_table(client):
    url = app.url_path_for("dashboard")
    data = {"name": "A new table"}
    response = client.post(url, data=data, allow_redirects=False)
    expected_redirect = url

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


def test_invalid_create_column(client):
    url = app.url_path_for("columns", table_id="uk-general-election-2017")
    data = {"name": "", "datatype": "nonsense"}
    response = client.post(url, data=data, allow_redirects=False)
    expected_redirect = url

    assert response.status_code == 400
    assert response.context["form_errors"]["name"] == "Must not be blank."
    assert response.context["form_errors"]["datatype"] == "Not a valid choice."


def test_valid_create_column(client):
    url = app.url_path_for("columns", table_id="uk-general-election-2017")
    data = {"name": "notes", "datatype": "string"}
    response = client.post(url, data=data, allow_redirects=False)
    expected_redirect = url

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


def test_invalid_create(client):
    """
    Test an invalid row create.
    """
    url = app.url_path_for("table", table_id="uk-general-election-2017")
    data = {
        "constituency": "",
        "surname": "WALLACE",
        "first_name": "Donna Maria",
        "party": "Green Party",
        "votes": 1090,
    }
    response = client.post(url, data=data, allow_redirects=False)

    assert response.status_code == 400
    assert response.context["form_errors"]["constituency"] == "Must not be blank."


def test_valid_create(client):
    """
    Test an valid row create.
    """
    url = app.url_path_for("table", table_id="uk-general-election-2017")
    data = {
        "constituency": "Aldershot",
        "surname": "WALLACE",
        "first_name": "Donna Maria",
        "party": "Green Party",
        "votes": 1090,
    }
    response = client.post(url, data=data, allow_redirects=False)
    expected_redirect = app.url_path_for("table", table_id="uk-general-election-2017")

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


def test_invalid_edit(client, row_uuid):
    """
    Test an invalid row edit.
    """
    url = app.url_path_for(
        "detail", table_id="uk-general-election-2017", row_uuid=row_uuid
    )
    data = {
        "constituency": "",
        "surname": "WALLACE",
        "first_name": "Donna Maria",
        "party": "Green Party",
        "votes": 1090,
    }
    response = client.post(url, data=data, allow_redirects=False)

    assert response.status_code == 400
    assert response.context["form_errors"]["constituency"] == "Must not be blank."


def test_valid_edit(client, row_uuid):
    """
    Test row edit.
    """
    url = app.url_path_for(
        "detail", table_id="uk-general-election-2017", row_uuid=row_uuid
    )
    data = {
        "constituency": "Aldershot",
        "surname": "WALLACE",
        "first_name": "Donna Maria",
        "party": "Green Party",
        "votes": 1090,
    }
    response = client.post(url, data=data, allow_redirects=False)
    expected_redirect = url

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


def test_delete(client, row_uuid):
    """
    Test row delete.
    """
    url = app.url_path_for(
        "delete-row", table_id="uk-general-election-2017", row_uuid=row_uuid
    )
    response = client.post(url, allow_redirects=False)
    expected_redirect = app.url_path_for("table", table_id="uk-general-election-2017")

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


# Filters


def test_table_with_ordering(client):
    """
    Ensure that a column ordering renders a sorted 'table.html' template.
    """
    url = (
        app.url_path_for("table", table_id="uk-general-election-2017") + "?order=votes"
    )
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
    url = (
        app.url_path_for("table", table_id="uk-general-election-2017")
        + "?search=tatton"
    )
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
    url = app.url_path_for("table", table_id="does-not-exist")
    response = client.get(url)
    assert response.status_code == 404
    assert response.template.name == "404.html"


def test_detail_404(client):
    """
    Ensure that detail pages with an invalid PK render the '404.html' template.
    """
    url = app.url_path_for(
        "detail", table_id="uk-general-election-2017", row_uuid="does-not-exist"
    )
    response = client.get(url)
    assert response.status_code == 404
    assert response.template.name == "404.html"


def test_delete_404(client):
    """
    Ensure that delete pages with an invalid PK render the '404.html' template.
    """
    url = app.url_path_for(
        "delete-row", table_id="uk-general-election-2017", row_uuid="does-not-exist"
    )
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
