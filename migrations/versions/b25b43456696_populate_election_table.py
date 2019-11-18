"""Populate election table

Revision ID: b25b43456696
Revises: dff1bea4f56b
Create Date: 2019-10-07 10:18:27.626402

"""
from alembic import op
import sqlalchemy

# revision identifiers, used by Alembic.
revision = 'b25b43456696'
down_revision = 'dff1bea4f56b'
branch_labels = None
depends_on = None

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



def upgrade():
    pass


def downgrade():
    query = election.delete()
    op.execute(query)
