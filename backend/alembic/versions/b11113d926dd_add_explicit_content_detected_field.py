"""Add explicit content detected field

Revision ID: b11113d926dd
Revises: 00fd35b458f0
Create Date: 2025-03-21 13:25:15.713771

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b11113d926dd'
down_revision: Union[str, None] = '00fd35b458f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('videos', sa.Column('explicit_content_detected', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('videos', 'explicit_content_detected')
    # ### end Alembic commands ###
