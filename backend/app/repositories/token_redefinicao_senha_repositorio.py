from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.token_redefinicao_senha import TokenRedefinicaoSenha


_HASH_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def _normalizar_hash_sha256(valor_hash: str) -> str:
    if not isinstance(valor_hash, str) or _HASH_SHA256.fullmatch(valor_hash) is None:
        raise ValueError("O token deve ser fornecido como hash SHA-256 hexadecimal.")
    return valor_hash.lower()


class TokenRedefinicaoSenhaRepositorio:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def salvar(self, token: TokenRedefinicaoSenha) -> TokenRedefinicaoSenha:
        token.valor_hash = _normalizar_hash_sha256(token.valor_hash)
        self._sessao.add(token)
        self._sessao.flush()
        return token

    def buscar_por_hash(self, valor_hash: str) -> TokenRedefinicaoSenha | None:
        hash_normalizado = _normalizar_hash_sha256(valor_hash)
        return self._sessao.scalar(
            select(TokenRedefinicaoSenha).where(
                TokenRedefinicaoSenha.valor_hash == hash_normalizado
            )
        )
