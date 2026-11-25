from __future__ import annotations

import re
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone

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


class DadosContaInvalidosError(ErroAutenticacao, ValueError):
    """Dados de conta invÃ¡lidos ou senha atual incorreta."""


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
            if self._solicitacao_exclusao_vencida(usuario):
                raise CredenciaisInvalidasError(_MENSAGEM_CREDENCIAIS_INVALIDAS)
            # Um novo login é uso da conta e cancela a solicitação pendente.
            if usuario.exclusao_solicitada_em is not None:
                usuario.exclusao_solicitada_em = None
            sessao = Sessao(
                usuario_id=usuario.id,
                persistente=True,
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

    def atualizar_conta(
        self,
        usuario_id: uuid.UUID,
        senha_atual: str,
        *,
        nome: str | None = None,
        email: str | None = None,
        nova_senha: str | None = None,
        data_nascimento: date | None = None,
        atualizar_data: bool = False,
    ) -> Usuario:
        usuario = self._usuarios.buscar_por_id(usuario_id)
        if usuario is None:
            raise CredenciaisInvalidasError(_MENSAGEM_CREDENCIAIS_INVALIDAS)
        try:
            self.validarCredenciais(usuario.email, senha_atual)
        except CredenciaisInvalidasError:
            raise DadosContaInvalidosError("Senha atual incorreta.") from None

        try:
            if nome is not None:
                usuario.nome = self._validar_nome(nome)
            if email is not None:
                email_validado = self._normalizar_email(email)
                if self._usuarios.buscar_por_email_de_outro_usuario(email_validado, usuario_id):
                    raise DadosContaInvalidosError("NÃ£o foi possÃ­vel atualizar os dados da conta.")
                usuario.email = email_validado
            if nova_senha is not None:
                self._validar_senha(nova_senha)
                usuario.senha_hash = _HASHER_SENHAS.hash(nova_senha)
            if atualizar_data:
                if data_nascimento is not None and data_nascimento > date.today():
                    raise DadosContaInvalidosError("A data deve ser vÃ¡lida e nÃ£o pode estar no futuro.")
                usuario.data_nascimento = data_nascimento
            self._sessao.commit()
            return usuario
        except (DadosCadastroInvalidosError, DadosContaInvalidosError):
            self._sessao.rollback()
            raise
        except IntegrityError as erro:
            self._sessao.rollback()
            if _email_ja_cadastrado(erro):
                raise DadosContaInvalidosError("NÃ£o foi possÃ­vel atualizar os dados da conta.") from None
            raise
        except Exception:
            self._sessao.rollback()
            raise

    def excluir_conta(self, usuario_id: uuid.UUID, senha_atual: str) -> datetime:
        usuario = self._usuarios.buscar_por_id(usuario_id)
        if usuario is None:
            raise CredenciaisInvalidasError(_MENSAGEM_CREDENCIAIS_INVALIDAS)
        try:
            self.validarCredenciais(usuario.email, senha_atual)
        except CredenciaisInvalidasError:
            raise DadosContaInvalidosError("Senha atual incorreta.") from None
        try:
            agora = datetime.now(timezone.utc)
            usuario.exclusao_solicitada_em = agora
            self._sessao.commit()
            return agora
        except Exception:
            self._sessao.rollback()
            raise

    def excluir_contas_vencidas(self, agora: datetime | None = None) -> int:
        """Remove contas com solicitação ativa há pelo menos 30 dias."""
        from sqlalchemy import select

        instante = agora or datetime.now(timezone.utc)
        limite = instante - timedelta(days=30)
        usuarios = list(self._sessao.scalars(
            select(Usuario).where(Usuario.exclusao_solicitada_em <= limite)
        ))
        try:
            for usuario in usuarios:
                self._usuarios.excluir(usuario)
            self._sessao.commit()
            return len(usuarios)
        except Exception:
            self._sessao.rollback()
            raise

    @staticmethod
    def _solicitacao_exclusao_vencida(usuario: Usuario) -> bool:
        solicitada_em = usuario.exclusao_solicitada_em
        if solicitada_em is None:
            return False
        if solicitada_em.tzinfo is None:
            solicitada_em = solicitada_em.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= solicitada_em + timedelta(days=30)

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
