from starlette.routing import Route
from source.auth import endpoints


routes = [
    Route("/login", endpoint=endpoints.login, methods=["POST"]),
    Route("/logout", endpoint=endpoints.logout, methods=["POST"]),
    Route("/callback", endpoint=endpoints.callback, methods=["GET"]),
]
