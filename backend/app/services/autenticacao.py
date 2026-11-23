from __future__ import annotations

import re
import secrets
import uuid

from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.sessao import Sessao
from app.models.usuario import Usuario
from app.repositories.sessao_repositorio import SessaoRepositorio
from app.repositories.usuario_repositorio import UsuarioRepositorio


class ErroAutenticacao(Exception):
    """Erro base para operações do serviço de autenticação."""


class DadosCadastroInvalidosError(ErroAutenticacao, ValueError):
    """Dados fornecidos para o cadastro não passaram pela validação."""


class EmailJaCadastradoError(ErroAutenticacao):
    """Não foi possível concluir o cadastro com os dados fornecidos."""


class CredenciaisInvalidasError(ErroAutenticacao):
    """E-mail ou senha inválidos."""


class SessaoInvalidaError(ErroAutenticacao):
    """A sessão não existe ou já está encerrada."""


_EMAIL_VALIDO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_TAMANHO_MINIMO_SENHA = 8
_TAMANHO_MAXIMO_SENHA = 1024
_MENSAGEM_CADASTRO_DUPLICADO = "Não foi possível concluir o cadastro com os dados fornecidos."
_MENSAGEM_CREDENCIAIS_INVALIDAS = "E-mail ou senha inválidos."
_MENSAGEM_SESSAO_INVALIDA = "Sessão inválida ou inativa."

_HASHER_SENHAS = PasswordHasher(
    time_cost=2,
    memory_cost=19_456,
    parallelism=1,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)
_HASH_DUMMY = _HASHER_SENHAS.hash(secrets.token_urlsafe(32))


def _email_ja_cadastrado(erro: IntegrityError) -> bool:
    origem = erro.orig
    diagnostico = getattr(origem, "diag", None)
    constraint = getattr(diagnostico, "constraint_name", None)
    if constraint == "usuarios_email_key":
        return True

    mensagem = str(origem).lower()
    return "unique constraint failed: usuarios.email" in mensagem


class ServicoAutenticacao:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao
        self._usuarios = UsuarioRepositorio(sessao)
        self._sessoes = SessaoRepositorio(sessao)

    def cadastrar(self, nome: str, email: str, senha: str) -> Usuario:
        try:
            nome_validado = self._validar_nome(nome)
            email_normalizado = self._normalizar_email(email)
            self._validar_senha(senha)

            if self._usuarios.buscar_por_email(email_normalizado) is not None:
                raise EmailJaCadastradoError(_MENSAGEM_CADASTRO_DUPLICADO)

            usuario = Usuario(
                nome=nome_validado,
                email=email_normalizado,
                senha_hash=_HASHER_SENHAS.hash(senha),
            )
            usuario = self._usuarios.salvar(usuario)
            self._sessao.commit()
            return usuario
        except EmailJaCadastradoError:
            self._sessao.rollback()
            raise
        except IntegrityError as erro:
            self._sessao.rollback()
            if _email_ja_cadastrado(erro):
                raise EmailJaCadastradoError(_MENSAGEM_CADASTRO_DUPLICADO) from None
            raise
        except Exception:
            self._sessao.rollback()
            raise

    def validarCredenciais(self, email: str, senha: str) -> Usuario:
        try:
            email_normalizado = self._normalizar_email(email)
        except DadosCadastroInvalidosError:
            raise CredenciaisInvalidasError(_MENSAGEM_CREDENCIAIS_INVALIDAS) from None

        usuario = self._usuarios.buscar_por_email(email_normalizado)
        if usuario is None:
            self._verificar_hash_dummy(senha)
            raise CredenciaisInvalidasError(_MENSAGEM_CREDENCIAIS_INVALIDAS)

        try:
            _HASHER_SENHAS.verify(usuario.senha_hash, senha)
        except (VerificationError, TypeError):
            raise CredenciaisInvalidasError(_MENSAGEM_CREDENCIAIS_INVALIDAS) from None
        return usuario

    def autenticar(self, email: str, senha: str) -> Sessao:
        try:
            usuario = self.validarCredenciais(email, senha)
            sessao = Sessao(
                usuario_id=usuario.id,
                persistente=False,
                ativa=True,
            )
            sessao = self._sessoes.salvar(sessao)
            self._sessao.commit()
            return sessao
        except Exception:
            self._sessao.rollback()
            raise

    def logout(self, sessaoId: uuid.UUID) -> None:
        try:
            if not isinstance(sessaoId, uuid.UUID):
                raise SessaoInvalidaError(_MENSAGEM_SESSAO_INVALIDA)

            sessao = self._sessoes.buscar_por_id(sessaoId)
            if sessao is None or not sessao.ativa:
                raise SessaoInvalidaError(_MENSAGEM_SESSAO_INVALIDA)

            if not self._sessoes.encerrar(sessaoId):
                raise SessaoInvalidaError(_MENSAGEM_SESSAO_INVALIDA)
            self._sessao.commit()
        except Exception:
            self._sessao.rollback()
            raise

    @staticmethod
    def _validar_nome(nome: str) -> str:
        if not isinstance(nome, str):
            raise DadosCadastroInvalidosError("Nome inválido.")
        nome_normalizado = nome.strip()
        if not nome_normalizado or len(nome_normalizado) > 200:
            raise DadosCadastroInvalidosError("Nome inválido.")
        return nome_normalizado

    @staticmethod
    def _normalizar_email(email: str) -> str:
        if not isinstance(email, str):
            raise DadosCadastroInvalidosError("E-mail inválido.")
        email_normalizado = email.strip().lower()
        if (
            len(email_normalizado) > 320
            or _EMAIL_VALIDO.fullmatch(email_normalizado) is None
        ):
            raise DadosCadastroInvalidosError("E-mail inválido.")
        return email_normalizado

    @staticmethod
    def _validar_senha(senha: str) -> None:
        if (
            not isinstance(senha, str)
            or not senha.strip()
            or not _TAMANHO_MINIMO_SENHA <= len(senha) <= _TAMANHO_MAXIMO_SENHA
        ):
            raise DadosCadastroInvalidosError("Senha inválida.")

    @staticmethod
    def _verificar_hash_dummy(senha: str) -> None:
        if not isinstance(senha, str):
            return
        try:
            _HASHER_SENHAS.verify(_HASH_DUMMY, senha)
        except VerificationError:
            pass
