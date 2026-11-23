from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.registro_consulta import RegistroConsulta, StatusRegistro


class RegistroConsultaRepositorio:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def salvar(self, registro: RegistroConsulta) -> RegistroConsulta:
        self._sessao.add(registro)
        self._sessao.flush()
        return registro

    def buscar_por_id(
        self, registro_id: uuid.UUID, usuario_id: uuid.UUID
    ) -> RegistroConsulta | None:
        return self._sessao.scalar(
            select(RegistroConsulta).where(
                RegistroConsulta.id == registro_id,
                RegistroConsulta.usuario_id == usuario_id,
            )
        )

    def listar_por_usuario(
        self,
        usuario_id: uuid.UUID,
        status: StatusRegistro | None = None,
    ) -> list[RegistroConsulta]:
        consulta = select(RegistroConsulta).where(RegistroConsulta.usuario_id == usuario_id)
        if status is not None:
            consulta = consulta.where(RegistroConsulta.status == status)
        return list(self._sessao.scalars(consulta).all())

    def excluir_por_id(self, registro_id: uuid.UUID, usuario_id: uuid.UUID) -> bool:
        registro = self.buscar_por_id(registro_id, usuario_id)
        if registro is None:
            return False

        self._sessao.delete(registro)
        self._sessao.flush()
        return True

    def excluir_por_usuario(
        self,
        usuario_id: uuid.UUID,
        status: StatusRegistro | None = None,
    ) -> int:
        consulta = select(RegistroConsulta).where(RegistroConsulta.usuario_id == usuario_id)
        if status is not None:
            consulta = consulta.where(RegistroConsulta.status == status)
        registros = list(self._sessao.scalars(consulta).all())
        for registro in registros:
            self._sessao.delete(registro)
        self._sessao.flush()
        return len(registros)
