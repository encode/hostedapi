from starlette.exceptions import HTTPException
from starlette.responses import RedirectResponse, Response, JSONResponse
from source import ordering, pagination, search, tables
from source.resources import database, broadcast, templates
from source.datasource import (
    load_datasources,
    load_datasources_for_user,
    load_datasource_or_404,
)
from source.negotiation import negotiate
from source.csv_utils import (
    normalize_table,
    determine_column_types,
    determine_column_identities,
)
from slugify import slugify
from sqlalchemy import func, select
import chardet
import csv
import datetime
import io
import json
import math
import typesystem
import uuid


class NewTableSchema(typesystem.Schema):
    name = typesystem.String(max_length=100)


class NewColumnSchema(typesystem.Schema):
    name = typesystem.String(max_length=100)
    datatype = typesystem.Choice(choices=["string", "integer"])


def check_can_edit(request, username):
    can_edit = request.session.get("username") == username
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and not can_edit:
        raise HTTPException(status_code=403)
    return can_edit


async def dashboard(request):
    datasources = await load_datasources()

    rows = []
    for datasource in datasources:
        text = datasource.name
        url = datasource.url
        count = await datasource.count()
        rows.append(
            {"owner": datasource.username, "text": text, "url": url, "count": count}
        )

    template = "dashboard.html"
    context = {
        "request": request,
        "rows": rows,
    }
    return templates.TemplateResponse(template, context)


async def profile(request):
    username = request.path_params["username"]
    can_edit = check_can_edit(request, username)

    query = tables.users.select().where(tables.users.c.username == username)
    profile_user = await database.fetch_one(query)
    if profile_user is None:
        raise HTTPException(status_code=404)

    datasources = await load_datasources_for_user(profile_user)

    rows = []
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
            query = (
                tables.table.select()
                .where(tables.table.c.user_id == profile_user["pk"])
                .where(tables.table.c.identity == identity)
            )
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
        "can_edit": can_edit,
    }
    return templates.TemplateResponse(template, context, status_code=status_code)


async def table(request):
    PAGE_SIZE = 10

    username = request.path_params["username"]
    table_id = request.path_params["table_id"]
    can_edit = check_can_edit(request, username)
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

    # Export
    export = request.query_params.get("export")
    if export == "json":
        queryset = await datasource.all()
        data = [
            {
                key: field.serialize(item.get(key))
                for key, field in datasource.schema.fields.items()
            }
            for item in queryset
        ]
        content = json.dumps(data, indent=4)
        headers = {"Content-Disposition": f'attachment; filename="{table_id}.json"'}
        return Response(content, headers=headers)
    elif export == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        queryset = await datasource.all()

        headers = [field.title for field in datasource.schema.fields.values()]
        writer.writerow(headers)
        for item in queryset:
            row = [item.get(key, default="") for key in datasource.schema.fields.keys()]
            writer.writerow(row)

        content = output.getvalue()
        headers = {"Content-Disposition": f'attachment; filename="{table_id}.csv"'}
        return Response(content, headers=headers)

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
            await broadcast.publish(f"{username}/{table_id}", "Added row")
            return RedirectResponse(url=request.url, status_code=303)
        status_code = 400
    else:
        form_values = None
        form_errors = None
        status_code = 200

    accept = request.headers.get("Accept", "*/*")
    media_type = negotiate(accept, ["application/json", "text/html"])

    view_style = request.query_params.get("view")
    if view_style not in ("json", "table"):
        view_style = "table"

    json_data = None
    if view_style == "json" or media_type == "application/json":
        data = [
            {
                key: field.serialize(item.get(key))
                for key, field in datasource.schema.fields.items()
            }
            for item in queryset
        ]
        if media_type == "application/json":
            return JSONResponse(data, headers={"Access-Control-Allow-Origin": "*"})
        json_data = json.dumps(data, indent=4)

    websocket_url = (
        str(request.url).replace("http://", "ws://").replace("https://", "wss://")
    )

    # Render the page
    template = "table.html"
    context = {
        "request": request,
        "schema": datasource.schema,
        "owner": username,
        "table_id": table_id,
        "table_name": datasource.name,
        "table_url": datasource.url,
        "websocket_url": websocket_url,
        "table_has_columns": bool(datasource.schema.fields),
        "table_has_rows": search_term or list(queryset),
        "queryset": queryset,
        "json_data": json_data,
        "view_style": view_style,
        "search_term": search_term,
        "column_controls": column_controls,
        "page_controls": page_controls,
        "form_errors": form_errors,
        "form_values": form_values,
        "can_edit": can_edit,
    }
    return templates.TemplateResponse(template, context, status_code=status_code)


async def columns(request):
    username = request.path_params["username"]
    table_id = request.path_params["table_id"]
    can_edit = check_can_edit(request, username)
    datasource = await load_datasource_or_404(username, table_id)

    if request.method == "POST":
        form_values = await request.form()
        validated_data, form_errors = NewColumnSchema.validate_or_error(form_values)
        if not form_errors:
            identity = slugify(validated_data["name"], separator="_", to_lower=True)
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
            insert_data["identity"] = slugify(
                insert_data["name"], separator="_", to_lower=True
            )
            insert_data["position"] = position
            query = tables.column.insert()
            await database.execute(query, values=insert_data)
            await broadcast.publish(f"{username}/{table_id}", "Added column")
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
        "can_edit": can_edit,
    }
    return templates.TemplateResponse(template, context, status_code=status_code)


async def delete_table(request):
    username = request.path_params["username"]
    table_id = request.path_params["table_id"]
    can_edit = check_can_edit(request, username)
    datasource = await load_datasource_or_404(username, table_id)

    query = tables.column.delete().where(
        tables.column.c.table == datasource.table["pk"]
    )
    await database.execute(query)

    query = tables.row.delete().where(tables.row.c.table == datasource.table["pk"])
    await database.execute(query)

    query = tables.table.delete().where(tables.table.c.pk == datasource.table["pk"])
    await database.execute(query)

    url = request.url_for("profile", username=username)
    return RedirectResponse(url=url, status_code=303)


async def upload(request):
    username = request.path_params["username"]
    table_id = request.path_params["table_id"]
    can_edit = check_can_edit(request, username)
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

    url = request.url_for("table", username=username, table_id=table_id)
    return RedirectResponse(url=url, status_code=303)


async def delete_column(request):
    username = request.path_params["username"]
    table_id = request.path_params["table_id"]
    column_id = request.path_params["column_id"]
    can_edit = check_can_edit(request, username)
    datasource = await load_datasource_or_404(username, table_id)
    if column_id not in datasource.schema.fields:
        raise HTTPException(status_code=404)

    # Delete the column.
    query = (
        tables.column.delete()
        .where(tables.column.c.table == datasource.table["pk"])
        .where(tables.column.c.identity == column_id)
    )
    await database.execute(query)

    # Perform a column count.
    query = (
        select([func.count()])
        .select_from(tables.column)
        .where(tables.row.c.table == datasource.table["pk"])
    )
    column_count = await database.fetch_val(query)

    # If the final column in a table has been deleted, then we should drop
    # all the data in the table.
    if column_count == 0:
        query = tables.row.delete().where(tables.row.c.table == datasource.table["pk"])
        await database.execute(query)

    url = request.url_for("columns", username=username, table_id=table_id)
    await broadcast.publish(f"{username}/{table_id}", "Deleted column")
    return RedirectResponse(url=url, status_code=303)


async def detail(request):
    username = request.path_params["username"]
    table_id = request.path_params["table_id"]
    row_uuid = request.path_params["row_uuid"]
    can_edit = check_can_edit(request, username)
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
            await broadcast.publish(f"{username}/{table_id}", "Updated row")
            return RedirectResponse(url=request.url, status_code=303)
        status_code = 400
    else:
        form_values = (
            None if item is None else datasource.schema.make_validator().serialize(item)
        )
        form_errors = None
        status_code = 200

    accept = request.headers.get("Accept", "*/*")
    media_type = negotiate(accept, ["application/json", "text/html"])

    view_style = request.query_params.get("view")
    if view_style not in ("json", "table"):
        view_style = "table"

    json_data = None
    if view_style == "json" or media_type == "application/json":
        data = {
            key: field.serialize(item.get(key))
            for key, field in datasource.schema.fields.items()
        }
        if media_type == "application/json":
            return JSONResponse(data, headers={"Access-Control-Allow-Origin": "*"})
        json_data = json.dumps(data, indent=4)

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
        "can_edit": can_edit,
        "view_style": view_style,
        "json_data": json_data,
    }
    return templates.TemplateResponse(template, context, status_code=status_code)


async def delete_row(request):
    username = request.path_params["username"]
    table_id = request.path_params["table_id"]
    row_uuid = request.path_params["row_uuid"]
    can_edit = check_can_edit(request, username)
    datasource = await load_datasource_or_404(username, table_id)
    datasource = datasource.filter(uuid=row_uuid)
    item = await datasource.get()
    if item is None:
        raise HTTPException(status_code=404)

    await item.delete()

    url = request.url_for("table", username=username, table_id=table_id)
    await broadcast.publish(f"{username}/{table_id}", "Deleted row")
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
