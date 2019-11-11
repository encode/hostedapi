from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.middleware import Middleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from source import endpoints, settings
from source.resources import database, statics, templates


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
]
# fmt: on

middleware = [
    Middleware(SentryAsgiMiddleware, enabled=settings.SENTRY_DSN),
    Middleware(HTTPSRedirectMiddleware, enabled=settings.HTTPS_ONLY),
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
