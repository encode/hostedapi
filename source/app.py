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


class ElectionDataSource:
    def __init__(self, app, year):
        self.name = f"UK General Election Results {year}"
        self.url = app.url_path_for("table", year=year)
        self.year = year
        self.clauses = []
        self.order_column = None
        self.query_limit = None
        self.query_offset = None

    def apply_query_filters(self, query):
        query = query.where(tables.election.c.year == self.year)

        for clause in self.clauses:
            query = query.where(clause)

        if self.query_limit is not None:
            query = query.limit(self.query_limit)

        if self.query_offset is not None:
            query = query.offset(self.query_offset)

        if self.order_column is not None:
            query = query.group_by(tables.election.c.pk).order_by(
                self.order_column, tables.election.c.pk
            )
        return query

    def limit(self, limit):
        self.query_limit = limit
        return self

    def offset(self, offset):
        self.query_offset = offset
        return self

    def search(self, search_term):
        if not search_term:
            return self

        match = f"%{search_term}%"
        self.clauses.append(
            (
                tables.election.c.constituency.ilike(match)
                | tables.election.c.surname.ilike(match)
                | tables.election.c.first_name.ilike(match)
                | tables.election.c.party.ilike(match)
            )
        )
        return self

    def filter(self, pk=None):
        self.clauses.append(tables.election.c.pk == pk)
        return self

    def order_by(self, column, reverse):
        order_column = {
            "constituency": tables.election.c.constituency,
            "surname": tables.election.c.surname,
            "first_name": tables.election.c.first_name,
            "party": tables.election.c.party,
            "votes": tables.election.c.votes,
        }[column]
        self.order_column = order_column.desc() if reverse else order_column.asc()
        return self

    async def count(self):
        query = tables.election.count()
        query = self.apply_query_filters(query)
        return await database.fetch_val(query)

    async def all(self):
        query = tables.election.select()
        query = self.apply_query_filters(query)
        return await database.fetch_all(query)

    async def get(self):
        query = tables.election.select()
        query = self.apply_query_filters(query)
        return await database.fetch_one(query)

    async def create(self, values):
        values = dict(values)
        values["year"] = self.year
        query = tables.election.insert()
        return await database.execute(query, values=values)

    async def update(self, values):
        query = tables.election.update()
        query = self.apply_query_filters(query)
        return await database.execute(query, values=values)

    async def delete(self):
        query = tables.election.delete()
        query = self.apply_query_filters(query)
        return await database.execute(query)

    def validate(self, data):
        record, errors = Record.validate_or_error(data)
        validated_data = dict(record) if record is not None else None
        return validated_data, errors


@app.route("/", name="dashboard")
async def dashboard(request):
    rows = []

    datasources = [
        ElectionDataSource(app=app, year=2017),
        ElectionDataSource(app=app, year=2015),
    ]
    for datasource in datasources:
        text = datasource.name
        url = datasource.url
        count = await datasource.count()
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
    if year not in (2017, 2015):
        raise HTTPException(status_code=404)

    datasource = ElectionDataSource(app=app, year=year)

    # Get some normalised information from URL query parameters
    current_page = pagination.get_page_number(url=request.url)
    order_column, is_reverse = ordering.get_ordering(
        url=request.url, allowed_column_ids=ALLOWED_COLUMN_IDS
    )
    search_term = search.get_search_term(url=request.url)

    # Filter by any search term
    datasource = datasource.search(search_term)

    # Determine pagination info
    count = await datasource.count()
    total_pages = max(math.ceil(count / PAGE_SIZE), 1)
    current_page = max(min(current_page, total_pages), 1)
    offset = (current_page - 1) * PAGE_SIZE

    # Perform column ordering
    if order_column is not None:
        datasource = datasource.order_by(column=order_column, reverse=is_reverse)

    #  Perform pagination
    datasource = datasource.offset(offset).limit(PAGE_SIZE)
    queryset = await datasource.all()

    # Get pagination and column controls to render on the page
    column_controls = ordering.get_column_controls(
        url=request.url, names=COLUMN_NAMES, column=order_column, is_reverse=is_reverse
    )
    page_controls = pagination.get_page_controls(
        url=request.url, current_page=current_page, total_pages=total_pages
    )

    if request.method == "POST":
        form_values = await request.form()
        validated_data, form_errors = datasource.validate(form_values)
        if not form_errors:
            await datasource.create(values=validated_data)
            return RedirectResponse(url=request.url, status_code=303)
        status_code = 400
    else:
        form_values = None
        form_errors = None
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
        "form_errors": form_errors,
        "form_values": form_values,
    }
    return templates.TemplateResponse(template, context, status_code=status_code)


@app.route(
    "/uk-general-election-{year:int}/{pk:int}", methods=["GET", "POST"], name="detail"
)
async def detail(request):
    year = request.path_params["year"]
    pk = request.path_params["pk"]

    datasource = ElectionDataSource(app=app, year=year)
    datasource = datasource.filter(pk=pk)
    item = await datasource.get()

    if item is None:
        raise HTTPException(status_code=404)

    if request.method == "POST":
        form_values = await request.form()
        validated_data, form_errors = datasource.validate(form_values)
        if not form_errors:
            await datasource.update(values=validated_data)
            return RedirectResponse(url=request.url, status_code=303)
        status_code = 400
    else:
        form_values = None if item is None else dict(item)
        form_errors = None
        status_code = 200

    # Render the page
    template = "detail.html"
    context = {
        "request": request,
        "year": year,
        "pk": pk,
        "item": item,
        "form_values": form_values,
        "form_errors": form_errors,
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

    datasource = ElectionDataSource(app=app, year=year)
    datasource = datasource.filter(pk=pk)
    item = await datasource.get()

    if item is None:
        raise HTTPException(status_code=404)

    await datasource.delete()
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
