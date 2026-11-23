from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.conexao import obter_sessao
from app.models.sessao import Sessao
from app.schemas.autenticacao import CadastroRequest, LoginRequest, UsuarioPublico
from app.services.autenticacao import (
    CredenciaisInvalidasError,
    DadosCadastroInvalidosError,
    EmailJaCadastradoError,
    ServicoAutenticacao,
    SessaoInvalidaError,
)
from app.routes.dependencias import NOME_COOKIE_SESSAO, obter_sessao_autenticada
from app.repositories.usuario_repositorio import UsuarioRepositorio


router = APIRouter(prefix="/api/usuarios", tags=["Usuários"])


@router.post(
    "/cadastro",
    response_model=UsuarioPublico,
    status_code=status.HTTP_201_CREATED,
)
def cadastrar(
    dados: CadastroRequest,
    sessao_banco: Session = Depends(obter_sessao),
) -> UsuarioPublico:
    try:
        usuario = ServicoAutenticacao(sessao_banco).cadastrar(
            nome=dados.nome,
            email=dados.email,
            senha=dados.senha,
        )
    except EmailJaCadastradoError as erro:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não foi possível concluir o cadastro com os dados fornecidos.",
        ) from erro
    except DadosCadastroInvalidosError as erro:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(erro),
        ) from erro
    return UsuarioPublico.model_validate(usuario)


@router.post("/login", response_model=UsuarioPublico)
def login(
    dados: LoginRequest,
    response: Response,
    sessao_banco: Session = Depends(obter_sessao),
) -> UsuarioPublico:
    try:
        sessao = ServicoAutenticacao(sessao_banco).autenticar(
            email=dados.email,
            senha=dados.senha,
        )
    except CredenciaisInvalidasError as erro:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
        ) from erro

    # A sessão usa armazenamento no servidor; o ID fica somente no cookie HttpOnly.
    usuario = UsuarioRepositorio(sessao_banco).buscar_por_id(sessao.usuario_id)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível concluir a autenticação.",
        )

    response.set_cookie(
        key=NOME_COOKIE_SESSAO,
        value=str(sessao.id),
        httponly=True,
        secure=settings.APP_ENV.lower() not in {"development", "test"},
        samesite="lax",
        path="/",
    )
    return UsuarioPublico.model_validate(usuario)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    sessao: Sessao = Depends(obter_sessao_autenticada),
    sessao_banco: Session = Depends(obter_sessao),
) -> Response:
    try:
        ServicoAutenticacao(sessao_banco).logout(sessao.id)
    except SessaoInvalidaError as erro:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária.",
        ) from erro
    response.delete_cookie(key=NOME_COOKIE_SESSAO, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
