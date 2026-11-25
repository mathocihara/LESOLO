from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.conexao import obter_sessao
from app.models.registro_consulta import StatusRegistro
from app.models.sessao import Sessao
from app.routes.dependencias import obter_sessao_autenticada, validar_origem_requisicao
from app.schemas.historico import (
    ExclusaoHistoricoResponse,
    RegistroHistoricoResponse,
    SalvarRegistroRequest,
)
from app.services.registro import (
    RegistroConsultaNaoEncontradoError,
    ServicoRegistro,
)
from app.models.registro_consulta import DadosGeograficos


router = APIRouter(prefix="/api/historico", tags=["Histórico"])


class CriarRegistroTemporarioRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    altitude_m: float | None = None
    declividade_percentual: float | None = None
    tipo_solo: str | None = None
    aptidao_agricola: str | None = None


@router.post(
    "/temporario",
    response_model=RegistroHistoricoResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_registro_temporario(
    dados: CriarRegistroTemporarioRequest,
    sessao: Sessao = Depends(obter_sessao_autenticada),
    _validacao_origem: None = Depends(validar_origem_requisicao),
    sessao_banco: Session = Depends(obter_sessao),
) -> RegistroHistoricoResponse:
    registro = ServicoRegistro(sessao_banco).criarTemporario(
        sessao.usuario_id,
        Decimal(str(dados.latitude)),
        Decimal(str(dados.longitude)),
        DadosGeograficos(
            Decimal(str(dados.altitude_m)) if dados.altitude_m is not None else None,
            Decimal(str(dados.declividade_percentual))
            if dados.declividade_percentual is not None
            else None,
            dados.tipo_solo,
            dados.aptidao_agricola,
        ),
        datetime.now(timezone.utc),
    )
    return RegistroHistoricoResponse.model_validate(registro)


@router.get("", response_model=list[RegistroHistoricoResponse])
def listar_historico(
    status_registro: StatusRegistro | None = Query(
        default=StatusRegistro.PERMANENTE,
        alias="status",
    ),
    sessao: Sessao = Depends(obter_sessao_autenticada),
    sessao_banco: Session = Depends(obter_sessao),
) -> list[RegistroHistoricoResponse]:
    registros = ServicoRegistro(sessao_banco).listarRegistrosDoUsuario(
        sessao.usuario_id,
        status=status_registro,
    )
    return [RegistroHistoricoResponse.model_validate(registro) for registro in registros]


@router.get("/{registro_id}", response_model=RegistroHistoricoResponse)
def buscar_registro(
    registro_id: uuid.UUID,
    sessao: Sessao = Depends(obter_sessao_autenticada),
    sessao_banco: Session = Depends(obter_sessao),
) -> RegistroHistoricoResponse:
    try:
        registro = ServicoRegistro(sessao_banco).buscarRegistro(
            registro_id,
            sessao.usuario_id,
            status=None,
        )
    except RegistroConsultaNaoEncontradoError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro não encontrado.",
        ) from erro
    return RegistroHistoricoResponse.model_validate(registro)


@router.post(
    "/{registro_id}/salvar",
    response_model=RegistroHistoricoResponse,
)
def salvar_registro(
    registro_id: uuid.UUID,
    dados: SalvarRegistroRequest | None = None,
    sessao: Sessao = Depends(obter_sessao_autenticada),
    _validacao_origem: None = Depends(validar_origem_requisicao),
    sessao_banco: Session = Depends(obter_sessao),
) -> RegistroHistoricoResponse:
    try:
        registro = ServicoRegistro(sessao_banco).salvarComoPermanente(
            registro_id,
            sessao.usuario_id,
            dados.nome if dados is not None else None,
        )
    except RegistroConsultaNaoEncontradoError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro não encontrado.",
        ) from erro
    return RegistroHistoricoResponse.model_validate(registro)


@router.delete("/{registro_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_registro(
    registro_id: uuid.UUID,
    sessao: Sessao = Depends(obter_sessao_autenticada),
    _validacao_origem: None = Depends(validar_origem_requisicao),
    sessao_banco: Session = Depends(obter_sessao),
) -> Response:
    try:
        ServicoRegistro(sessao_banco).excluirRegistro(registro_id, sessao.usuario_id)
    except RegistroConsultaNaoEncontradoError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro não encontrado.",
        ) from erro
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("", response_model=ExclusaoHistoricoResponse)
def excluir_historico(
    sessao: Sessao = Depends(obter_sessao_autenticada),
    _validacao_origem: None = Depends(validar_origem_requisicao),
    sessao_banco: Session = Depends(obter_sessao),
) -> ExclusaoHistoricoResponse:
    quantidade = ServicoRegistro(sessao_banco).excluirHistoricoDoUsuario(sessao.usuario_id)
    return ExclusaoHistoricoResponse(excluidos=quantidade)
