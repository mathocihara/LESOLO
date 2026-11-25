"""Registrar resultado parcial e falhas por fonte sem perder histórico."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "registros_consulta",
        sa.Column("status_consulta", sa.Text(), nullable=True),
    )
    op.execute(
        "UPDATE registros_consulta SET status_consulta = 'NAO_CLASSIFICADA' "
        "WHERE status_consulta IS NULL"
    )
    op.alter_column(
        "registros_consulta",
        "status_consulta",
        existing_type=sa.Text(),
        nullable=False,
        server_default="COMPLETA",
    )
    for nome in ("dados_ausentes", "falhas_fontes", "dados_desatualizados"):
        op.add_column(
            "registros_consulta",
            sa.Column(nome, sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        )


def downgrade() -> None:
    op.drop_column("registros_consulta", "dados_desatualizados")
    op.drop_column("registros_consulta", "falhas_fontes")
    op.drop_column("registros_consulta", "dados_ausentes")
    op.drop_column("registros_consulta", "status_consulta")
