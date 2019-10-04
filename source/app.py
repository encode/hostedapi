from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from source import datasource, settings, pagination, ordering, search
import sentry_sdk
import math


if settings.SENTRY_DSN:  # pragma: nocover
    sentry_sdk.init(dsn=settings.SENTRY_DSN, release=settings.RELEASE_VERSION)


templates = Jinja2Templates(directory="templates")

app = Starlette(debug=settings.DEBUG)

if settings.SENTRY_DSN:  # pragma: nocover
    app.add_middleware(SentryAsgiMiddleware)

app.mount("/static", StaticFiles(directory="statics"), name="static")


@app.route("/")
async def homepage(request):
    PAGE_SIZE = 10
    COLUMN_NAMES = ("Constituency", "Surname", "First Name", "Party", "Votes")
    ALLOWED_COLUMN_IDS = ("constituency", "surname", "first_name", "party", "votes")

    queryset = datasource.DATA_SOURCE_WITH_INDEX

    # Get some normalised information from URL query parameters
    current_page = pagination.get_page_number(url=request.url)
    order_column, is_reverse = ordering.get_ordering(
        url=request.url, allowed_column_ids=ALLOWED_COLUMN_IDS
    )
    search_term = search.get_search_term(url=request.url)

    # Filter by any search term
    queryset = search.filter_by_search_term(
        queryset, search_term=search_term, attributes=ALLOWED_COLUMN_IDS
    )

    # Determine pagination info
    total_pages = max(math.ceil(len(queryset) / PAGE_SIZE), 1)
    current_page = max(min(current_page, total_pages), 1)
    offset = (current_page - 1) * PAGE_SIZE

    # Perform column ordering
    queryset = ordering.sort_by_ordering(
        queryset, column=order_column, is_reverse=is_reverse
    )

    #  Perform pagination
    queryset = queryset[offset : offset + PAGE_SIZE]

    # Get pagination and column controls to render on the page
    column_controls = ordering.get_column_controls(
        url=request.url, names=COLUMN_NAMES, column=order_column, is_reverse=is_reverse
    )
    page_controls = pagination.get_page_controls(
        url=request.url, current_page=current_page, total_pages=total_pages
    )

    # Render the page
    template = "table.html"
    context = {
        "request": request,
        "queryset": queryset,
        "search_term": search_term,
        "column_controls": column_controls,
        "page_controls": page_controls,
    }
    return templates.TemplateResponse(template, context)


@app.route("/detail/{pk:int}", name="detail")
async def detail(request):
    queryset = datasource.DATA_SOURCE_WITH_INDEX
    try:
        item = queryset[request.path_params["pk"] - 1]
    except IndexError:
        raise HTTPException(status_code=404)

    # Render the page
    template = "detail.html"
    context = {"request": request, "item": item}
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
