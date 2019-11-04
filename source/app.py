from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.middleware import Middleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from source import endpoints, settings
from source.resources import database, statics, templates


routes = [
    Route("/", endpoints.dashboard, name="dashboard", methods=["GET", "POST"]),
    Route("/tables/{table_id}", endpoints.table, methods=["GET", "POST"], name="table"),
    Route(
        "/tables/{table_id}/columns",
        endpoints.columns,
        methods=["GET", "POST"],
        name="columns",
    ),
    Route(
        "/tables/{table_id}/delete",
        endpoints.delete_table,
        methods=["POST"],
        name="delete-table",
    ),
    Route(
        "/tables/{table_id}/upload", endpoints.upload, methods=["POST"], name="upload"
    ),
    Route(
        "/tables/{table_id}/columns/{column_id}/delete",
        endpoints.delete_column,
        methods=["POST"],
        name="delete-column",
    ),
    Route(
        "/tables/{table_id}/{row_uuid}",
        endpoints.detail,
        methods=["GET", "POST"],
        name="detail",
    ),
    Route(
        "/tables/{table_id}/{row_uuid}/delete",
        endpoints.delete_row,
        methods=["POST"],
        name="delete-row",
    ),
    Route("/500", endpoints.error),
    Mount("/static", statics, name="static"),
]

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
    on_shutdown=[database.disconnect]
)
