from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


_PADRAO_EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class SchemaEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CadastroRequest(SchemaEntrada):
    nome: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320, pattern=_PADRAO_EMAIL)
    senha: str = Field(min_length=8, max_length=1024)

    @field_validator("nome", "email", mode="before")
    @classmethod
    def remover_espacos_externos(cls, valor: object) -> object:
        return valor.strip() if isinstance(valor, str) else valor


class LoginRequest(SchemaEntrada):
    email: str = Field(min_length=3, max_length=320, pattern=_PADRAO_EMAIL)
    senha: str = Field(min_length=1, max_length=1024)

    @field_validator("email", mode="before")
    @classmethod
    def remover_espacos_externos(cls, valor: object) -> object:
        return valor.strip() if isinstance(valor, str) else valor


class UsuarioPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nome: str
    email: str
