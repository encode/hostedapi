from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.responses import HTMLResponse, RedirectResponse
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from source import settings, pagination, ordering, search, tables
from source.resources import database, statics, templates
from source.datasource import ElectionDataSource
import databases
import math
import typesystem


app = Starlette(debug=settings.DEBUG)

if settings.SENTRY_DSN:  # pragma: nocover
    app.add_middleware(SentryAsgiMiddleware)

app.mount("/static", statics, name="static")


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


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

    year = request.path_params["year"]
    if year not in (2017, 2015):
        raise HTTPException(status_code=404)

    datasource = ElectionDataSource(app=app, year=year)
    columns = {key: field.title for key, field in datasource.schema.fields.items()}

    # Get some normalised information from URL query parameters
    current_page = pagination.get_page_number(url=request.url)
    order_column, is_reverse = ordering.get_ordering(url=request.url, columns=columns)
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
        url=request.url,
        columns=columns,
        selected_column=order_column,
        is_reverse=is_reverse,
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
        "schema": datasource.schema,
        "table_name": datasource.name,
        "table_url": datasource.url,
        "queryset": queryset,
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
            await item.update(values=validated_data)
            return RedirectResponse(url=request.url, status_code=303)
        status_code = 400
    else:
        form_values = (
            None if item is None else datasource.schema.make_validator().serialize(item)
        )
        form_errors = None
        status_code = 200

    # Render the page
    template = "detail.html"
    context = {
        "request": request,
        "schema": datasource.schema,
        "table_name": datasource.name,
        "table_url": datasource.url,
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

    await item.delete()
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
