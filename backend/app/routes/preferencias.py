from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.conexao import obter_sessao
from app.models.sessao import Sessao
from app.routes.dependencias import obter_sessao_autenticada
from app.schemas.preferencias import (
    AtualizarPreferenciasRequest,
    PreferenciasResponse,
)
from app.services.preferencias_usuario import ServicoPreferenciasUsuario


router = APIRouter(prefix="/api/preferencias", tags=["Preferências"])


@router.get("", response_model=PreferenciasResponse)
def buscar_preferencias(
    sessao: Sessao = Depends(obter_sessao_autenticada),
    sessao_banco: Session = Depends(obter_sessao),
) -> PreferenciasResponse:
    preferencia = ServicoPreferenciasUsuario(sessao_banco).buscar(sessao.usuario_id)
    return PreferenciasResponse.model_validate(preferencia)


@router.put("", response_model=PreferenciasResponse)
def atualizar_preferencias(
    dados: AtualizarPreferenciasRequest,
    sessao: Sessao = Depends(obter_sessao_autenticada),
    sessao_banco: Session = Depends(obter_sessao),
) -> PreferenciasResponse:
    preferencia = ServicoPreferenciasUsuario(sessao_banco).atualizar(
        sessao.usuario_id,
        tema=dados.tema,
        altoContraste=dados.alto_contraste,
        notificacoes=dados.notificacoes,
    )
    return PreferenciasResponse.model_validate(preferencia)
