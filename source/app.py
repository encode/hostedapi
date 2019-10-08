from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from source import settings, pagination, ordering, search, tables
import databases
import sentry_sdk
import math
import typesystem


if settings.SENTRY_DSN:  # pragma: nocover
    sentry_sdk.init(dsn=settings.SENTRY_DSN, release=settings.RELEASE_VERSION)


templates = Jinja2Templates(directory="templates")

if settings.TESTING:
    database = databases.Database(settings.TEST_DATABASE_URL, force_rollback=True)
else:  # pragma: nocover
    database = databases.Database(settings.DATABASE_URL)

app = Starlette(debug=settings.DEBUG)

if settings.SENTRY_DSN:  # pragma: nocover
    app.add_middleware(SentryAsgiMiddleware)

app.mount("/static", StaticFiles(directory="statics"), name="static")


class Record(typesystem.Schema):
    constituency = typesystem.String(max_length=100)
    surname = typesystem.String(max_length=100)
    first_name = typesystem.String(max_length=100)
    party = typesystem.String(max_length=100)
    votes = typesystem.Integer(minimum=0)


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.route("/", name="dashboard")
async def dashboard(request):
    rows = []
    for year in (2017, 2015):
        text = f"UK General Election Results {year}"
        url = request.url_for("table", year=year)
        query = tables.election.count().where(tables.election.c.year == year)
        count = await database.fetch_val(query)
        rows.append({"text": text, "url": url, "count": count})

    template = "dashboard.html"
    context = {"request": request, "rows": rows}
    return templates.TemplateResponse(template, context)


@app.route("/uk-general-election-{year:int}", methods=["GET", "POST"], name="table")
async def table(request):
    PAGE_SIZE = 10
    COLUMN_NAMES = ("Constituency", "Surname", "First Name", "Party", "Votes")
    ALLOWED_COLUMN_IDS = ("constituency", "surname", "first_name", "party", "votes")

    year = request.path_params["year"]
    query = tables.election.select().where(tables.election.c.year == year)
    queryset = await database.fetch_all(query=query)
    if not queryset:
        raise HTTPException(status_code=404)

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

    if request.method == "POST":
        data = await request.form()
        record, error = Record.validate_or_error(data)
        if not error:
            query = tables.election.insert()
            values = dict(record)
            values["year"] = year
            await database.execute(query=query, values=values)
            return RedirectResponse(url=request.url, status_code=303)
        status_code = 400
    else:
        data = None
        error = None
        status_code = 200

    # Render the page
    template = "table.html"
    context = {
        "request": request,
        "queryset": queryset,
        "year": year,
        "search_term": search_term,
        "column_controls": column_controls,
        "page_controls": page_controls,
        "error": error,
        "data": data,
    }
    return templates.TemplateResponse(template, context, status_code=status_code)


@app.route(
    "/uk-general-election-{year:int}/{pk:int}", methods=["GET", "POST"], name="detail"
)
async def detail(request):
    year = request.path_params["year"]
    pk = request.path_params["pk"]
    query = tables.election.select().where(tables.election.c.pk == pk)
    item = await database.fetch_one(query=query)
    if item is None:
        raise HTTPException(status_code=404)

    if request.method == "POST":
        data = await request.form()
        record, error = Record.validate_or_error(data)
        if not error:
            query = tables.election.update().where(tables.election.c.pk == pk)
            values = dict(record)
            await database.execute(query=query, values=values)
            return RedirectResponse(url=request.url, status_code=303)
        status_code = 400
    else:
        data = item
        error = None
        status_code = 200

    # Render the page
    template = "detail.html"
    context = {
        "request": request,
        "year": year,
        "pk": pk,
        "item": item,
        "data": data,
        "error": error,
    }
    return templates.TemplateResponse(template, context, status_code=status_code)


@app.route(
    "/uk-general-election-{year:int}/{pk:int}/delete",
    methods=["POST"],
    name="delete-row",
)
async def delete_row(request):
    year = request.path_params["year"]
    pk = request.path_params["pk"]
    query = tables.election.select().where(tables.election.c.pk == pk)
    item = await database.fetch_one(query=query)
    if item is None:
        raise HTTPException(status_code=404)

    query = tables.election.delete().where(tables.election.c.pk == pk)
    await database.execute(query=query)
    url = request.url_for("table", year=year)
    return RedirectResponse(url=url, status_code=303)


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
