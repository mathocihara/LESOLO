import unittest
import uuid
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.conexao import Base
from app.models import Usuario
from app.services.autenticacao import (
    CredenciaisInvalidasError,
    DadosCadastroInvalidosError,
    EmailJaCadastradoError,
    ServicoAutenticacao,
    SessaoInvalidaError,
)


class TesteServicoAutenticacao(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        fabrica_sessoes = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )
        self.sessao: Session = fabrica_sessoes()
        self.servico = ServicoAutenticacao(self.sessao)

    def tearDown(self) -> None:
        self.sessao.rollback()
        self.sessao.close()
        self.engine.dispose()

    def _cadastrar_usuario(self) -> Usuario:
        return self.servico.cadastrar("Pessoa Teste", "pessoa@example.test", "senha-segura-123")

    def test_cadastro_valido_normaliza_email_e_armazena_hash_argon2id(self) -> None:
        usuario = self.servico.cadastrar(
            "  Pessoa Teste  ", "  Pessoa@Example.Test ", "senha-segura-123"
        )

        self.assertEqual(usuario.nome, "Pessoa Teste")
        self.assertEqual(usuario.email, "pessoa@example.test")
        self.assertTrue(usuario.senha_hash.startswith("$argon2id$"))
        self.assertNotEqual(usuario.senha_hash, "senha-segura-123")
        self.assertTrue(PasswordHasher().verify(usuario.senha_hash, "senha-segura-123"))

    def test_cadastro_rejeita_email_duplicado_sem_incluir_email_na_mensagem(self) -> None:
        self._cadastrar_usuario()

        with self.assertRaises(EmailJaCadastradoError) as erro:
            self.servico.cadastrar("Outra Pessoa", " PESSOA@example.test ", "outra-senha-123")

        self.assertNotIn("pessoa@example.test", str(erro.exception))

    def test_cadastro_valida_dados(self) -> None:
        with self.assertRaises(DadosCadastroInvalidosError):
            self.servico.cadastrar("   ", "pessoa@example.test", "senha-segura-123")
        with self.assertRaises(DadosCadastroInvalidosError):
            self.servico.cadastrar("Pessoa", "email-invalido", "senha-segura-123")
        with self.assertRaises(DadosCadastroInvalidosError):
            self.servico.cadastrar("Pessoa", "pessoa@example.test", "curta")

    def test_login_correto_retorna_usuario(self) -> None:
        usuario_cadastrado = self._cadastrar_usuario()

        usuario = self.servico.validarCredenciais(" PESSOA@example.test ", "senha-segura-123")

        self.assertEqual(usuario.id, usuario_cadastrado.id)

    def test_senha_incorreta_e_email_inexistente_usam_mesmo_erro(self) -> None:
        self._cadastrar_usuario()

        with self.assertRaises(CredenciaisInvalidasError) as senha_incorreta:
            self.servico.validarCredenciais("pessoa@example.test", "senha-errada-123")
        with self.assertRaises(CredenciaisInvalidasError) as email_inexistente:
            self.servico.validarCredenciais("ausente@example.test", "senha-errada-123")

        self.assertEqual(str(senha_incorreta.exception), str(email_inexistente.exception))

    def test_autenticar_cria_sessao_ativa_persistente_com_ttl_limitado(self) -> None:
        usuario = self._cadastrar_usuario()

        sessao = self.servico.autenticar("pessoa@example.test", "senha-segura-123")

        self.assertEqual(sessao.usuario_id, usuario.id)
        self.assertIsNotNone(sessao.data_criacao)
        self.assertTrue(sessao.persistente)
        self.assertTrue(sessao.ativa)

    def test_logout_encerra_sessao(self) -> None:
        self._cadastrar_usuario()
        sessao = self.servico.autenticar("pessoa@example.test", "senha-segura-123")

        resultado = self.servico.logout(sessao.id)

        self.assertIsNone(resultado)
        self.assertFalse(sessao.ativa)

    def test_logout_rejeita_sessao_inexistente_e_ja_encerrada(self) -> None:
        with self.assertRaises(SessaoInvalidaError):
            self.servico.logout(uuid.uuid4())

        self._cadastrar_usuario()
        sessao = self.servico.autenticar("pessoa@example.test", "senha-segura-123")
        self.servico.logout(sessao.id)
        with self.assertRaises(SessaoInvalidaError):
            self.servico.logout(sessao.id)

    def test_solicitacao_exclusao_preserva_conta_e_login_cancela(self) -> None:
        usuario = self._cadastrar_usuario()

        solicitada_em = self.servico.excluir_conta(usuario.id, "senha-segura-123")

        self.assertIsNotNone(self.servico._usuarios.buscar_por_id(usuario.id))
        self.assertEqual(usuario.exclusao_solicitada_em, solicitada_em)
        self.servico.autenticar("pessoa@example.test", "senha-segura-123")
        self.assertIsNone(usuario.exclusao_solicitada_em)

    def test_exclusao_definitiva_apenas_apos_trinta_dias(self) -> None:
        usuario = self._cadastrar_usuario()
        agora = datetime.now(timezone.utc)
        usuario.exclusao_solicitada_em = agora - timedelta(days=30, seconds=1)
        self.sessao.commit()

        quantidade = self.servico.excluir_contas_vencidas(agora)

        self.assertEqual(quantidade, 1)
        self.assertIsNone(self.servico._usuarios.buscar_por_id(usuario.id))

    def test_solicitacao_com_menos_de_trinta_dias_preserva_conta(self) -> None:
        usuario = self._cadastrar_usuario()
        agora = datetime.now(timezone.utc)
        usuario.exclusao_solicitada_em = agora - timedelta(days=29)
        self.sessao.commit()

        quantidade = self.servico.excluir_contas_vencidas(agora)

        self.assertEqual(quantidade, 0)
        self.assertIsNotNone(self.servico._usuarios.buscar_por_id(usuario.id))

    def test_login_nao_cancela_solicitacao_que_ja_venceu(self) -> None:
        usuario = self._cadastrar_usuario()
        usuario.exclusao_solicitada_em = datetime.now(timezone.utc) - timedelta(days=31)
        self.sessao.commit()

        with self.assertRaises(CredenciaisInvalidasError):
            self.servico.autenticar("pessoa@example.test", "senha-segura-123")

        self.assertIsNotNone(self.servico._usuarios.buscar_por_id(usuario.id))
        self.assertIsNotNone(usuario.exclusao_solicitada_em)


if __name__ == "__main__":
    unittest.main()
