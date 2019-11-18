"""Create initial dynamic tables

Revision ID: c609270e720d
Revises: e13b872e5e22
Create Date: 2019-10-16 08:47:46.675150

"""
from alembic import op
import sqlalchemy as sa
import datetime
import uuid


# revision identifiers, used by Alembic.
revision = 'c609270e720d'
down_revision = 'e13b872e5e22'
branch_labels = None
depends_on = None


metadata = sa.MetaData()

table = sa.Table(
    "table",
    metadata,
    sa.Column("pk", sa.Integer, primary_key=True),
    sa.Column("created_at", sa.DateTime, index=True),
    sa.Column("identity", sa.String, index=True),
    sa.Column("name", sa.String),
)


column = sa.Table(
    "column",
    metadata,
    sa.Column("pk", sa.Integer, primary_key=True),
    sa.Column("created_at", sa.DateTime, index=True),
    sa.Column("identity", sa.String),
    sa.Column("name", sa.String),
    sa.Column("datatype", sa.String),
    sa.Column("table", sa.Integer, index=True),
    sa.Column("position", sa.Integer),
)


row = sa.Table(
    "row",
    metadata,
    sa.Column("pk", sa.Integer, primary_key=True),
    sa.Column("created_at", sa.DateTime, index=True),
    sa.Column("uuid", sa.String, index=True),
    sa.Column("table", sa.Integer, index=True),
    sa.Column("data", sa.JSON),
    sa.Column("search_text", sa.String),
)


def upgrade():
    pass


def downgrade():
    query = table.delete()
    op.execute(query)

    query = column.delete()
    op.execute(query)
