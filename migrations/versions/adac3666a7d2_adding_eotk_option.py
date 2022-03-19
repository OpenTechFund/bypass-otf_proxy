"""adding eotk option

Revision ID: adac3666a7d2
Revises: b66d328b9fa7
Create Date: 2022-03-19 14:55:20.242089

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'adac3666a7d2'
down_revision = 'b66d328b9fa7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('group', sa.Column('eotk', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('group', 'eotk')
    # ### end Alembic commands ###
