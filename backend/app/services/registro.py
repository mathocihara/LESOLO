from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy import select
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
_PRECISAO_COORDENADAS = Decimal("0.000001")
_STATUS_CONSULTA = {"COMPLETA", "PARCIAL", "SEM_RESULTADOS", "NAO_CLASSIFICADA"}


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

    def excluir_temporarios_vencidos(self, agora: datetime | None = None) -> int:
        """Remove registros temporários cujo prazo de retenção já terminou."""
        instante = agora or datetime.now(timezone.utc)
        try:
            vencidos = list(self._sessao.scalars(
                select(RegistroConsulta).where(
                    RegistroConsulta.status == StatusRegistro.TEMPORARIO,
                    RegistroConsulta.data_expiracao.is_not(None),
                    RegistroConsulta.data_expiracao <= instante,
                )
            ))
            for registro in vencidos:
                self._sessao.delete(registro)
            self._sessao.commit()
            return len(vencidos)
        except Exception:
            self._sessao.rollback()
            raise

    def criarTemporario(
        self,
        usuarioId: uuid.UUID,
        latitude: Decimal | int | float,
        longitude: Decimal | int | float,
        dadosGeograficos: DadosGeograficos,
        dataConsulta: datetime,
        *,
        statusConsulta: str = "COMPLETA",
        dadosAusentes: list[str] | None = None,
        falhasFontes: list[str] | None = None,
    ) -> RegistroConsulta:
        self._validar_uuid(usuarioId, "Usuário")
        latitude_validada = self._validar_coordenada(latitude, -90, 90, "latitude")
        longitude_validada = self._validar_coordenada(longitude, -180, 180, "longitude")
        if not isinstance(dadosGeograficos, DadosGeograficos):
            raise DadosRegistroInvalidosError("Dados geográficos inválidos.")
        if not isinstance(dataConsulta, datetime):
            raise DadosRegistroInvalidosError("Data da consulta inválida.")
        self._validar_status_consulta(statusConsulta)

        try:
            registro = RegistroConsulta(
                usuario_id=usuarioId,
                latitude=latitude_validada,
                longitude=longitude_validada,
                dados_geograficos=dadosGeograficos,
                data_consulta=dataConsulta,
                status=StatusRegistro.TEMPORARIO,
                data_expiracao=dataConsulta + self._prazo_expiracao_temporario,
                status_consulta=statusConsulta,
                dados_ausentes=list(dadosAusentes or []),
                falhas_fontes=list(falhasFontes or []),
                dados_desatualizados=[],
            )
            registro = self._repositorio.salvar(registro)
            self._sessao.commit()
            return registro
        except Exception:
            self._sessao.rollback()
            raise

    def buscarConsultasRepetidas(
        self,
        usuarioId: uuid.UUID,
        latitude: Decimal | int | float,
        longitude: Decimal | int | float,
    ) -> list[RegistroConsulta]:
        self._validar_uuid(usuarioId, "Usuário")
        latitude_validada = self._validar_coordenada(latitude, -90, 90, "latitude")
        longitude_validada = self._validar_coordenada(longitude, -180, 180, "longitude")
        return self._repositorio.buscar_por_coordenadas(
            usuarioId, latitude_validada, longitude_validada
        )

    def atualizarConsulta(
        self,
        registroId: uuid.UUID,
        usuarioId: uuid.UUID,
        latitude: Decimal | int | float,
        longitude: Decimal | int | float,
        dadosGeograficos: DadosGeograficos,
        dataConsulta: datetime,
        *,
        statusConsulta: str,
        dadosAusentes: list[str],
        falhasFontes: list[str],
    ) -> RegistroConsulta:
        self._validar_uuid(registroId, "Registro")
        self._validar_uuid(usuarioId, "Usuário")
        self._validar_status_consulta(statusConsulta)
        if not isinstance(dadosGeograficos, DadosGeograficos) or not isinstance(dataConsulta, datetime):
            raise DadosRegistroInvalidosError("Resultados da consulta inválidos.")
        latitude_validada = self._validar_coordenada(latitude, -90, 90, "latitude")
        longitude_validada = self._validar_coordenada(longitude, -180, 180, "longitude")
        campos = {
            "altitude_m": ("mde", "mde"),
            "declividade_percentual": ("declividade", "declividade"),
            "tipo_solo": ("tipo_solo", "tipo_solo"),
            "aptidao_agricola": ("aptidao_agricola", "aptidao_agricola"),
        }
        ausentes = set(dadosAusentes)
        self._validar_campos_consulta(ausentes | set(falhasFontes))
        try:
            registro = self._repositorio.buscar_por_id(registroId, usuarioId)
            if registro is None:
                raise RegistroConsultaNaoEncontradoError("Registro não encontrado para este usuário.")
            anteriores = registro.dados_geograficos
            novos = {}
            desatualizados = []
            for campo_api, (campo_anterior, campo_novo) in campos.items():
                valor_novo = getattr(dadosGeograficos, campo_novo)
                valor_anterior = getattr(anteriores, campo_anterior)
                if campo_api in ausentes:
                    novos[campo_novo] = valor_anterior
                    if valor_anterior is not None:
                        desatualizados.append(campo_api)
                else:
                    novos[campo_novo] = valor_novo
            registro.latitude = latitude_validada
            registro.longitude = longitude_validada
            registro.dados_geograficos = DadosGeograficos(**novos)
            registro.data_consulta = dataConsulta
            registro.status_consulta = statusConsulta
            registro.dados_ausentes = sorted(ausentes)
            registro.falhas_fontes = sorted(set(falhasFontes))
            registro.dados_desatualizados = desatualizados
            if registro.status == StatusRegistro.TEMPORARIO:
                registro.data_expiracao = dataConsulta + self._prazo_expiracao_temporario
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
        return coordenada.quantize(_PRECISAO_COORDENADAS, rounding=ROUND_HALF_UP)

    @staticmethod
    def _validar_status_consulta(status: str) -> None:
        if status not in _STATUS_CONSULTA:
            raise DadosRegistroInvalidosError("Estado da consulta inválido.")

    @staticmethod
    def _validar_campos_consulta(campos: set[str]) -> None:
        if not campos.issubset({"altitude_m", "declividade_percentual", "tipo_solo", "aptidao_agricola"}):
            raise DadosRegistroInvalidosError("A consulta contém nomes de dados inválidos.")

    @staticmethod
    def _normalizar_nome(nome: str | None) -> str | None:
        if nome is None:
            return None
        if not isinstance(nome, str):
            raise DadosRegistroInvalidosError("Nome inválido.")
        nome_normalizado = nome.strip()
        return nome_normalizado or None
