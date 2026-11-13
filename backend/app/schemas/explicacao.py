
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SchemaBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConsultaGeoespacial(SchemaBase):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    altitude_m: float | None = Field(
        default=None,
        allow_inf_nan=False
    )

    declividade_percentual: float | None = Field(
        default=None,
        allow_inf_nan=False
    )

    tipo_solo: str | None = None
    aptidao_agricola: str | None = None


class ExplicacaoRequest(SchemaBase):
    consulta: ConsultaGeoespacial


class ReferenciaTecnica(SchemaBase):
    titulo: str
    origem: str
    trecho_utilizado: str

    @field_validator("titulo", "origem", "trecho_utilizado")
    @classmethod
    def texto_obrigatorio(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O campo não pode estar vazio.")
        return value


class ExplicacaoConteudo(SchemaBase):
    dados_recebidos: str
    interpretacao_aptidao: str
    relacao_variaveis_geoespaciais: str
    implicacoes_praticas: str
    limitacoes: str

    @field_validator(
        "dados_recebidos",
        "interpretacao_aptidao",
        "relacao_variaveis_geoespaciais",
        "implicacoes_praticas",
        "limitacoes",
    )
    @classmethod
    def texto_obrigatorio(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A seção da explicação não pode estar vazia.")
        return value


class ExplicacaoResponse(SchemaBase):
    status: Literal["concluida", "parcial"]

    explicacao: ExplicacaoConteudo

    referencias: list[ReferenciaTecnica] = Field(
        default_factory=list
    )

    avisos: list[str] = Field(
        default_factory=list
    )

