from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.preferencia_usuario import PreferenciaUsuario
from app.repositories.preferencia_usuario_repositorio import PreferenciaUsuarioRepositorio


class DadosPreferenciasInvalidosError(ValueError):
    """Valor inválido fornecido para as preferências do usuário."""


class ServicoPreferenciasUsuario:
    TEMA_PADRAO = "escuro"
    ALTO_CONTRASTE_PADRAO = False
    NOTIFICACOES_PADRAO = False
    TEMAS_VALIDOS = frozenset({"escuro", "claro"})

    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao
        self._repositorio = PreferenciaUsuarioRepositorio(sessao)

    def buscar(self, usuarioId: uuid.UUID) -> PreferenciaUsuario:
        self._validar_usuario_id(usuarioId)
        preferencia = self._repositorio.buscar_por_usuario(usuarioId)
        if preferencia is not None:
            return preferencia

        try:
            preferencia = self._repositorio.salvar(self._criar_padrao(usuarioId))
            self._sessao.commit()
            return preferencia
        except IntegrityError:
            # Outra transação pode ter criado a preferência simultaneamente.
            self._sessao.rollback()
            preferencia = self._repositorio.buscar_por_usuario(usuarioId)
            if preferencia is not None:
                return preferencia
            raise
        except Exception:
            self._sessao.rollback()
            raise

    def buscarOuCriarPadrao(self, usuarioId: uuid.UUID) -> PreferenciaUsuario:
        return self.buscar(usuarioId)

    def atualizar(
        self,
        usuarioId: uuid.UUID,
        *,
        tema: str | None = None,
        altoContraste: bool | None = None,
        notificacoes: bool | None = None,
    ) -> PreferenciaUsuario:
        self._validar_usuario_id(usuarioId)
        tema_validado = self._validar_tema(tema) if tema is not None else None
        alto_contraste_validado = (
            self._validar_booleano(altoContraste, "alto contraste")
            if altoContraste is not None
            else None
        )
        notificacoes_validadas = (
            self._validar_booleano(notificacoes, "notificações")
            if notificacoes is not None
            else None
        )

        try:
            if self._repositorio.buscar_por_usuario(usuarioId) is None:
                self._repositorio.salvar(self._criar_padrao(usuarioId))

            preferencia = self._repositorio.atualizar(
                usuarioId,
                tema=tema_validado,
                alto_contraste=alto_contraste_validado,
                notificacoes=notificacoes_validadas,
            )
            if preferencia is None:
                raise RuntimeError("A preferência do usuário não foi encontrada após a criação.")

            self._sessao.commit()
            return preferencia
        except Exception:
            self._sessao.rollback()
            raise

    def atualizarTema(self, usuarioId: uuid.UUID, tema: str) -> PreferenciaUsuario:
        return self.atualizar(usuarioId, tema=tema)

    def definirAltoContraste(
        self, usuarioId: uuid.UUID, ativo: bool
    ) -> PreferenciaUsuario:
        return self.atualizar(usuarioId, altoContraste=ativo)

    def definirNotificacoes(
        self, usuarioId: uuid.UUID, ativo: bool
    ) -> PreferenciaUsuario:
        return self.atualizar(usuarioId, notificacoes=ativo)

    @staticmethod
    def _validar_usuario_id(usuarioId: uuid.UUID) -> None:
        if not isinstance(usuarioId, uuid.UUID):
            raise DadosPreferenciasInvalidosError("UUID do usuário inválido.")

    @classmethod
    def _criar_padrao(cls, usuarioId: uuid.UUID) -> PreferenciaUsuario:
        return PreferenciaUsuario(
            usuario_id=usuarioId,
            tema=cls.TEMA_PADRAO,
            alto_contraste=cls.ALTO_CONTRASTE_PADRAO,
            notificacoes=cls.NOTIFICACOES_PADRAO,
        )

    @classmethod
    def _validar_tema(cls, tema: str) -> str:
        if not isinstance(tema, str):
            raise DadosPreferenciasInvalidosError("Tema inválido.")
        tema_normalizado = tema.strip().lower()
        if tema_normalizado not in cls.TEMAS_VALIDOS:
            raise DadosPreferenciasInvalidosError("Tema deve ser 'escuro' ou 'claro'.")
        return tema_normalizado

    @staticmethod
    def _validar_booleano(valor: bool, campo: str) -> bool:
        if not isinstance(valor, bool):
            raise DadosPreferenciasInvalidosError(f"Valor inválido para {campo}.")
        return valor
