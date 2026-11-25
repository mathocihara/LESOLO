from fastapi import APIRouter, Depends, HTTPException, Response, status
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.conexao import obter_sessao
from app.models.sessao import Sessao
from app.schemas.autenticacao import (
    AtualizarContaRequest,
    CadastroRequest,
    ContaResponse,
    ExcluirContaRequest,
    LoginRequest,
    UsuarioPublico,
)
from app.services.autenticacao import (
    CredenciaisInvalidasError,
    DadosContaInvalidosError,
    DadosCadastroInvalidosError,
    EmailJaCadastradoError,
    ServicoAutenticacao,
    SessaoInvalidaError,
)
from app.routes.dependencias import (
    NOME_COOKIE_SESSAO,
    obter_sessao_autenticada,
    validar_origem_requisicao,
)
from app.repositories.usuario_repositorio import UsuarioRepositorio


router = APIRouter(
    prefix="/api/usuarios",
    tags=["Usuários"],
    dependencies=[Depends(validar_origem_requisicao)],
)


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
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
        max_age=settings.SESSION_TTL_SECONDS,
        expires=datetime.now(timezone.utc) + timedelta(seconds=settings.SESSION_TTL_SECONDS),
    )
    return UsuarioPublico.model_validate(usuario)


@router.get("/me", response_model=ContaResponse)
def usuario_atual(
    sessao: Sessao = Depends(obter_sessao_autenticada),
    sessao_banco: Session = Depends(obter_sessao),
) -> ContaResponse:
    usuario = UsuarioRepositorio(sessao_banco).buscar_por_id(sessao.usuario_id)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária.",
        )
    return ContaResponse.model_validate(usuario)


@router.patch("/me", response_model=ContaResponse)
def atualizar_conta(
    dados: AtualizarContaRequest,
    sessao: Sessao = Depends(obter_sessao_autenticada),
    sessao_banco: Session = Depends(obter_sessao),
) -> ContaResponse:
    try:
        atualizacao = dados.dados_para_atualizar()
        usuario = ServicoAutenticacao(sessao_banco).atualizar_conta(
            sessao.usuario_id,
            dados.senha_atual,
            **atualizacao,
        )
    except DadosContaInvalidosError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro)) from erro
    except DadosCadastroInvalidosError as erro:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(erro)) from erro
    return ContaResponse.model_validate(usuario)


@router.delete("/me", status_code=status.HTTP_202_ACCEPTED)
def excluir_conta(
    dados: ExcluirContaRequest,
    response: Response,
    sessao: Sessao = Depends(obter_sessao_autenticada),
    sessao_banco: Session = Depends(obter_sessao),
) -> dict[str, str]:
    try:
        solicitada_em = ServicoAutenticacao(sessao_banco).excluir_conta(
            sessao.usuario_id, dados.senha_atual
        )
    except DadosContaInvalidosError as erro:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(erro)) from erro
    return {
        "status": "solicitada",
        "exclusao_solicitada_em": solicitada_em.isoformat(),
        "mensagem": "A conta será excluída definitivamente após 30 dias sem acesso. Um novo acesso cancela a solicitação.",
    }


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
