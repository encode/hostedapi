from starlette.applications import Starlette
from starlette.routing import Router, Route, Mount
from starlette.middleware import Middleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from source import endpoints, settings
from source.resources import database, statics, templates
from source.auth.routes import routes as auth_routes
from source.mock_github.routes import routes as github_routes
import httpx


# fmt: off
routes = [
    Route("/", endpoints.dashboard, name="dashboard", methods=["GET", "POST"]),
    Route("/tables/{table_id}", endpoints.table, name="table", methods=["GET", "POST"]),
    Route("/tables/{table_id}/columns", endpoints.columns, name="columns", methods=["GET", "POST"]),
    Route("/tables/{table_id}/delete", endpoints.delete_table, name="delete-table", methods=["POST"]),
    Route("/tables/{table_id}/upload", endpoints.upload, name="upload", methods=["POST"]),
    Route("/tables/{table_id}/columns/{column_id}/delete", endpoints.delete_column, name="delete-column", methods=["POST"]),
    Route("/tables/{table_id}/{row_uuid}", endpoints.detail, name="detail", methods=["GET", "POST"]),
    Route("/tables/{table_id}/{row_uuid}/delete", endpoints.delete_row, name="delete-row", methods=["POST"]),
    Route("/500", endpoints.error),
    Mount("/static", statics, name="static"),
    Mount("/auth", routes=auth_routes, name='auth'),
]

if settings.MOCK_GITHUB:
    routes += [
        Mount("/mock_github", routes=github_routes, name='mock_github')
    ]
    github_client = httpx.AsyncClient(
        base_url='http://mock',
        app=Router(routes=github_routes)
    )
    github_api_client = httpx.AsyncClient(
        base_url='http://mock',
        app=Router(routes=github_routes)
    )
    GITHUB_AUTH_URL = '/mock_github/login/oauth/authorize'

else:  # pragma: nocover
    github_client = httpx.AsyncClient(base_url='https://github.com/')
    github_api_client = httpx.AsyncClient(
        base_url='https://api.github.com/',
        headers={'accept': 'application/vnd.github.v3+json'}
    )
    GITHUB_AUTH_URL = 'https://github.com/login/oauth/authorize'


middleware = [
    Middleware(SentryAsgiMiddleware, enabled=settings.SENTRY_DSN),
    Middleware(HTTPSRedirectMiddleware, enabled=settings.HTTPS_ONLY),
    Middleware(SessionMiddleware, options={
        'secret_key': settings.SECRET, 'https_only': settings.HTTPS_ONLY
    })
]

exception_handlers = {
    404: endpoints.not_found,
    500: endpoints.server_error,
}

app = Starlette(
    debug=settings.DEBUG,
    routes=routes,
    middleware=middleware,
    exception_handlers=exception_handlers,
    on_startup=[database.connect],
    on_shutdown=[database.disconnect],
)
