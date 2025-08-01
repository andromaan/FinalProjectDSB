"""added regresion

Revision ID: 1277451be81b
Revises: 5e027df5d85d
Create Date: 2025-06-17 14:34:41.939661

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1277451be81b'
down_revision: Union[str, None] = '5e027df5d85d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('regression_models',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('target_variable', sa.String(), nullable=False),
    sa.Column('feature_variables', sa.JSON(), nullable=False),
    sa.Column('coefficients_json', sa.JSON(), nullable=False),
    sa.Column('intercept', sa.Float(), nullable=False),
    sa.Column('r_squared', sa.Float(), nullable=True),
    sa.Column('last_trained_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('platform_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['platform_id'], ['car_platforms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('regression_models')
    # ### end Alembic commands ###
