from starlette.applications import Starlette
from starlette.staticfiles import StaticFiles
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from source import settings
import sentry_sdk


if settings.SENTRY_DSN:  # pragma: nocover
    sentry_sdk.init(dsn=settings.SENTRY_DSN, release=settings.RELEASE_VERSION)


templates = Jinja2Templates(directory="templates")

app = Starlette(debug=settings.DEBUG)

if settings.SENTRY_DSN:  # pragma: nocover
    app.add_middleware(SentryAsgiMiddleware)

app.mount("/static", StaticFiles(directory="statics"), name="static")


class User:
    def __init__(self, pk, first, last, handle):
        self.pk = pk
        self.first = first
        self.last = last
        self.handle = handle


class ColumnControl:
    def __init__(self, text, url=None, is_sorted=False, is_reverse=False):
        self.text = text
        self.url = url
        self.is_sorted = is_sorted
        self.is_reverse = is_reverse


class PageControl:
    def __init__(self, text, url=None, is_active=False, is_disabled=False):
        self.text = text
        self.url = url
        self.is_active = is_active
        self.is_disabled = is_disabled


@app.route("/")
async def homepage(request):
    template = "table.html"
    context = {
        "request": request,
        "queryset": [
            User(pk=0, first="Mark", last="Otto", handle="@mdo"),
            User(pk=1, first="Jacob", last="Thornton", handle="@fat"),
            User(pk=2, first="Larry", last="The Bird", handle="@twitter"),
        ],
        "search_term": "",
        "column_controls": [
            ColumnControl(text="#"),
            ColumnControl(text="First", url="#"),
            ColumnControl(text="Last", url="#"),
            ColumnControl(text="Handle", url="#"),
        ],
        "page_controls": [
            PageControl(text="Previous", is_disabled=True),
            PageControl(text="1", is_active=True, url="#"),
            PageControl(text="2", url="#"),
            PageControl(text="3", url="#"),
            PageControl(text="Next", url="#"),
        ],
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
