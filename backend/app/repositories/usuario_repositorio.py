from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usuario import Usuario


class UsuarioRepositorio:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def salvar(self, usuario: Usuario) -> Usuario:
        self._sessao.add(usuario)
        self._sessao.flush()
        return usuario

    def buscar_por_email(self, email: str) -> Usuario | None:
        return self._sessao.scalar(select(Usuario).where(Usuario.email == email))

    def buscar_por_id(self, usuario_id: uuid.UUID) -> Usuario | None:
        return self._sessao.get(Usuario, usuario_id)
