from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.database.conexao import obter_sessao
from app.models.registro_consulta import DadosGeograficos
from app.models.sessao import Sessao
from app.routes.dependencias import obter_sessao_autenticada
from app.schemas.historico import RegistroHistoricoResponse
from app.services.processamento_geo import consultar_coordenada
from app.services.registro import RegistroConsultaNaoEncontradoError, ServicoRegistro


router = APIRouter(prefix="/api/consultas", tags=["Consultas Geoespaciais"])


class CoordenadaRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    acao_repeticao: Literal["NOVO", "ATUALIZAR"] | None = None
    registro_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validar_decisao_repeticao(self):
        if (self.acao_repeticao == "ATUALIZAR") != (self.registro_id is not None):
            raise ValueError("Selecione um registro ao escolher atualizá-lo.")
        return self


@router.post("/consultar")
def realizar_consulta(
    dados: CoordenadaRequest,
    sessao: Sessao = Depends(obter_sessao_autenticada),
    sessao_banco: Session = Depends(obter_sessao),
):
    servico_registro = ServicoRegistro(sessao_banco)
    try:
        repetidas = servico_registro.buscarConsultasRepetidas(
            sessao.usuario_id, dados.latitude, dados.longitude
        )
        if repetidas and dados.acao_repeticao is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "CONSULTA_REPETIDA",
                    "message": "Já existem consultas para essas coordenadas. Escolha criar um registro ou atualizar um existente.",
                    "registros": [
                        RegistroHistoricoResponse.model_validate(item).model_dump(mode="json")
                        for item in repetidas
                    ],
                },
            )
        if not repetidas and dados.acao_repeticao == "ATUALIZAR":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "CONSULTA_REPETIDA_DESATUALIZADA",
                    "message": "A lista de registros mudou. Tente consultar novamente.",
                },
            )

        registro_existente = None
        if dados.acao_repeticao == "ATUALIZAR":
            registro_existente = next(
                (item for item in repetidas if item.id == dados.registro_id), None
            )
            if registro_existente is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="O registro selecionado não pertence a esta conta ou não corresponde mais às coordenadas.",
                )

        resultado = consultar_coordenada(dados.latitude, dados.longitude)
        geografia = DadosGeograficos(
            mde=Decimal(str(resultado["altitude_m"])) if resultado["altitude_m"] is not None else None,
            declividade=Decimal(str(resultado["declividade_percentual"]))
            if resultado["declividade_percentual"] is not None
            else None,
            tipo_solo=resultado["tipo_solo"],
            aptidao_agricola=resultado["aptidao_agricola"],
        )
        agora = datetime.now(timezone.utc)
        if registro_existente is not None:
            registro = servico_registro.atualizarConsulta(
                registro_existente.id,
                sessao.usuario_id,
                dados.latitude,
                dados.longitude,
                geografia,
                agora,
                statusConsulta=resultado["status_consulta"],
                dadosAusentes=resultado["dados_ausentes"],
                falhasFontes=resultado["falhas_fontes"],
            )
        else:
            registro = servico_registro.criarTemporario(
                usuarioId=sessao.usuario_id,
                latitude=dados.latitude,
                longitude=dados.longitude,
                dadosGeograficos=geografia,
                dataConsulta=agora,
                statusConsulta=resultado["status_consulta"],
                dadosAusentes=resultado["dados_ausentes"],
                falhasFontes=resultado["falhas_fontes"],
            )
        resposta = {
            **resultado,
            "id": str(registro.id),
            "status": registro.status.value,
            "status_consulta": registro.status_consulta,
            "dados_ausentes": registro.dados_ausentes,
            "falhas_fontes": registro.falhas_fontes,
            "dados_desatualizados": registro.dados_desatualizados,
        }
        resposta.update({
            "altitude_m": float(registro.altitude_m) if registro.altitude_m is not None else None,
            "declividade_percentual": float(registro.declividade_percentual)
            if registro.declividade_percentual is not None
            else None,
            "tipo_solo": registro.tipo_solo,
            "aptidao_agricola": registro.aptidao_agricola,
        })
        return resposta
    except HTTPException:
        raise
    except RegistroConsultaNaoEncontradoError as erro:
        raise HTTPException(status_code=404, detail="Registro não encontrado para esta conta.") from erro
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro
