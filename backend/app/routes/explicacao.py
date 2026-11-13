import logging

from fastapi import APIRouter, HTTPException

from app.schemas.explicacao import ExplicacaoRequest, ExplicacaoResponse
from app.services.ia.principal import gerar_explicacao


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/explicacao", tags=["Inteligência Artificial"])


@router.post("", response_model=ExplicacaoResponse)
def solicitar_explicacao(dados: ExplicacaoRequest) -> ExplicacaoResponse:
    try:
        return gerar_explicacao(dados)
    except (RuntimeError, ValueError) as erro:
        logger.warning("Falha na geração de explicação: %s", erro)
        raise HTTPException(status_code=503, detail=str(erro)) from erro
    except Exception as erro:
        logger.exception("Erro inesperado ao gerar explicação")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao gerar a explicação.",
        ) from erro
