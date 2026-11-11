
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.processamento_geo import consultar_coordenada


router = APIRouter(
    prefix="/api/consultas",
    tags=["Consultas Geoespaciais"]
)


class CoordenadaRequest(BaseModel):

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


@router.post("/consultar")
def realizar_consulta(dados: CoordenadaRequest):

    try:

        resultado = consultar_coordenada(
            latitude=dados.latitude,
            longitude=dados.longitude
        )

        return resultado

    except ValueError as erro:

        raise HTTPException(
            status_code=400,
            detail=str(erro)
        )
    