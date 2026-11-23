"""Validação de sessões de servidor carregadas por cookie HttpOnly.

O modelo de sessão não define expiração no banco. O cookie é de sessão do
navegador e usa SameSite=Lax; não há token CSRF independente nesta etapa.
"""

from __future__ import annotations

import uuid

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.conexao import obter_sessao
from app.models.sessao import Sessao
from app.repositories.sessao_repositorio import SessaoRepositorio


NOME_COOKIE_SESSAO = "lesolo_sessao"


def obter_sessao_autenticada(
    valor_cookie: str | None = Cookie(default=None, alias=NOME_COOKIE_SESSAO),
    sessao_banco: Session = Depends(obter_sessao),
) -> Sessao:
    try:
        sessao_id = uuid.UUID(valor_cookie) if valor_cookie is not None else None
    except (ValueError, TypeError):
        sessao_id = None

    sessao = (
        SessaoRepositorio(sessao_banco).buscar_por_id(sessao_id)
        if sessao_id is not None
        else None
    )
    if sessao is None or not sessao.ativa:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária.",
        )
    return sessao
