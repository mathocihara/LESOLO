from __future__ import annotations

from datetime import date
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class ContaResponse(UsuarioPublico):
    data_nascimento: date | None = None


class AtualizarContaRequest(SchemaEntrada):
    senha_atual: str = Field(min_length=1, max_length=1024)
    nome: str | None = Field(default=None, min_length=1, max_length=200)
    email: str | None = Field(default=None, min_length=3, max_length=320, pattern=_PADRAO_EMAIL)
    nova_senha: str | None = Field(default=None, min_length=8, max_length=1024)
    data_nascimento: date | None = None

    @field_validator("nome", "email", mode="before")
    @classmethod
    def remover_espacos_externos(cls, valor: object) -> object:
        return valor.strip() if isinstance(valor, str) else valor

    @model_validator(mode="after")
    def validar_alteracoes(self):
        alteracoes = self.model_fields_set - {"senha_atual"}
        if not alteracoes:
            raise ValueError("Informe ao menos um dado para atualizar.")
        if "nome" in alteracoes and self.nome is None:
            raise ValueError("O nome não pode ser vazio.")
        if "email" in alteracoes and self.email is None:
            raise ValueError("O e-mail não pode ser vazio.")
        return self

    def dados_para_atualizar(self) -> dict[str, object]:
        alteracoes = self.model_fields_set - {"senha_atual"}
        return {
            "nome": self.nome,
            "email": self.email,
            "nova_senha": self.nova_senha,
            "data_nascimento": self.data_nascimento,
            "atualizar_data": "data_nascimento" in alteracoes,
        }


class ExcluirContaRequest(SchemaEntrada):
    senha_atual: str = Field(min_length=1, max_length=1024)
    confirmacao: str = Field(pattern=r"^EXCLUIR$")
