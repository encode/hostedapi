from source.app import app
from starlette.testclient import TestClient


def test_homepage():
    """
    Ensure that the homepage renders the 'index.html' template.
    """
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.template.name == "table.html"


def test_404_not_found():
    """
    Ensure that unrouted URLs render the '404.html' template.
    """
    client = TestClient(app)
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
