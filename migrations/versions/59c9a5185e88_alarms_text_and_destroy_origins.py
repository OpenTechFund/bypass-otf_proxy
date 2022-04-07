"""alarms text and destroy origins

Revision ID: 59c9a5185e88
Revises: 5c69fe874e4d
Create Date: 2022-04-07 16:30:27.888327

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '59c9a5185e88'
down_revision = '5c69fe874e4d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('alarm', schema=None) as batch_op:
        batch_op.add_column(sa.Column('text', sa.String(length=255), nullable=True))

    with op.batch_alter_table('origin', schema=None) as batch_op:
        batch_op.add_column(sa.Column('destroyed', sa.DateTime(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('origin', schema=None) as batch_op:
        batch_op.drop_column('destroyed')

    with op.batch_alter_table('alarm', schema=None) as batch_op:
        batch_op.drop_column('text')

    # ### end Alembic commands ###