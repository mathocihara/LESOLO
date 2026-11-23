from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database.conexao import obter_sessao
from app.models.registro_consulta import StatusRegistro
from app.models.sessao import Sessao
from app.routes.dependencias import obter_sessao_autenticada
from app.schemas.historico import (
    ExclusaoHistoricoResponse,
    RegistroHistoricoResponse,
    SalvarRegistroRequest,
)
from app.services.registro import (
    RegistroConsultaNaoEncontradoError,
    ServicoRegistro,
)


router = APIRouter(prefix="/api/historico", tags=["Histórico"])


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
    sessao_banco: Session = Depends(obter_sessao),
) -> ExclusaoHistoricoResponse:
    quantidade = ServicoRegistro(sessao_banco).excluirHistoricoDoUsuario(sessao.usuario_id)
    return ExclusaoHistoricoResponse(excluidos=quantidade)
