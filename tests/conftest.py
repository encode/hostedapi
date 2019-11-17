import pytest
import httpx
from alembic import command
from alembic.config import Config
from starlette.config import environ
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database, drop_database
from tests.client import TestClient

# This sets `os.environ`, but provides some additional protection.
# If we placed it below the application import, it would raise an error
# informing us that 'TESTING' had already been read from the environment.
environ["TESTING"] = "True"
environ["MOCK_GITHUB"] = "True"
environ["SECRET"] = "TESTING"


@pytest.fixture(scope="session", autouse=True)
def create_test_database():
    """
    Create a clean database on every test case.
    For safety, we should abort if a database already exists.

    We use the `sqlalchemy_utils` package here for a few helpers in consistently
    creating and dropping the database.
    """
    from source import settings

    url = str(settings.TEST_DATABASE_URL)
    engine = create_engine(url)
    assert not database_exists(url), "Test database already exists. Aborting tests."
    create_database(url)  # Create the test database.
    config = Config("alembic.ini")  # Run the migrations.
    command.upgrade(config, "head")
    yield  # Run the tests.
    drop_database(url)  # Drop the test database.


@pytest.fixture()
async def client():
    """
    When using the 'client' fixture in test cases, we'll get full database
    rollbacks between test cases:

    def test_homepage(client):
        url = app.url_path_for('homepage')
        response = client.get(url)
        assert response.status_code == 200
    """
    from source.app import app
    from source.resources import database

    await database.connect()
    try:
        yield TestClient(app=app)
    finally:
        await database.disconnect()


@pytest.fixture()
async def auth_client():
    from source.app import app
    from source.resources import database

    await database.connect()
    try:
        client = TestClient(app=app)

        # A POST /auth/login should redirect to the github auth URL.
        url = app.url_path_for("auth:login")
        response = await client.post(url, allow_redirects=True)
        assert response.status_code == 200
        assert response.template.name == "mock_github/authorize.html"

        # Once the callback is made, the user should be authenticated, and end up on the homepage.
        url = app.url_path_for("auth:callback")
        response = await client.get(url)
        assert response.status_code == 200
        assert response.template.name == "profile.html"
        assert response.context["request"].session["username"] == "tomchristie"

        yield client
    finally:
        await database.disconnect()
