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
