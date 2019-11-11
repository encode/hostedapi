from starlette.routing import Route
from source.mock_github import endpoints


routes = [
    # Site Routes mocking out `https://github.com`
    Route("/login/oauth/authorize", endpoint=endpoints.authorize, name="authorize"),
    Route(
        "/login/oauth/access_token", endpoint=endpoints.access_token, methods=["POST"]
    ),
    #  API Routes mocking out `https://api.github.com"`
    Route("/user", endpoint=endpoints.user),
]
