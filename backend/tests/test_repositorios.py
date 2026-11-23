import hashlib
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.conexao import Base
from app.models import (
    DadosGeograficos,
    PreferenciaUsuario,
    RegistroConsulta,
    Sessao,
    StatusRegistro,
    TokenRedefinicaoSenha,
    Usuario,
)
from app.repositories import (
    PreferenciaUsuarioRepositorio,
    RegistroConsultaRepositorio,
    SessaoRepositorio,
    TokenRedefinicaoSenhaRepositorio,
    UsuarioRepositorio,
)


class TesteRepositorios(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        fabrica_sessoes = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )
        self.sessao: Session = fabrica_sessoes()

        self.usuarios = UsuarioRepositorio(self.sessao)
        self.sessoes = SessaoRepositorio(self.sessao)
        self.tokens = TokenRedefinicaoSenhaRepositorio(self.sessao)
        self.registros = RegistroConsultaRepositorio(self.sessao)
        self.preferencias = PreferenciaUsuarioRepositorio(self.sessao)

        self.usuario = self.usuarios.salvar(
            Usuario(nome="Usuário Um", email="um@example.test", senha_hash="hash-senha")
        )

    def tearDown(self) -> None:
        self.sessao.rollback()
        self.sessao.close()
        self.engine.dispose()

    def _novo_registro(
        self,
        usuario_id: uuid.UUID,
        status: StatusRegistro,
    ) -> RegistroConsulta:
        return RegistroConsulta(
            usuario_id=usuario_id,
            nome="Área de teste",
            latitude=Decimal("-25.430000"),
            longitude=Decimal("-49.270000"),
            dados_geograficos=DadosGeograficos(
                mde=Decimal("900.250"),
                declividade=Decimal("12.500"),
                tipo_solo="Latossolo",
                aptidao_agricola="A1",
            ),
            status=status,
        )

    def test_salva_e_busca_usuario_por_email_e_uuid(self) -> None:
        usuario = self.usuarios.buscar_por_email("um@example.test")

        self.assertIsNotNone(usuario)
        self.assertEqual(usuario.id, self.usuario.id)
        self.assertIs(self.usuarios.buscar_por_id(self.usuario.id), usuario)
        self.assertIsNone(self.usuarios.buscar_por_email("inexistente@example.test"))
        self.assertIsNone(self.usuarios.buscar_por_id(uuid.uuid4()))

    def test_salva_e_encerra_sessao(self) -> None:
        sessao = self.sessoes.salvar(Sessao(usuario_id=self.usuario.id))

        self.assertIs(self.sessoes.buscar_por_id(sessao.id), sessao)
        self.assertTrue(sessao.ativa)
        self.assertTrue(self.sessoes.encerrar(sessao.id))
        self.assertFalse(self.sessoes.buscar_por_id(sessao.id).ativa)
        self.assertFalse(self.sessoes.encerrar(uuid.uuid4()))

    def test_salva_e_busca_token_apenas_pelo_hash_sha256(self) -> None:
        hash_token = hashlib.sha256(b"segredo temporario").hexdigest()
        token = TokenRedefinicaoSenha(
            valor_hash=hash_token,
            usuario_id=self.usuario.id,
            data_expiracao=datetime.now(timezone.utc) + timedelta(minutes=15),
        )

        salvo = self.tokens.salvar(token)

        self.assertEqual(salvo.valor_hash, hash_token)
        self.assertIs(self.tokens.buscar_por_hash(hash_token), salvo)
        self.assertIsNone(self.tokens.buscar_por_hash(hashlib.sha256(b"outro").hexdigest()))

        token_puro = TokenRedefinicaoSenha(
            valor_hash="segredo temporario",
            usuario_id=self.usuario.id,
            data_expiracao=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
        with self.assertRaises(ValueError):
            self.tokens.salvar(token_puro)

    def test_salva_lista_filtra_status_e_isola_registros_por_usuario(self) -> None:
        outro_usuario = self.usuarios.salvar(
            Usuario(nome="Usuário Dois", email="dois@example.test", senha_hash="hash-senha")
        )
        temporario = self.registros.salvar(
            self._novo_registro(self.usuario.id, StatusRegistro.TEMPORARIO)
        )
        permanente = self.registros.salvar(
            self._novo_registro(self.usuario.id, StatusRegistro.PERMANENTE)
        )
        registro_de_outro_usuario = self.registros.salvar(
            self._novo_registro(outro_usuario.id, StatusRegistro.TEMPORARIO)
        )

        listados = self.registros.listar_por_usuario(self.usuario.id)
        temporarios = self.registros.listar_por_usuario(
            self.usuario.id, status=StatusRegistro.TEMPORARIO
        )

        self.assertEqual({registro.id for registro in listados}, {temporario.id, permanente.id})
        self.assertEqual([registro.id for registro in temporarios], [temporario.id])
        self.assertIs(self.registros.buscar_por_id(temporario.id, self.usuario.id), temporario)
        self.assertIsNone(
            self.registros.buscar_por_id(registro_de_outro_usuario.id, self.usuario.id)
        )
        self.assertEqual(
            self.registros.listar_por_usuario(outro_usuario.id), [registro_de_outro_usuario]
        )

    def test_salva_busca_e_atualiza_preferencias(self) -> None:
        preferencia = self.preferencias.salvar(
            PreferenciaUsuario(
                usuario_id=self.usuario.id,
                tema="claro",
                alto_contraste=False,
                notificacoes=True,
            )
        )

        encontrada = self.preferencias.buscar_por_usuario(self.usuario.id)
        atualizada = self.preferencias.atualizar(
            self.usuario.id,
            tema="escuro",
            alto_contraste=True,
            notificacoes=False,
        )

        self.assertIs(encontrada, preferencia)
        self.assertIs(atualizada, preferencia)
        self.assertEqual(atualizada.tema, "escuro")
        self.assertTrue(atualizada.alto_contraste)
        self.assertFalse(atualizada.notificacoes)
        self.assertIsNone(self.preferencias.atualizar(uuid.uuid4(), tema="claro"))


if __name__ == "__main__":
    unittest.main()
