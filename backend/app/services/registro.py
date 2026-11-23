from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.models.registro_consulta import (
    DadosGeograficos,
    RegistroConsulta,
    StatusRegistro,
)
from app.repositories.registro_consulta_repositorio import RegistroConsultaRepositorio


class DadosRegistroInvalidosError(ValueError):
    """Dados de entrada inválidos para um registro de consulta."""


class RegistroConsultaNaoEncontradoError(LookupError):
    """Registro inexistente ou pertencente a outro usuário."""


_NOME_AUTOMATICO = re.compile(r"^Consulta (\d+)$")
_PRAZO_EXPIRACAO_PADRAO = timedelta(days=30)


class ServicoRegistro:
    def __init__(
        self,
        sessao: Session,
        prazoExpiracaoTemporario: timedelta = _PRAZO_EXPIRACAO_PADRAO,
    ) -> None:
        if (
            not isinstance(prazoExpiracaoTemporario, timedelta)
            or prazoExpiracaoTemporario <= timedelta(0)
        ):
            raise ValueError("O prazo de expiração temporária deve ser positivo.")

        self._sessao = sessao
        self._repositorio = RegistroConsultaRepositorio(sessao)
        self._prazo_expiracao_temporario = prazoExpiracaoTemporario

    def criarTemporario(
        self,
        usuarioId: uuid.UUID,
        latitude: Decimal | int | float,
        longitude: Decimal | int | float,
        dadosGeograficos: DadosGeograficos,
        dataConsulta: datetime,
    ) -> RegistroConsulta:
        self._validar_uuid(usuarioId, "Usuário")
        latitude_validada = self._validar_coordenada(latitude, -90, 90, "latitude")
        longitude_validada = self._validar_coordenada(longitude, -180, 180, "longitude")
        if not isinstance(dadosGeograficos, DadosGeograficos):
            raise DadosRegistroInvalidosError("Dados geográficos inválidos.")
        if not isinstance(dataConsulta, datetime):
            raise DadosRegistroInvalidosError("Data da consulta inválida.")

        try:
            registro = RegistroConsulta(
                usuario_id=usuarioId,
                latitude=latitude_validada,
                longitude=longitude_validada,
                dados_geograficos=dadosGeograficos,
                data_consulta=dataConsulta,
                status=StatusRegistro.TEMPORARIO,
                data_expiracao=dataConsulta + self._prazo_expiracao_temporario,
            )
            registro = self._repositorio.salvar(registro)
            self._sessao.commit()
            return registro
        except Exception:
            self._sessao.rollback()
            raise

    def salvarComoPermanente(
        self,
        registroId: uuid.UUID,
        usuarioId: uuid.UUID,
        nome: str | None = None,
    ) -> RegistroConsulta:
        self._validar_uuid(registroId, "Registro")
        self._validar_uuid(usuarioId, "Usuário")
        nome_personalizado = self._normalizar_nome(nome)

        try:
            registro = self._repositorio.buscar_por_id(registroId, usuarioId)
            if registro is None:
                raise RegistroConsultaNaoEncontradoError(
                    "Registro não encontrado para este usuário."
                )

            registro.nome = nome_personalizado or self.gerarNomeAutomatico(usuarioId)
            registro.status = StatusRegistro.PERMANENTE
            registro.data_expiracao = None
            self._sessao.flush()
            self._sessao.commit()
            return registro
        except Exception:
            self._sessao.rollback()
            raise

    def gerarNomeAutomatico(self, usuarioId: uuid.UUID) -> str:
        self._validar_uuid(usuarioId, "Usuário")
        permanentes = self._repositorio.listar_por_usuario(
            usuarioId, status=StatusRegistro.PERMANENTE
        )
        maiores_numeros = (
            int(correspondencia.group(1))
            for registro in permanentes
            if registro.nome is not None
            if (correspondencia := _NOME_AUTOMATICO.fullmatch(registro.nome)) is not None
        )
        proximo_numero = max(maiores_numeros, default=0) + 1
        return f"Consulta {proximo_numero}"

    def buscarRegistro(
        self,
        registroId: uuid.UUID,
        usuarioId: uuid.UUID,
        status: StatusRegistro | None = StatusRegistro.PERMANENTE,
    ) -> RegistroConsulta:
        self._validar_uuid(registroId, "Registro")
        self._validar_uuid(usuarioId, "Usuário")
        registro = self._repositorio.buscar_por_id(registroId, usuarioId)
        if registro is None or (status is not None and registro.status != status):
            raise RegistroConsultaNaoEncontradoError(
                "Registro não encontrado para este usuário."
            )
        return registro

    def listarRegistrosDoUsuario(
        self,
        usuarioId: uuid.UUID,
        status: StatusRegistro | None = StatusRegistro.PERMANENTE,
    ) -> list[RegistroConsulta]:
        self._validar_uuid(usuarioId, "Usuário")
        registros = self._repositorio.listar_por_usuario(usuarioId, status=status)
        return sorted(
            registros,
            key=lambda registro: (registro.data_consulta, str(registro.id)),
            reverse=True,
        )

    def excluirRegistro(self, registroId: uuid.UUID, usuarioId: uuid.UUID) -> None:
        self._validar_uuid(registroId, "Registro")
        self._validar_uuid(usuarioId, "Usuário")
        try:
            if not self._repositorio.excluir_por_id(registroId, usuarioId):
                raise RegistroConsultaNaoEncontradoError(
                    "Registro não encontrado para este usuário."
                )
            self._sessao.commit()
        except Exception:
            self._sessao.rollback()
            raise

    def excluirHistoricoDoUsuario(self, usuarioId: uuid.UUID) -> int:
        self._validar_uuid(usuarioId, "Usuário")
        try:
            quantidade = self._repositorio.excluir_por_usuario(
                usuarioId, status=StatusRegistro.PERMANENTE
            )
            self._sessao.commit()
            return quantidade
        except Exception:
            self._sessao.rollback()
            raise

    @staticmethod
    def _validar_uuid(valor: uuid.UUID, campo: str) -> None:
        if not isinstance(valor, uuid.UUID):
            raise DadosRegistroInvalidosError(f"{campo} inválido.")

    @staticmethod
    def _validar_coordenada(
        valor: Decimal | int | float,
        minimo: int,
        maximo: int,
        campo: str,
    ) -> Decimal:
        try:
            coordenada = valor if isinstance(valor, Decimal) else Decimal(str(valor))
        except (InvalidOperation, ValueError, TypeError):
            raise DadosRegistroInvalidosError(f"{campo.capitalize()} inválida.") from None

        if (
            not coordenada.is_finite()
            or not Decimal(minimo) <= coordenada <= Decimal(maximo)
        ):
            raise DadosRegistroInvalidosError(f"{campo.capitalize()} fora dos limites permitidos.")
        return coordenada

    @staticmethod
    def _normalizar_nome(nome: str | None) -> str | None:
        if nome is None:
            return None
        if not isinstance(nome, str):
            raise DadosRegistroInvalidosError("Nome inválido.")
        nome_normalizado = nome.strip()
        return nome_normalizado or None
