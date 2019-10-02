from starlette.applications import Starlette
from starlette.staticfiles import StaticFiles
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from source import settings
import sentry_sdk
import uvicorn


if settings.SENTRY_DSN:
    sentry_sdk.init(dsn=settings.SENTRY_DSN)


templates = Jinja2Templates(directory="templates")

app = Starlette(debug=settings.DEBUG)

if settings.SENTRY_DSN:
    app.add_middleware(SentryAsgiMiddleware)

app.mount("/static", StaticFiles(directory="statics"), name="static")


@app.route("/")
async def homepage(request):
    template = "index.html"
    context = {"request": request}
    return templates.TemplateResponse(template, context)


@app.route("/error")
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