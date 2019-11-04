from starlette.applications import Starlette
from starlette.routing import Route, Mount
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

app = Starlette(debug=settings.DEBUG, routes=routes)

if settings.HTTPS_ONLY:  # pragma: nocover
    app.add_middleware(HTTPSRedirectMiddleware)

if settings.SENTRY_DSN:  # pragma: nocover
    app.add_middleware(SentryAsgiMiddleware)


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.exception_handler(404)
async def not_found(request, exc):
    """
    Return an HTTP 404 page.
    """
    template = "404.html"
    context = {"request": request}
    return templates.TemplateResponse(template, context, status_code=404)


@app.exception_handler(500)
async def server_error(request, exc):
    """
    Return an HTTP 500 page.
    """
    template = "500.html"
    context = {"request": request}
    return templates.TemplateResponse(template, context, status_code=500)
