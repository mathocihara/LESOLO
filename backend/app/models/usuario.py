from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.conexao import Base

if TYPE_CHECKING:
    from app.models.preferencia_usuario import PreferenciaUsuario
    from app.models.registro_consulta import RegistroConsulta
    from app.models.sessao import Sessao
    from app.models.token_redefinicao_senha import TokenRedefinicaoSenha


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    senha_hash: Mapped[str] = mapped_column("senha_hash", String(255), nullable=False)

    sessoes: Mapped[list[Sessao]] = relationship(
        back_populates="usuario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    tokens_redefinicao: Mapped[list[TokenRedefinicaoSenha]] = relationship(
        back_populates="usuario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    registros_consulta: Mapped[list[RegistroConsulta]] = relationship(
        back_populates="usuario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    preferencia: Mapped[PreferenciaUsuario | None] = relationship(
        back_populates="usuario",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
