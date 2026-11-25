"""Adicionar data de nascimento opcional ao perfil do usuário."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1c2e3f4b5d6"
down_revision: Union[str, None] = "ed4bdd3fc88a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("data_nascimento", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("usuarios", "data_nascimento")
