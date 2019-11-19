from starlette.exceptions import HTTPException
from source.resources import database, url_for
from source import tables
from sqlalchemy.sql import select
import datetime
import typesystem
import uuid


async def load_datasources():
    query = (
        select([tables.table] + [tables.users.c.username])
        .select_from(tables.table.join(tables.users))
        .order_by(tables.table.c.created_at.desc())
    )
    records = await database.fetch_all(query)
    return [
        TableDataSource(table["username"], table)
        for table in records
        if table["identity"]
    ]


async def load_datasources_for_user(user):
    username = user["username"]
    query = (
        tables.table.select()
        .order_by(tables.table.c.created_at.desc())
        .where(tables.table.c.user_id == user["pk"])
    )
    records = await database.fetch_all(query)
    return [TableDataSource(username, table) for table in records if table["identity"]]


async def load_datasource_or_404(username, table_identity):
    query = (
        tables.table.select()
        .select_from(tables.table.join(tables.users))
        .where(tables.users.c.username == username)
        .where(tables.table.c.identity == table_identity)
    )

    table = await database.fetch_one(query)
    if table is None:
        raise HTTPException(status_code=404)

    query = (
        tables.column.select()
        .where(tables.column.c.table == table["pk"])
        .order_by(tables.column.c.position)
    )
    columns = await database.fetch_all(query)
    return TableDataSource(username, table, columns)


class TableDataSource:
    def __init__(self, username, table, columns=None):
        self.name = table["name"]
        self.url = url_for("table", username=username, table_id=table["identity"])
        self.username = username
        self.table = table
        self.columns = columns
        self.query_limit = None
        self.query_offset = None
        self.uuid_filter = None
        self.search_term = None
        self.sort_func = None
        self.sort_reverse = False

        if columns is not None:
            fields = {}
            for column in columns:
                if column["datatype"] == "string":
                    fields[column["identity"]] = typesystem.String(
                        title=column["name"], max_length=100
                    )
                elif column["datatype"] == "integer":
                    fields[column["identity"]] = typesystem.Integer(
                        title=column["name"]
                    )
            self.schema = type("Schema", (typesystem.Schema,), fields)

    def limit(self, limit):
        self.query_limit = limit
        return self

    def offset(self, offset):
        self.query_offset = offset
        return self

    def search(self, search_term):
        self.search_term = search_term
        return self

    def order_by(self, column, reverse):
        self.sort_func = lambda row: row["data"][column]
        self.sort_reverse = reverse
        return self

    def apply_query_filters(self, query):
        query = query.where(tables.row.c.table == self.table["pk"])
        if self.search_term is not None:
            query = query.where(
                tables.row.c.search_text.ilike("%" + self.search_term + "%")
            )
        if self.uuid_filter is not None:
            query = query.where(tables.row.c.uuid == self.uuid_filter)
        return query

    def filter(self, uuid=None):
        self.uuid_filter = uuid
        return self

    async def count(self):
        query = tables.row.count()
        query = self.apply_query_filters(query)
        return await database.fetch_val(query)

    async def all(self):
        query = tables.row.select()
        query = self.apply_query_filters(query)
        query = query.order_by(tables.row.c.created_at)
        rows = await database.fetch_all(query)
        if self.sort_func is not None:
            rows = sorted(rows, key=self.sort_func, reverse=self.sort_reverse)
        if self.query_offset is not None and self.query_limit is not None:
            rows = rows[self.query_offset : self.query_offset + self.query_limit]
        return [RowDataItem(self.username, self.table, row) for row in rows]

    async def get(self):
        query = tables.row.select()
        query = self.apply_query_filters(query)
        row = await database.fetch_one(query)
        if row is None:
            return
        return RowDataItem(self.username, self.table, row)

    async def create(self, values):
        insert_values = {
            "created_at": datetime.datetime.now(),
            "uuid": str(uuid.uuid4()),
            "table": self.table["pk"],
            "data": values,
            "search_text": " ".join(
                [item for item in values.values() if isinstance(item, str)]
            ),
        }
        query = tables.row.insert()
        return await database.execute(query, values=insert_values)

    def validate(self, data):
        record, errors = self.schema.validate_or_error(data)
        validated_data = dict(record) if record is not None else None
        return validated_data, errors


class RowDataItem:
    def __init__(self, username, table, row):
        self.username = username
        self.table = table
        self.row = row
        self.uuid = row["uuid"]

    def __getitem__(self, key):
        return self.row["data"][key]

    def get(self, key, default=None):
        return self.row["data"].get(key, default)

    @property
    def url(self):
        return url_for(
            "detail",
            username=self.username,
            table_id=self.table["identity"],
            row_uuid=self.row["uuid"],
        )

    @property
    def delete_url(self):
        return url_for(
            "delete-row",
            username=self.username,
            table_id=self.table["identity"],
            row_uuid=self.row["uuid"],
        )

    async def update(self, values):
        query = tables.row.update().where(tables.row.c.uuid == self.row["uuid"])
        update_values = {
            "data": values,
            "search_text": " ".join(
                [item for item in values.values() if isinstance(item, str)]
            ),
        }
        return await database.execute(query, values=update_values)

    async def delete(self):
        query = tables.row.delete().where(tables.row.c.uuid == self.row["uuid"])
        return await database.execute(query)
