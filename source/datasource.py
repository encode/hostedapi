from source.resources import database
from source import tables
import typesystem


async def load_datasource(table_identity):
    query = tables.table.select().where(tables.table.c.identity == table_identity)
    table = await database.fetch_one(query)
    if table is None:
        return None

    query = (
        tables.column.select()
        .where(tables.column.c.table == table["pk"])
        .order_by(tables.column.c.position)
    )
    columns = await database.fetch_all(query)
    return TableDataSource(table, columns)


class TableDataSource:
    def __init__(self, table, columns):
        self.name = table["name"]
        self.url = "/" + table["identity"]
        self.table = table
        self.columns = columns
        self.query_limit = None
        self.query_offset = None

        fields = {}
        for column in columns:
            if column['datatype'] == 'string':
                fields[column['identity']] = typesystem.String(title=column['name'])
            elif column['datatype'] == 'integer':
                fields[column['identity']] = typesystem.Integer(title=column['name'])
        self.schema = type('Schema', (typesystem.Schema,), fields)

    def limit(self, limit):
        self.query_limit = limit
        return self

    def offset(self, offset):
        self.query_offset = offset
        return self

    def search(self, search_term):
        self.search_term = search_term
        return self

    async def count(self):
        query = tables.row.count().where(tables.row.c.table == self.table["pk"])
        return await database.fetch_val(query)

    async def all(self):
        query = tables.row.select().where(tables.row.c.table == self.table["pk"])
        rows = await database.fetch_all(query)
        rows = rows[self.query_offset:self.query_offset+self.query_limit]
        return [RowDataItem(self.table, row) for row in rows]


class RowDataItem:
    def __init__(self, table, row):
        self.table = table
        self.row = row

    def __getitem__(self, key):
        return self.row['data'][key]

    def __str__(self):
        return f"{self['first_name']} {self['surname']}"

    @property
    def url(self):
        return "/" + self.table["identity"] + "/" + self.row["uuid"]

    @property
    def delete_url(self):
        return "/" + self.table["identity"] + "/" + self.row["uuid"] + "/delete"


class Record(typesystem.Schema):
    constituency = typesystem.String(title="Constituency", max_length=100)
    surname = typesystem.String(title="Surname", max_length=100)
    first_name = typesystem.String(title="First Name", max_length=100)
    party = typesystem.String(title="Party", max_length=100)
    votes = typesystem.Integer(title="Votes", minimum=0)


class ElectionDataSource:
    schema = Record

    def __init__(self, app, year):
        self.name = f"UK General Election Results {year}"
        self.app = app
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
        rows = await database.fetch_all(query)
        return [ElectionDataItem(app=self.app, year=self.year, row=row) for row in rows]

    async def get(self):
        query = tables.election.select()
        query = self.apply_query_filters(query)
        row = await database.fetch_one(query)
        if row is None:
            return None
        return ElectionDataItem(app=self.app, year=self.year, row=row)

    async def create(self, values):
        values = dict(values)
        values["year"] = self.year
        query = tables.election.insert()
        return await database.execute(query, values=values)

    def validate(self, data):
        record, errors = Record.validate_or_error(data)
        validated_data = dict(record) if record is not None else None
        return validated_data, errors


class ElectionDataItem:
    def __init__(self, app, year, row):
        self.app = app
        self.year = year
        self.pk = row["pk"]
        self.constituency = row["constituency"]
        self.surname = row["surname"]
        self.first_name = row["first_name"]
        self.party = row["party"]
        self.votes = row["votes"]

    def __str__(self):
        return f"{self.first_name} {self.surname}"

    async def update(self, values):
        query = tables.election.update().where(tables.election.c.pk == self.pk)
        return await database.execute(query, values=values)

    async def delete(self):
        query = tables.election.delete().where(tables.election.c.pk == self.pk)
        return await database.execute(query)

    @property
    def url(self):
        return self.app.url_path_for("detail", year=self.year, pk=self.pk)

    @property
    def delete_url(self):
        return self.app.url_path_for("delete-row", year=self.year, pk=self.pk)
