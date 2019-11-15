from starlette.exceptions import HTTPException
from starlette.responses import RedirectResponse
from source import ordering, pagination, search, tables
from source.resources import database, templates
from source.datasource import (
    load_datasources,
    load_datasources_for_user,
    load_datasource_or_404,
)
from source.csv_utils import (
    normalize_table,
    determine_column_types,
    determine_column_identities,
)
from slugify import slugify
import chardet
import csv
import datetime
import math
import typesystem
import uuid


class NewTableSchema(typesystem.Schema):
    name = typesystem.String(max_length=100)


class NewColumnSchema(typesystem.Schema):
    name = typesystem.String(max_length=100)
    datatype = typesystem.Choice(choices=["string", "integer"])


async def dashboard(request):
    rows = []

    datasources = await load_datasources()

    for datasource in datasources:
        text = datasource.name
        url = datasource.url
        count = await datasource.count()
        rows.append(
            {"owner": datasource.username, "text": text, "url": url, "count": count}
        )

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


async def profile(request):
    rows = []

    username = request.path_params["username"]
    query = tables.users.select().where(tables.users.c.username == username)
    profile_user = await database.fetch_one(query)
    if profile_user is None:
        raise HTTPException(status_code=404)

    datasources = await load_datasources_for_user(profile_user)

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
            insert_data["user_id"] = profile_user["pk"]
            query = tables.table.insert()
            await database.execute(query, values=insert_data)
            return RedirectResponse(url=request.url, status_code=303)
        status_code = 400
    else:
        form_values = None
        form_errors = None
        status_code = 200

    template = "profile.html"
    context = {
        "request": request,
        "owner": username,
        "profile_user": profile_user,
        "rows": rows,
        "form_values": form_values,
        "form_errors": form_errors,
    }
    return templates.TemplateResponse(template, context, status_code=status_code)


async def table(request):
    PAGE_SIZE = 10

    username = request.path_params.get("username")
    table_id = request.path_params["table_id"]
    datasource = await load_datasource_or_404(username, table_id)

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
        "owner": username,
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


async def columns(request):
    username = request.path_params.get("username")
    table_id = request.path_params["table_id"]
    datasource = await load_datasource_or_404(username, table_id)

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
        "owner": username,
        "table_id": table_id,
        "table_name": datasource.name,
        "table_url": datasource.url,
        "columns": datasource.columns,
        "form_errors": form_errors,
        "form_values": form_values,
    }
    return templates.TemplateResponse(template, context, status_code=status_code)


async def delete_table(request):
    username = request.path_params.get("username")
    table_id = request.path_params["table_id"]
    datasource = await load_datasource_or_404(username, table_id)

    query = tables.column.delete().where(
        tables.column.c.table == datasource.table["pk"]
    )
    await database.execute(query)

    query = tables.row.delete().where(tables.row.c.table == datasource.table["pk"])
    await database.execute(query)

    query = tables.table.delete().where(tables.table.c.pk == datasource.table["pk"])
    await database.execute(query)

    if username:
        url = request.url_for("profile", username=username)
    else:
        url = request.url_for("dashboard")

    return RedirectResponse(url=url, status_code=303)


async def upload(request):
    username = request.path_params.get("username")
    table_id = request.path_params["table_id"]
    datasource = await load_datasource_or_404(username, table_id)

    form = await request.form()
    data = await form["upload-file"].read()
    encoding = chardet.detect(data)["encoding"]
    lines = data.decode(encoding).splitlines()
    rows = normalize_table([row for row in csv.reader(lines)])
    column_identities = determine_column_identities(rows)
    column_types, schema = determine_column_types(rows)
    unvalidated_data = [dict(zip(column_identities, row)) for row in rows[1:]]
    validated_data = [
        dict(instance)
        for instance in typesystem.Array(
            items=typesystem.Reference(to=schema)
        ).validate(unvalidated_data, strict=False)
    ]

    column_insert_values = [
        {
            "created_at": datetime.datetime.now(),
            "name": name,
            "identity": column_identities[idx],
            "datatype": column_types[idx],
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
            "data": validated_data[idx],
            "search_text": " ".join(row),
        }
        for idx, row in enumerate(rows[1:])
    ]

    query = tables.row.insert()
    await database.execute_many(query, row_insert_values)

    if username:
        url = request.url_for("table", username=username, table_id=table_id)
    else:
        url = request.url_for("table", table_id=table_id)

    return RedirectResponse(url=url, status_code=303)


async def delete_column(request):
    username = request.path_params.get("username")
    table_id = request.path_params["table_id"]
    column_id = request.path_params["column_id"]
    datasource = await load_datasource_or_404(username, table_id)
    if column_id not in datasource.schema.fields:
        raise HTTPException(status_code=404)

    query = (
        tables.column.delete()
        .where(tables.column.c.table == datasource.table["pk"])
        .where(tables.column.c.identity == column_id)
    )
    await database.execute(query)

    if username:
        url = request.url_for("columns", username=username, table_id=table_id)
    else:
        url = request.url_for("columns", table_id=table_id)

    return RedirectResponse(url=url, status_code=303)


async def detail(request):
    username = request.path_params.get("username")
    table_id = request.path_params["table_id"]
    row_uuid = request.path_params["row_uuid"]
    datasource = await load_datasource_or_404(username, table_id)
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
        "owner": username,
        "table_name": datasource.name,
        "table_url": datasource.url,
        "item": item,
        "form_values": form_values,
        "form_errors": form_errors,
    }
    return templates.TemplateResponse(template, context, status_code=status_code)


async def delete_row(request):
    username = request.path_params.get("username")
    table_id = request.path_params["table_id"]
    row_uuid = request.path_params["row_uuid"]
    datasource = await load_datasource_or_404(username, table_id)
    datasource = datasource.filter(uuid=row_uuid)
    item = await datasource.get()
    if item is None:
        raise HTTPException(status_code=404)

    await item.delete()

    if username:
        url = request.url_for("table", username=username, table_id=table_id)
    else:
        url = request.url_for("table", table_id=table_id)

    return RedirectResponse(url=url, status_code=303)


async def error(request):
    """
    An example error. Switch the `debug` setting to see either tracebacks or 500 pages.
    """
    raise RuntimeError("Oh no")


async def not_found(request, exc):
    """
    Return an HTTP 404 page.
    """
    template = "404.html"
    context = {"request": request}
    return templates.TemplateResponse(template, context, status_code=404)


async def server_error(request, exc):
    """
    Return an HTTP 500 page.
    """
    template = "500.html"
    context = {"request": request}
    return templates.TemplateResponse(template, context, status_code=500)
