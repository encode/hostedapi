from starlette.applications import Starlette
from starlette.staticfiles import StaticFiles
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from source import datasource, settings, pagination
import sentry_sdk
import math


if settings.SENTRY_DSN:  # pragma: nocover
    sentry_sdk.init(dsn=settings.SENTRY_DSN, release=settings.RELEASE_VERSION)


templates = Jinja2Templates(directory="templates")

app = Starlette(debug=settings.DEBUG)

if settings.SENTRY_DSN:  # pragma: nocover
    app.add_middleware(SentryAsgiMiddleware)

app.mount("/static", StaticFiles(directory="statics"), name="static")


class ColumnControl:
    def __init__(self, text, url=None, is_sorted=False, is_reverse=False):
        self.text = text
        self.url = url
        self.is_sorted = is_sorted
        self.is_reverse = is_reverse


@app.route("/")
async def homepage(request):
    PAGE_SIZE = 20
    queryset = datasource.DATA_SOURCE_WITH_INDEX

    current_page = pagination.get_page_number(url=request.url)

    total_pages = max(math.ceil(len(queryset) / PAGE_SIZE), 1)
    current_page = max(min(current_page, total_pages), 1)

    offset = (current_page - 1) * PAGE_SIZE
    queryset = queryset[offset : offset + PAGE_SIZE]

    page_controls = pagination.get_page_controls(
        url=request.url, current_page=current_page, total_pages=total_pages
    )

    template = "table.html"
    context = {
        "request": request,
        "queryset": queryset,
        "search_term": "",
        "column_controls": [
            ColumnControl(text="#"),
            ColumnControl(text="Constituency", url="#"),
            ColumnControl(text="Surname", url="#"),
            ColumnControl(text="First name", url="#"),
            ColumnControl(text="Party", url="#"),
            ColumnControl(text="Votes", url="#"),
        ],
        "page_controls": page_controls,
    }
    return templates.TemplateResponse(template, context)


@app.route("/500")
async def error(request):
    """
    An example error. Switch the `debug` setting to see either tracebacks or 500 pages.
    """
    raise RuntimeError("Oh no")


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
