from starlette.responses import RedirectResponse
from starlette.datastructures import URL
from source import settings


async def login(request):
    from source.app import GITHUB_AUTH_URL

    query = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "scope": "user:email",
        "redirect_url": request.url_for("auth:callback"),
    }
    url = URL(GITHUB_AUTH_URL).include_query_params(**query)
    return RedirectResponse(url, status_code=303)


async def logout(request):
    request.session.clear()
    url = request.url_for("dashboard")
    return RedirectResponse(url, status_code=303)


async def callback(request):
    from source.app import github_client, github_api_client

    # Obtain an access token.
    code = request.query_params.get("code", "")
    url = "/login/oauth/access_token"
    data = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "client_secret": settings.GITHUB_CLIENT_SECRET,
        "code": code,
    }
    headers = {"accept": "application/json"}
    response = await github_client.post(url, data=data, headers=headers)
    response.raise_for_status()
    data = response.json()

    #  Make a request to the API.
    url = "/user"
    headers = {
        "authorization": f'token {data["access_token"]}',
    }
    response = await github_api_client.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    # Log the user in, and redirect back to the homepage.
    request.session["username"] = data["login"]
    request.session["avatar_url"] = data["avatar_url"]
    url = request.url_for("dashboard")
    return RedirectResponse(url, status_code=303)
