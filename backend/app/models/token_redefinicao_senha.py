from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.conexao import Base

if TYPE_CHECKING:
    from app.models.usuario import Usuario


class TokenRedefinicaoSenha(Base):
    __tablename__ = "tokens_redefinicao_senha"
    __table_args__ = (
        Index("ix_tokens_redefinicao_usuario_expiracao", "usuario_id", "data_expiracao"),
    )

    # Armazena SHA-256 do token aleatório; o valor original não é persistido.
    valor_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    data_expiracao: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    utilizado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))

    usuario: Mapped[Usuario] = relationship(back_populates="tokens_redefinicao")
