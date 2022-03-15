"""mirror lifecycle

Revision ID: b66d328b9fa7
Revises: f31ac849f6b2
Create Date: 2022-03-10 12:42:21.404500

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b66d328b9fa7'
down_revision = 'f31ac849f6b2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('mirror', sa.Column('deprecated', sa.DateTime(), nullable=True))
    op.add_column('mirror', sa.Column('destroyed', sa.DateTime(), nullable=True))
    op.drop_column('mirror', 'deleted')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('mirror', sa.Column('deleted', sa.DATETIME(), nullable=True))
    op.drop_column('mirror', 'destroyed')
    op.drop_column('mirror', 'deprecated')
    # ### end Alembic commands ###