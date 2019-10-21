from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.responses import HTMLResponse, RedirectResponse
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from source import settings, pagination, ordering, search, tables
from source.resources import database, statics, templates
from source.datasource import load_datasources, load_datasource_or_404
from slugify import slugify
import chardet
import csv
import datetime
import databases
import math
import typesystem
import uuid


app = Starlette(debug=settings.DEBUG)

if settings.SENTRY_DSN:  # pragma: nocover
    app.add_middleware(SentryAsgiMiddleware)

app.mount("/static", statics, name="static")


class NewTableSchema(typesystem.Schema):
    name = typesystem.String(max_length=100)


class NewColumnSchema(typesystem.Schema):
    name = typesystem.String(max_length=100)
    datatype = typesystem.Choice(choices=["string", "integer"])


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.route("/", name="dashboard", methods=["GET", "POST"])
async def dashboard(request):
    rows = []

    datasources = await load_datasources(app)

    for datasource in datasources:
        text = datasource.name
        url = datasource.url
        count = await datasource.count()
        rows.append({"text": text, "url": url, "count": count})

    if request.method == "POST":
        form_values = await request.form()
        validated_data, form_errors = NewTableSchema.validate_or_error(form_values)
        if not form_errors:
            identity = slugify(validated_data["name"], to_lower=True)
            query = tables.table.select().where(tables.table.c.identity == identity)
            table = await database.fetch_one(query)
            if table is not None:
                form_errors = {"name": "A table with this name already exists."}

        if not form_errors:
            insert_data = dict(validated_data)
            insert_data["created_at"] = datetime.datetime.now()
            insert_data["identity"] = slugify(insert_data["name"], to_lower=True)
            query = tables.table.insert()
            await database.execute(query, values=insert_data)
            return RedirectResponse(url=request.url, status_code=303)
        status_code = 400
    else:
        form_values = None
        form_errors = None
        status_code = 200

    template = "dashboard.html"
    context = {
        "request": request,
        "rows": rows,
        "form_values": form_values,
        "form_errors": form_errors,
    }
    return templates.TemplateResponse(template, context, status_code=status_code)


@app.route("/tables/{table_id}", methods=["GET", "POST"], name="table")
async def table(request):
    PAGE_SIZE = 10

    table_id = request.path_params["table_id"]
    datasource = await load_datasource_or_404(app, table_id)

    # datasource = ElectionDataSource(app=app, year=year)
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
        "table_id": table_id,
        "table_name": datasource.name,
        "table_url": datasource.url,
        "table_has_columns": bool(datasource.schema.fields),
        "table_has_rows": search_term or list(queryset),
        "queryset": queryset,
        "search_term": search_term,
        "column_controls": column_controls,
        "page_controls": page_controls,
        "form_errors": form_errors,
        "form_values": form_values,
    }
    return templates.TemplateResponse(template, context, status_code=status_code)


@app.route("/tables/{table_id}/columns", methods=["GET", "POST"], name="columns")
async def columns(request):
    table_id = request.path_params["table_id"]
    datasource = await load_datasource_or_404(app, table_id)

    if request.method == "POST":
        form_values = await request.form()
        validated_data, form_errors = NewColumnSchema.validate_or_error(form_values)
        if not form_errors:
            identity = slugify(validated_data["name"], to_lower=True)
            query = (
                tables.column.select()
                .where(tables.column.c.table == datasource.table["pk"])
                .where(tables.column.c.identity == identity)
            )
            column = await database.fetch_one(query)
            if column is not None:
                form_errors = {"name": "A column with this name already exists."}

        if not form_errors:
            position = (
                1 if not datasource.columns else datasource.columns[-1]["position"] + 1
            )
            insert_data = dict(validated_data)
            insert_data["table"] = datasource.table["pk"]
            insert_data["created_at"] = datetime.datetime.now()
            insert_data["identity"] = slugify(insert_data["name"], to_lower=True)
            insert_data["position"] = position
            query = tables.column.insert()
            await database.execute(query, values=insert_data)
            return RedirectResponse(url=request.url, status_code=303)
        status_code = 400
    else:
        form_values = None
        form_errors = None
        status_code = 200

    # Render the page
    template = "columns.html"
    context = {
        "request": request,
        "table_id": table_id,
        "table_name": datasource.name,
        "table_url": datasource.url,
        "columns": datasource.columns,
        "form_errors": form_errors,
        "form_values": form_values,
    }
    return templates.TemplateResponse(template, context, status_code=status_code)


@app.route("/tables/{table_id}/delete", methods=["POST"], name="delete-table")
async def delete_table(request):
    table_id = request.path_params["table_id"]
    datasource = await load_datasource_or_404(app, table_id)

    query = tables.column.delete().where(
        tables.column.c.table == datasource.table["pk"]
    )
    await database.execute(query)

    query = tables.row.delete().where(tables.row.c.table == datasource.table["pk"])
    await database.execute(query)

    query = tables.table.delete().where(tables.table.c.pk == datasource.table["pk"])
    await database.execute(query)

    url = request.url_for("dashboard")
    return RedirectResponse(url=url, status_code=303)


@app.route("/tables/{table_id}/upload", methods=["POST"], name="upload")
async def upload(request):
    table_id = request.path_params["table_id"]
    datasource = await load_datasource_or_404(app, table_id)

    form = await request.form()
    data = await form["upload-file"].read()
    encoding = chardet.detect(data)["encoding"]
    lines = data.decode(encoding).splitlines()
    rows = [row for row in csv.reader(lines)]
    column_idents = [slugify(name, to_lower=True) for name in rows[0]]

    column_insert_values = [
        {
            "created_at": datetime.datetime.now(),
            "name": name,
            "identity": slugify(name, to_lower=True),
            "datatype": "string",
            "table": datasource.table["pk"],
            "position": idx + 1,
        }
        for idx, name in enumerate(rows[0])
    ]

    query = tables.column.insert()
    await database.execute_many(query, column_insert_values)

    row_insert_values = [
        {
            "created_at": datetime.datetime.now(),
            "uuid": str(uuid.uuid4()),
            "table": datasource.table["pk"],
            "data": dict(zip(column_idents, row)),
            "search_text": " ".join(row),
        }
        for row in rows[1:]
    ]

    query = tables.row.insert()
    await database.execute_many(query, row_insert_values)

    url = request.url_for("table", table_id=table_id)
    return RedirectResponse(url=url, status_code=303)


@app.route(
    "/tables/{table_id}/columns/{column_id}/delete",
    methods=["POST"],
    name="delete-column",
)
async def delete_column(request):
    table_id = request.path_params["table_id"]
    column_id = request.path_params["column_id"]
    datasource = await load_datasource_or_404(app, table_id)
    if column_id not in datasource.schema.fields:
        raise HTTPException(status_code=404)

    query = (
        tables.column.delete()
        .where(tables.column.c.table == datasource.table["pk"])
        .where(tables.column.c.identity == column_id)
    )
    await database.execute(query)
    url = request.url_for("columns", table_id=table_id)
    return RedirectResponse(url=url, status_code=303)


@app.route("/tables/{table_id}/{row_uuid}", methods=["GET", "POST"], name="detail")
async def detail(request):
    table_id = request.path_params["table_id"]
    row_uuid = request.path_params["row_uuid"]
    datasource = await load_datasource_or_404(app, table_id)
    datasource = datasource.filter(uuid=row_uuid)
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


@app.route("/tables/{table_id}/{row_uuid}/delete", methods=["POST"], name="delete-row")
async def delete_row(request):
    table_id = request.path_params["table_id"]
    row_uuid = request.path_params["row_uuid"]
    datasource = await load_datasource_or_404(app, table_id)
    datasource = datasource.filter(uuid=row_uuid)
    item = await datasource.get()
    if item is None:
        raise HTTPException(status_code=404)

    await item.delete()
    url = request.url_for("table", table_id=table_id)
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
