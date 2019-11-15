from source.app import app
from starlette.datastructures import URL
from tests.client import TestClient
import pytest
import tempfile


@pytest.fixture
async def row_uuid(client):
    # This is a bit of a fudge. Because we're using a sync client & test cases
    # we can't easily query the database using our async APIs.
    # We need to determine a valid row UUID for a bunch of our test cases,
    # so we do so by making a table page request, and inspecting the returned
    # context.
    url = app.url_path_for("table", table_id="uk-general-election-2017")
    response = await client.get(url)
    assert response.status_code == 200
    return response.context["queryset"][0].uuid


@pytest.fixture
def mock_csv():
    csv = tempfile.NamedTemporaryFile()
    csv.write(b"name,score\n")
    csv.write(b"tom,123\n")
    csv.write(b"lucy,456\n")
    csv.write(b"rose,789\n")
    csv.seek(0)
    return csv


@pytest.mark.asyncio
async def test_dashboard(client):
    """
    Ensure that the dashboard renders the 'dashboard.html' template.
    """
    url = app.url_path_for("dashboard")
    response = await client.get(url)
    assert response.status_code == 200
    assert response.template.name == "dashboard.html"


@pytest.mark.asyncio
async def test_table(client):
    """
    Ensure that the tabular results render the 'table.html' template.
    """
    url = app.url_path_for("table", table_id="uk-general-election-2017")
    response = await client.get(url)
    assert response.status_code == 200
    assert response.template.name == "table.html"


@pytest.mark.asyncio
async def test_columns(client):
    """
    Ensure that the tabular column results render the 'columns.html' template.
    """
    url = app.url_path_for("columns", table_id="uk-general-election-2017")
    response = await client.get(url)
    assert response.status_code == 200
    assert response.template.name == "columns.html"


@pytest.mark.asyncio
async def test_detail(client, row_uuid):
    """
    Ensure that the detail pages renders the 'detail.html' template.
    """
    url = app.url_path_for(
        "detail", table_id="uk-general-election-2017", row_uuid=row_uuid
    )
    response = await client.get(url)
    assert response.status_code == 200
    assert response.template.name == "detail.html"


# Table actions from a user profile


@pytest.mark.asyncio
async def test_invalid_user_create_table(auth_client):
    url = app.url_path_for("profile", username="tomchristie")
    data = {"name": ""}
    response = await auth_client.post(url, data=data, allow_redirects=False)
    expected_redirect = url

    assert response.status_code == 400
    assert response.context["form_errors"]["name"] == "Must not be blank."


@pytest.mark.asyncio
async def test_invalid_user_create_duplicate_table(auth_client):
    url = app.url_path_for("profile", username="tomchristie")
    data = {"name": "UK General Election 2017"}
    response = await auth_client.post(url, data=data, allow_redirects=False)
    expected_redirect = url

    assert response.status_code == 400
    assert (
        response.context["form_errors"]["name"]
        == "A table with this name already exists."
    )


@pytest.mark.asyncio
async def test_valid_user_create_table(auth_client):
    url = app.url_path_for("profile", username="tomchristie")
    data = {"name": "A new table"}
    response = await auth_client.post(url, data=data, allow_redirects=False)
    expected_redirect = url

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect

    url = app.url_path_for("profile", username="tomchristie")
    response = await auth_client.get(url)
    assert response.status_code == 200
    assert len(response.context["rows"]) == 1


# Actions


@pytest.mark.asyncio
async def test_invalid_create_table(client):
    url = app.url_path_for("dashboard")
    data = {"name": ""}
    response = await client.post(url, data=data, allow_redirects=False)
    expected_redirect = url

    assert response.status_code == 400
    assert response.context["form_errors"]["name"] == "Must not be blank."


@pytest.mark.asyncio
async def test_invalid_create_duplicate_table(client):
    url = app.url_path_for("dashboard")
    data = {"name": "UK General Election 2017"}
    response = await client.post(url, data=data, allow_redirects=False)
    expected_redirect = url

    assert response.status_code == 400
    assert (
        response.context["form_errors"]["name"]
        == "A table with this name already exists."
    )


@pytest.mark.asyncio
async def test_valid_create_table(client):
    url = app.url_path_for("dashboard")
    data = {"name": "A new table"}
    response = await client.post(url, data=data, allow_redirects=False)
    expected_redirect = url

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


@pytest.mark.asyncio
async def test_invalid_create_column(client):
    url = app.url_path_for("columns", table_id="uk-general-election-2017")
    data = {"name": "", "datatype": "nonsense"}
    response = await client.post(url, data=data, allow_redirects=False)
    expected_redirect = url

    assert response.status_code == 400
    assert response.context["form_errors"]["name"] == "Must not be blank."
    assert response.context["form_errors"]["datatype"] == "Not a valid choice."


@pytest.mark.asyncio
async def test_invalid_create_duplicate_column(client):
    url = app.url_path_for("columns", table_id="uk-general-election-2017")
    data = {"name": "party", "datatype": "integer"}
    response = await client.post(url, data=data, allow_redirects=False)

    assert response.status_code == 400
    assert (
        response.context["form_errors"]["name"]
        == "A column with this name already exists."
    )


@pytest.mark.asyncio
async def test_valid_create_column(client):
    url = app.url_path_for("columns", table_id="uk-general-election-2017")
    data = {"name": "notes", "datatype": "string"}
    response = await client.post(url, data=data, allow_redirects=False)
    expected_redirect = url

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


@pytest.mark.asyncio
async def test_invalid_create(client):
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
    response = await client.post(url, data=data, allow_redirects=False)

    assert response.status_code == 400
    assert response.context["form_errors"]["constituency"] == "Must not be blank."


@pytest.mark.asyncio
async def test_valid_create(client):
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
    response = await client.post(url, data=data, allow_redirects=False)
    expected_redirect = app.url_path_for("table", table_id="uk-general-election-2017")

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


@pytest.mark.asyncio
async def test_invalid_edit(client, row_uuid):
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
    response = await client.post(url, data=data, allow_redirects=False)

    assert response.status_code == 400
    assert response.context["form_errors"]["constituency"] == "Must not be blank."


@pytest.mark.asyncio
async def test_valid_edit(client, row_uuid):
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
    response = await client.post(url, data=data, allow_redirects=False)
    expected_redirect = url

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


@pytest.mark.asyncio
async def test_column_delete(client, row_uuid):
    """
    Test column deletion.
    """
    url = app.url_path_for(
        "delete-column", table_id="uk-general-election-2017", column_id="party"
    )
    response = await client.post(url, allow_redirects=False)
    expected_redirect = app.url_path_for("columns", table_id="uk-general-election-2017")

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


@pytest.mark.asyncio
async def test_table_delete(client, row_uuid):
    """
    Test table delete.
    """
    url = app.url_path_for("delete-table", table_id="uk-general-election-2017")
    response = await client.post(url, allow_redirects=False)
    expected_redirect = app.url_path_for("dashboard")

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


@pytest.mark.asyncio
async def test_delete(client, row_uuid):
    """
    Test row delete.
    """
    url = app.url_path_for(
        "delete-row", table_id="uk-general-election-2017", row_uuid=row_uuid
    )
    response = await client.post(url, allow_redirects=False)
    expected_redirect = app.url_path_for("table", table_id="uk-general-election-2017")

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


@pytest.mark.asyncio
async def test_upload(client, mock_csv):
    url = app.url_path_for("dashboard")
    data = {"name": "new table"}
    response = await client.post(url, data=data, allow_redirects=False)
    expected_redirect = url

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect

    url = app.url_path_for("upload", table_id="new-table")
    response = await client.post(
        url, files={"upload-file": mock_csv.name}, allow_redirects=False
    )
    expected_redirect = app.url_path_for("table", table_id="new-table")

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


# Filters


@pytest.mark.asyncio
async def test_table_with_ordering(client):
    """
    Ensure that a column ordering renders a sorted 'table.html' template.
    """
    url = (
        app.url_path_for("table", table_id="uk-general-election-2017") + "?order=votes"
    )
    response = await client.get(url)
    template_queryset = response.context["queryset"]
    rendered_votes = [item["votes"] for item in template_queryset]

    assert response.status_code == 200
    assert response.template.name == "table.html"
    assert rendered_votes == sorted(rendered_votes)


@pytest.mark.asyncio
async def test_table_with_search(client):
    """
    Ensure that a column ordering renders a sorted 'table.html' template.
    """
    url = (
        app.url_path_for("table", table_id="uk-general-election-2017")
        + "?search=tatton"
    )
    response = await client.get(url)
    template_queryset = response.context["queryset"]
    rendered_constituency = [item["constituency"] for item in template_queryset]

    assert response.status_code == 200
    assert response.template.name == "table.html"
    assert all([constituency == "Tatton" for constituency in rendered_constituency])


# Error handler cases


@pytest.mark.asyncio
async def test_table_404(client):
    """
    Ensure that tabular pages with an invalid year render the '404.html' template.
    """
    url = app.url_path_for("table", table_id="does-not-exist")
    response = await client.get(url)
    assert response.status_code == 404
    assert response.template.name == "404.html"


@pytest.mark.asyncio
async def test_detail_404(client):
    """
    Ensure that detail pages with an invalid PK render the '404.html' template.
    """
    url = app.url_path_for(
        "detail", table_id="uk-general-election-2017", row_uuid="does-not-exist"
    )
    response = await client.get(url)
    assert response.status_code == 404
    assert response.template.name == "404.html"


@pytest.mark.asyncio
async def test_delete_404(client):
    """
    Ensure that delete pages with an invalid PK render the '404.html' template.
    """
    url = app.url_path_for(
        "delete-row", table_id="uk-general-election-2017", row_uuid="does-not-exist"
    )
    response = await client.post(url)
    assert response.status_code == 404
    assert response.template.name == "404.html"


@pytest.mark.asyncio
async def test_column_delete_404(client):
    """
    Ensure that column delete pages with an invalid PK render the '404.html' template.
    """
    url = app.url_path_for(
        "delete-column", table_id="uk-general-election-2017", column_id="does-not-exist"
    )
    response = await client.post(url)
    assert response.status_code == 404
    assert response.template.name == "404.html"


@pytest.mark.asyncio
async def test_404_not_found(client):
    """
    Ensure that unrouted URLs render the '404.html' template.
    """
    response = await client.get("/404")  # This URL does not exist in the application.
    assert response.status_code == 404
    assert response.template.name == "404.html"


@pytest.mark.asyncio
async def test_500_server_error():
    """
    Ensure that exceptions in the application render the '500.html' template.
    """
    client = TestClient(app, raise_server_exceptions=False)
    response = await client.get("/500")  # This URL raises a deliberate exception.
    assert response.status_code == 500
    assert response.template.name == "500.html"
