from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.conexao import Base

if TYPE_CHECKING:
    from app.models.usuario import Usuario


class PreferenciaUsuario(Base):
    __tablename__ = "preferencias_usuario"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    tema: Mapped[str] = mapped_column(String(30), nullable=False, default="escuro", server_default="escuro")
    alto_contraste: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    notificacoes: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    usuario: Mapped[Usuario] = relationship(back_populates="preferencia")
