from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.sessao import Sessao


class SessaoRepositorio:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def salvar(self, sessao: Sessao) -> Sessao:
        self._sessao.add(sessao)
        self._sessao.flush()
        return sessao

    def buscar_por_id(self, sessao_id: uuid.UUID) -> Sessao | None:
        return self._sessao.get(Sessao, sessao_id)

    def encerrar(self, sessao_id: uuid.UUID) -> bool:
        sessao = self.buscar_por_id(sessao_id)
        if sessao is None:
            return False

        sessao.ativa = False
        self._sessao.flush()
        return True
