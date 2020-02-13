from .resources import broadcast, templates
from source import ordering, pagination, search
from source.datasource import load_datasource_or_404

import asyncio
import math
import json


async def ws_table(websocket):
    await websocket.accept()
    task = asyncio.create_task(ws_table_listener(websocket))
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            break
    task.cancel()
    await websocket.close()


async def ws_table_listener(websocket):
    PAGE_SIZE = 10
    username = websocket.path_params["username"]
    table_id = websocket.path_params["table_id"]

    async with broadcast.subscribe(f"{username}/{table_id}") as queue:
        while True:
            message = await queue.get()

            datasource = await load_datasource_or_404(username, table_id)

            # datasource = ElectionDataSource(app=app, year=year)
            columns = {
                key: field.title for key, field in datasource.schema.fields.items()
            }

            # Get some normalised information from URL query parameters
            current_page = pagination.get_page_number(url=websocket.url)
            order_column, is_reverse = ordering.get_ordering(
                url=websocket.url, columns=columns
            )
            search_term = search.get_search_term(url=websocket.url)

            # Filter by any search term
            datasource = datasource.search(search_term)

            # Determine pagination info
            count = await datasource.count()
            total_pages = max(math.ceil(count / PAGE_SIZE), 1)
            current_page = max(min(current_page, total_pages), 1)
            offset = (current_page - 1) * PAGE_SIZE

            # Perform column ordering
            if order_column is not None:
                datasource = datasource.order_by(
                    column=order_column, reverse=is_reverse
                )

            #  Perform pagination
            datasource = datasource.offset(offset).limit(PAGE_SIZE)
            queryset = await datasource.all()

            # Get pagination and column controls to render on the page
            column_controls = ordering.get_column_controls(
                url=websocket.url,
                columns=columns,
                selected_column=order_column,
                is_reverse=is_reverse,
            )
            page_controls = pagination.get_page_controls(
                url=websocket.url, current_page=current_page, total_pages=total_pages
            )

            # Handle JSON view
            view_style = websocket.query_params.get("view")
            if view_style not in ("json", "table"):
                view_style = "table"

            json_data = None
            if view_style == "json":
                data = [
                    {
                        key: field.serialize(item.get(key))
                        for key, field in datasource.schema.fields.items()
                    }
                    for item in queryset
                ]
                json_data = json.dumps(data, indent=4)

            template = templates.get_template("ws_table.html")
            html = template.render(
                {
                    "schema": datasource.schema,
                    "queryset": queryset,
                    "json_data": json_data,
                    "view_style": view_style,
                    "column_controls": column_controls,
                    "page_controls": page_controls,
                }
            )
            await websocket.send_text(html)
