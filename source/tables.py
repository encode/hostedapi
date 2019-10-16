import sqlalchemy


metadata = sqlalchemy.MetaData()

election = sqlalchemy.Table(
    "election",
    metadata,
    sqlalchemy.Column("pk", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("year", sqlalchemy.Integer),
    sqlalchemy.Column("constituency", sqlalchemy.String),
    sqlalchemy.Column("surname", sqlalchemy.String),
    sqlalchemy.Column("first_name", sqlalchemy.String),
    sqlalchemy.Column("party", sqlalchemy.String),
    sqlalchemy.Column("votes", sqlalchemy.Integer),
)


table = sqlalchemy.Table(
    "table",
    metadata,
    sqlalchemy.Column("pk", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, index=True),
    sqlalchemy.Column("identity", sqlalchemy.String, index=True),
    sqlalchemy.Column("name", sqlalchemy.String),
)


column = sqlalchemy.Table(
    "column",
    metadata,
    sqlalchemy.Column("pk", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, index=True),
    sqlalchemy.Column("identity", sqlalchemy.String),
    sqlalchemy.Column("name", sqlalchemy.String),
    sqlalchemy.Column("datatype", sqlalchemy.String),
    sqlalchemy.Column("table", sqlalchemy.Integer, index=True),
    sqlalchemy.Column("position", sqlalchemy.Integer),
)


row = sqlalchemy.Table(
    "row",
    metadata,
    sqlalchemy.Column("pk", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, index=True),
    sqlalchemy.Column("uuid", sqlalchemy.String, index=True),
    sqlalchemy.Column("table", sqlalchemy.Integer, index=True),
    sqlalchemy.Column("data", sqlalchemy.JSON),
    sqlalchemy.Column("search_text", sqlalchemy.String),
)
