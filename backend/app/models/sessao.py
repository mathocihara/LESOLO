from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.conexao import Base

if TYPE_CHECKING:
    from app.models.usuario import Usuario


class Sessao(Base):
    __tablename__ = "sessoes"
    __table_args__ = (Index("ix_sessoes_usuario_data_criacao", "usuario_id", "data_criacao"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    data_criacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    persistente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    ativa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    usuario: Mapped[Usuario] = relationship(back_populates="sessoes")
