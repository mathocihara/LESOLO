from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.registro_consulta import StatusRegistro


class RegistroHistoricoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str | None
    latitude: Decimal
    longitude: Decimal
    data_consulta: datetime
    altitude_m: Decimal | None
    declividade_percentual: Decimal | None
    tipo_solo: str | None
    aptidao_agricola: str | None
    status: StatusRegistro
    data_expiracao: datetime | None


class ExclusaoHistoricoResponse(BaseModel):
    excluidos: int


class SalvarRegistroRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str | None = Field(default=None, max_length=250)

    @field_validator("nome")
    @classmethod
    def remover_espacos_externos(cls, valor: str | None) -> str | None:
        return valor.strip() if valor is not None else None
