from source import tables
from source.app import app
from source.resources import database
from starlette.datastructures import URL
from tests.client import TestClient
import datetime
import pytest
import tempfile
import uuid


@pytest.fixture
def mock_csv():
    csv = tempfile.NamedTemporaryFile()
    csv.write(b"name,score\n")
    csv.write(b"tom,123\n")
    csv.write(b"lucy,456\n")
    csv.write(b"rose,789\n")
    csv.seek(0)
    return csv


async def create_user():
    query = tables.users.insert()
    user = {
        "created_at": datetime.datetime.now(),
        "last_login": datetime.datetime.now(),
        "github_id": 123,
        "username": "tomchristie",
        "is_admin": True,
        "name": "Tom Christie",
        "avatar_url": "http://example.com/avatar.jpg",
    }
    user["pk"] = await database.execute(query, user)
    return user


async def create_table(user):
    # Create the table.
    query = tables.table.insert()
    table = {
        "created_at": datetime.datetime.now(),
        "identity": "uk-general-election-2015",
        "name": "UK General Election 2015",
        "user_id": user["pk"],
    }
    table["pk"] = await database.execute(query, table)

    # Create the column layout.
    columns = [
        {
            "created_at": datetime.datetime.now(),
            "identity": "constituency",
            "name": "Constituency",
            "datatype": "string",
            "table": table["pk"],
            "position": 1,
        },
        {
            "created_at": datetime.datetime.now(),
            "identity": "surname",
            "name": "Surname",
            "datatype": "string",
            "table": table["pk"],
            "position": 2,
        },
        {
            "created_at": datetime.datetime.now(),
            "identity": "first_name",
            "name": "First Name",
            "datatype": "string",
            "table": table["pk"],
            "position": 3,
        },
        {
            "created_at": datetime.datetime.now(),
            "identity": "party",
            "name": "Party",
            "datatype": "string",
            "table": table["pk"],
            "position": 4,
        },
        {
            "created_at": datetime.datetime.now(),
            "identity": "votes",
            "name": "Votes",
            "datatype": "integer",
            "table": table["pk"],
            "position": 5,
        },
    ]
    query = tables.column.insert()
    await database.execute_many(query, columns)

    rows = [
        {
            "created_at": datetime.datetime.now(),
            "uuid": str(uuid.uuid4()),
            "table": table["pk"],
            "data": {
                "constituency": "Brighton, Pavilion",
                "surname": "LUCAS",
                "first_name": "Caroline",
                "party": "Green",
                "votes": 22871,
            },
            "search_text": "Brighton, Pavilion LUCAS Caroline Green",
        },
        {
            "created_at": datetime.datetime.now(),
            "uuid": str(uuid.uuid4()),
            "table": table["pk"],
            "data": {
                "constituency": "Brighton, Pavilion",
                "surname": "SEN",
                "first_name": "Purna",
                "party": "Labour",
                "votes": 14904,
            },
            "search_text": "Brighton, Pavilion SEN Purna Labour",
        },
        {
            "created_at": datetime.datetime.now(),
            "uuid": str(uuid.uuid4()),
            "table": table["pk"],
            "data": {
                "constituency": "Brighton, Pavilion",
                "surname": "MITCHELL",
                "first_name": "Clarence",
                "party": "Conservative",
                "votes": 12448,
            },
            "search_text": "Brighton, Pavilion MITCHELL Clarence Conservative",
        },
        {
            "created_at": datetime.datetime.now(),
            "uuid": str(uuid.uuid4()),
            "table": table["pk"],
            "data": {
                "constituency": "Brighton, Pavilion",
                "surname": "CARTER",
                "first_name": "Nigel",
                "party": "UK Independence Party",
                "votes": 2724,
            },
            "search_text": "Brighton, Pavilion CARTER Nigel UK Independence Party",
        },
        {
            "created_at": datetime.datetime.now(),
            "uuid": str(uuid.uuid4()),
            "table": table["pk"],
            "data": {
                "constituency": "Brighton, Pavilion",
                "surname": "BOWERS",
                "first_name": "Chris",
                "party": "Liberal Democrat",
                "votes": 1525,
            },
            "search_text": "Brighton, Pavilion BOWERS Chris Liberal Democrat",
        },
        {
            "created_at": datetime.datetime.now(),
            "uuid": str(uuid.uuid4()),
            "table": table["pk"],
            "data": {
                "constituency": "Brighton, Pavilion",
                "surname": "YEOMANS",
                "first_name": "Nick",
                "party": "Independent",
                "votes": 116,
            },
            "search_text": "Brighton, Pavilion YEOMANS Nick Independent",
        },
        {
            "created_at": datetime.datetime.now(),
            "uuid": str(uuid.uuid4()),
            "table": table["pk"],
            "data": {
                "constituency": "Brighton, Pavilion",
                "surname": "PILOTT",
                "first_name": "Howard",
                "party": "The Socialist Party of Great Britain",
                "votes": 88,
            },
            "search_text": "Brighton, Pavilion PILOTT Howard The Socialist Party of Great Britain",
        },
    ]
    query = tables.row.insert()
    await database.execute_many(query, rows)

    return table, columns, rows


@pytest.mark.asyncio
async def test_dashboard(client):
    """
    Ensure that the dashboard renders the 'dashboard.html' template.
    """
    user = await create_user()
    table, columns, rows = await create_table(user)

    url = app.url_path_for("dashboard")
    response = await client.get(url)

    assert response.status_code == 200
    assert response.template.name == "dashboard.html"


@pytest.mark.asyncio
async def test_table(client):
    """
    Ensure that the tabular results render the 'table.html' template.
    """
    user = await create_user()
    table, columns, rows = await create_table(user)

    url = app.url_path_for(
        "table", username=user["username"], table_id=table["identity"]
    )
    response = await client.get(url)

    assert response.status_code == 200
    assert response.template.name == "table.html"


@pytest.mark.asyncio
async def test_columns(client):
    """
    Ensure that the tabular column results render the 'columns.html' template.
    """
    user = await create_user()
    table, columns, rows = await create_table(user)

    url = app.url_path_for(
        "columns", username=user["username"], table_id=table["identity"]
    )
    response = await client.get(url)

    assert response.status_code == 200
    assert response.template.name == "columns.html"


@pytest.mark.asyncio
async def test_detail(client):
    """
    Ensure that the detail pages renders the 'detail.html' template.
    """
    user = await create_user()
    table, columns, rows = await create_table(user)

    url = app.url_path_for(
        "detail",
        username=user["username"],
        table_id=table["identity"],
        row_uuid=rows[0]["uuid"],
    )
    response = await client.get(url)

    assert response.status_code == 200
    assert response.template.name == "detail.html"


# Table actions from a user profile


# @pytest.mark.asyncio
# async def test_invalid_user_create_table(auth_client):
#     url = app.url_path_for("profile", username="tomchristie")
#     data = {"name": ""}
#     response = await auth_client.post(url, data=data, allow_redirects=False)
#     expected_redirect = url
#
#     assert response.status_code == 400
#     assert response.context["form_errors"]["name"] == "Must not be blank."
#
#
# @pytest.mark.asyncio
# async def test_invalid_user_create_duplicate_table(auth_client):
#     url = app.url_path_for("profile", username="tomchristie")
#     data = {"name": "UK General Election 2017"}
#     response = await auth_client.post(url, data=data, allow_redirects=False)
#     expected_redirect = url
#
#     assert response.status_code == 400
#     assert (
#         response.context["form_errors"]["name"]
#         == "A table with this name already exists."
#     )
#
#
# @pytest.mark.asyncio
# async def test_valid_user_create_table(auth_client):
#     url = app.url_path_for("profile", username="tomchristie")
#     data = {"name": "A new table"}
#     response = await auth_client.post(url, data=data, allow_redirects=False)
#     expected_redirect = url
#
#     assert response.is_redirect
#     assert URL(response.headers["location"]).path == expected_redirect
#
#     url = app.url_path_for("profile", username="tomchristie")
#     response = await auth_client.get(url)
#     assert response.status_code == 200
#     assert len(response.context["rows"]) == 1


# Actions


@pytest.mark.asyncio
async def test_invalid_create_table(client):
    user = await create_user()

    url = app.url_path_for("profile", username=user["username"])
    data = {"name": ""}
    response = await client.post(url, data=data)

    assert response.status_code == 400
    assert response.context["form_errors"]["name"] == "Must not be blank."


@pytest.mark.asyncio
async def test_invalid_create_duplicate_table(client):
    user = await create_user()
    table, columns, rows = await create_table(user)

    url = app.url_path_for("profile", username=user["username"])
    data = {"name": table["name"]}
    response = await client.post(url, data=data)

    assert response.status_code == 400
    assert (
        response.context["form_errors"]["name"]
        == "A table with this name already exists."
    )


@pytest.mark.asyncio
async def test_valid_create_table(client):
    user = await create_user()
    url = app.url_path_for("profile", username=user["username"])

    data = {"name": "A new table"}
    response = await client.post(url, data=data, allow_redirects=False)

    expected_redirect = url
    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


@pytest.mark.asyncio
async def test_invalid_create_column(client):
    user = await create_user()
    table, columns, rows = await create_table(user)

    url = app.url_path_for(
        "columns", username=user["username"], table_id=table["identity"]
    )
    data = {"name": "", "datatype": "nonsense"}
    response = await client.post(url, data=data)

    assert response.status_code == 400
    assert response.context["form_errors"]["name"] == "Must not be blank."
    assert response.context["form_errors"]["datatype"] == "Not a valid choice."


@pytest.mark.asyncio
async def test_invalid_create_duplicate_column(client):
    user = await create_user()
    table, columns, rows = await create_table(user)

    url = app.url_path_for(
        "columns", username=user["username"], table_id=table["identity"]
    )
    data = {"name": "party", "datatype": "integer"}
    response = await client.post(url, data=data)

    assert response.status_code == 400
    assert (
        response.context["form_errors"]["name"]
        == "A column with this name already exists."
    )


@pytest.mark.asyncio
async def test_valid_create_column(client):
    user = await create_user()
    table, columns, rows = await create_table(user)

    url = app.url_path_for(
        "columns", username=user["username"], table_id=table["identity"]
    )
    data = {"name": "notes", "datatype": "string"}
    response = await client.post(url, data=data, allow_redirects=False)
    expected_redirect = url

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


@pytest.mark.asyncio
async def test_invalid_row_create(client):
    """
    Test an invalid row create.
    """
    user = await create_user()
    table, columns, rows = await create_table(user)

    url = app.url_path_for(
        "table", username=user["username"], table_id=table["identity"]
    )
    data = {
        "constituency": "",
        "surname": "WALLACE",
        "first_name": "Emma",
        "party": "Green Party",
        "votes": 846,
    }
    response = await client.post(url, data=data)

    assert response.status_code == 400
    assert response.context["form_errors"]["constituency"] == "Must not be blank."


@pytest.mark.asyncio
async def test_valid_row_create(client):
    """
    Test an valid row create.
    """
    user = await create_user()
    table, columns, rows = await create_table(user)

    url = app.url_path_for(
        "table", username=user["username"], table_id=table["identity"]
    )
    data = {
        "constituency": "Harrow East",
        "surname": "WALLACE",
        "first_name": "Emma",
        "party": "Green Party",
        "votes": 846,
    }
    response = await client.post(url, data=data, allow_redirects=False)
    expected_redirect = url

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


@pytest.mark.asyncio
async def test_invalid_edit(client):
    """
    Test an invalid row edit.
    """
    user = await create_user()
    table, columns, rows = await create_table(user)

    url = app.url_path_for(
        "detail",
        username=user["username"],
        table_id=table["identity"],
        row_uuid=rows[0]["uuid"],
    )
    data = {
        "constituency": "",
        "surname": "WALLACE",
        "first_name": "Emma",
        "party": "Green Party",
        "votes": 846,
    }
    response = await client.post(url, data=data)

    assert response.status_code == 400
    assert response.context["form_errors"]["constituency"] == "Must not be blank."


@pytest.mark.asyncio
async def test_valid_edit(client):
    """
    Test row edit.
    """
    user = await create_user()
    table, columns, rows = await create_table(user)

    url = app.url_path_for(
        "detail",
        username=user["username"],
        table_id=table["identity"],
        row_uuid=rows[0]["uuid"],
    )
    data = {
        "constituency": "Harrow East",
        "surname": "WALLACE",
        "first_name": "Emma",
        "party": "Green Party",
        "votes": 846,
    }
    response = await client.post(url, data=data, allow_redirects=False)
    expected_redirect = url

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


@pytest.mark.asyncio
async def test_column_delete(client):
    """
    Test column deletion.
    """
    user = await create_user()
    table, columns, rows = await create_table(user)

    url = app.url_path_for(
        "delete-column",
        username=user["username"],
        table_id=table["identity"],
        column_id=columns[0]["identity"],
    )
    response = await client.post(url, allow_redirects=False)
    expected_redirect = app.url_path_for(
        "columns", username=user["username"], table_id=table["identity"]
    )

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


@pytest.mark.asyncio
async def test_table_delete(client):
    """
    Test table delete.
    """
    user = await create_user()
    table, columns, rows = await create_table(user)

    url = app.url_path_for(
        "delete-table", username=user["username"], table_id=table["identity"]
    )
    response = await client.post(url, allow_redirects=False)
    expected_redirect = app.url_path_for("profile", username=user["username"])

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


@pytest.mark.asyncio
async def test_delete(client):
    """
    Test row delete.
    """
    user = await create_user()
    table, columns, rows = await create_table(user)

    url = app.url_path_for(
        "delete-row",
        username=user["username"],
        table_id=table["identity"],
        row_uuid=rows[0]["uuid"],
    )
    response = await client.post(url, allow_redirects=False)
    expected_redirect = app.url_path_for(
        "table", username=user["username"], table_id=table["identity"]
    )

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


@pytest.mark.asyncio
async def test_upload(client, mock_csv):
    user = await create_user()
    csv_file = open(mock_csv.name, "r")

    url = app.url_path_for("profile", username=user["username"])
    data = {"name": "new table"}
    response = await client.post(url, data=data, allow_redirects=False)
    expected_redirect = url

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect

    url = app.url_path_for("upload", username=user["username"], table_id="new-table")
    response = await client.post(
        url, files={"upload-file": csv_file}, allow_redirects=False
    )
    expected_redirect = app.url_path_for(
        "table", username=user["username"], table_id="new-table"
    )

    assert response.is_redirect
    assert URL(response.headers["location"]).path == expected_redirect


# Filters


@pytest.mark.asyncio
async def test_table_with_ordering(client):
    """
    Ensure that a column ordering renders a sorted 'table.html' template.
    """
    user = await create_user()
    table, columns, rows = await create_table(user)

    url = (
        app.url_path_for("table", username=user["username"], table_id=table["identity"])
        + "?order=votes"
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
    user = await create_user()
    table, columns, rows = await create_table(user)

    url = (
        app.url_path_for("table", username=user["username"], table_id=table["identity"])
        + "?search=party"
    )
    response = await client.get(url)
    template_queryset = response.context["queryset"]
    rendered_party_names = [item["party"] for item in template_queryset]

    assert response.status_code == 200
    assert response.template.name == "table.html"
    assert all(["party" in party_name.lower() for party_name in rendered_party_names])


# Error handler cases


@pytest.mark.asyncio
async def test_table_404(client):
    """
    Ensure that tabular pages with an invalid year render the '404.html' template.
    """
    user = await create_user()

    url = app.url_path_for(
        "table", username=user["username"], table_id="does-not-exist"
    )
    response = await client.get(url)

    assert response.status_code == 404
    assert response.template.name == "404.html"


@pytest.mark.asyncio
async def test_detail_404(client):
    """
    Ensure that detail pages with an invalid PK render the '404.html' template.
    """
    user = await create_user()
    table, columns, rows = await create_table(user)

    url = app.url_path_for(
        "detail",
        username=user["username"],
        table_id=table["identity"],
        row_uuid="does-not-exist",
    )
    response = await client.get(url)

    assert response.status_code == 404
    assert response.template.name == "404.html"


@pytest.mark.asyncio
async def test_delete_404(client):
    """
    Ensure that delete pages with an invalid PK render the '404.html' template.
    """
    user = await create_user()
    table, columns, rows = await create_table(user)

    url = app.url_path_for(
        "delete-row",
        username=user["username"],
        table_id=table["identity"],
        row_uuid="does-not-exist",
    )
    response = await client.post(url)
    assert response.status_code == 404
    assert response.template.name == "404.html"


@pytest.mark.asyncio
async def test_column_delete_404(client):
    """
    Ensure that column delete pages with an invalid PK render the '404.html' template.
    """
    user = await create_user()
    table, columns, rows = await create_table(user)

    url = app.url_path_for(
        "delete-column",
        username=user["username"],
        table_id=table["identity"],
        column_id="does-not-exist",
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


@pytest.mark.asyncio
async def test_raise_500_server_error():
    """
    Ensure that exceptions in the application raise through the client.
    """
    client = TestClient(app)
    with pytest.raises(RuntimeError):
        await client.get("/500")
