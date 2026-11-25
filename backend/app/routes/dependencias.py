"""Validação de sessões de servidor carregadas por cookie HttpOnly.

O modelo de sessão não define expiração no banco. O cookie é de sessão do
navegador e usa SameSite=Lax; não há token CSRF independente nesta etapa.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.conexao import obter_sessao
from app.models.sessao import Sessao
from app.repositories.sessao_repositorio import SessaoRepositorio
from app.services.autenticacao import ServicoAutenticacao, SessaoInvalidaError


NOME_COOKIE_SESSAO = "lesolo_sessao"


def obter_sessao_autenticada(
    response: Response,
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
        raise _erro_sessao_invalida(response)
    if _sessao_expirada(sessao):
        try:
            ServicoAutenticacao(sessao_banco).logout(sessao.id)
        except SessaoInvalidaError:
            pass
        raise _erro_sessao_invalida(response)
    # Qualquer acesso autenticado dentro dos 30 dias recupera a conta.
    solicitada_em = sessao.usuario.exclusao_solicitada_em
    if solicitada_em is not None:
        if solicitada_em.tzinfo is None:
            solicitada_em = solicitada_em.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) >= solicitada_em + timedelta(days=30):
            sessao.ativa = False
            sessao_banco.commit()
            raise _erro_sessao_invalida(response)
        sessao.usuario.exclusao_solicitada_em = None
        sessao_banco.commit()
    return sessao


def _erro_sessao_invalida(response: Response) -> HTTPException:
    response.delete_cookie(
        key=NOME_COOKIE_SESSAO,
        path="/",
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
    )
    cookie = response.headers.get("set-cookie")
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autenticação necessária.",
        headers={"set-cookie": cookie} if cookie else None,
    )


def validar_origem_requisicao(request: Request) -> None:
    """Bloqueia mutações sem Origin igual à origem confiável configurada."""
    if request.method.upper() in {"GET", "HEAD", "OPTIONS"}:
        return

    origem = request.headers.get("origin")
    if origem not in settings.frontend_origins():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Origem não autorizada para esta operação.",
        )

    if request.headers.get("sec-fetch-site", "").casefold() == "cross-site":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Origem não autorizada para esta operação.",
        )


def _sessao_expirada(sessao: Sessao) -> bool:
    data_criacao = sessao.data_criacao
    if data_criacao is None:
        return True
    if data_criacao.tzinfo is None:
        data_criacao = data_criacao.replace(tzinfo=timezone.utc)
    validade = timedelta(seconds=settings.SESSION_TTL_SECONDS)
    return datetime.now(timezone.utc) >= data_criacao + validade
