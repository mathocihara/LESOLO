from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.preferencia_usuario import PreferenciaUsuario


class PreferenciaUsuarioRepositorio:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def salvar(self, preferencia: PreferenciaUsuario) -> PreferenciaUsuario:
        self._sessao.add(preferencia)
        self._sessao.flush()
        return preferencia

    def buscar_por_usuario(self, usuario_id: uuid.UUID) -> PreferenciaUsuario | None:
        return self._sessao.scalar(
            select(PreferenciaUsuario).where(PreferenciaUsuario.usuario_id == usuario_id)
        )

    def atualizar(
        self,
        usuario_id: uuid.UUID,
        *,
        tema: str | None = None,
        alto_contraste: bool | None = None,
        notificacoes: bool | None = None,
    ) -> PreferenciaUsuario | None:
        preferencia = self.buscar_por_usuario(usuario_id)
        if preferencia is None:
            return None

        if tema is not None:
            preferencia.tema = tema
        if alto_contraste is not None:
            preferencia.alto_contraste = alto_contraste
        if notificacoes is not None:
            preferencia.notificacoes = notificacoes

        self._sessao.flush()
        return preferencia
