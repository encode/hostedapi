from source.app import app
import pytest


@pytest.mark.asyncio
async def test_login_flow(client):
    # Ensure the user is not logged in.
    url = app.url_path_for("dashboard")
    response = await client.get(url)
    assert response.status_code == 200
    assert response.template.name == "dashboard.html"
    assert "username" not in response.context["request"].session

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

    # A POST /auth/logout should unauthenticate the user and redirect to the homepage.
    url = app.url_path_for("auth:logout")
    response = await client.post(url, allow_redirects=True)

    assert response.template.name == "dashboard.html"
    assert "username" not in response.context["request"].session


@pytest.mark.asyncio
async def test_authenticated_login_flow(auth_client):
    # Ensure the user is logged in.
    url = app.url_path_for("dashboard")
    response = await auth_client.get(url)
    assert response.status_code == 200
    assert response.template.name == "dashboard.html"
    assert response.context["request"].session["username"] == "tomchristie"

    # A POST /auth/logout should unauthenticate the user and redirect to the homepage.
    url = app.url_path_for("auth:logout")
    response = await auth_client.post(url, allow_redirects=True)
    assert response.template.name == "dashboard.html"
    assert "username" not in response.context["request"].session

    # A POST /auth/login should redirect to the github auth URL.
    url = app.url_path_for("auth:login")
    response = await auth_client.post(url, allow_redirects=True)
    assert response.status_code == 200
    assert response.template.name == "mock_github/authorize.html"

    # Once the callback is made, the user should be authenticated, and end up on the homepage.
    url = app.url_path_for("auth:callback")
    response = await auth_client.get(url)
    assert response.status_code == 200
    assert response.template.name == "profile.html"
    assert response.context["request"].session["username"] == "tomchristie"
