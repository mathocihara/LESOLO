from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class AtualizarPreferenciasRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tema: Literal["escuro", "claro"] | None = None
    alto_contraste: bool | None = None
    notificacoes: bool | None = None

    @model_validator(mode="after")
    def requer_pelo_menos_uma_preferencia(self) -> AtualizarPreferenciasRequest:
        if self.tema is None and self.alto_contraste is None and self.notificacoes is None:
            raise ValueError("Informe ao menos uma preferência para atualizar.")
        return self


class PreferenciasResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tema: Literal["escuro", "claro"]
    alto_contraste: bool
    notificacoes: bool
