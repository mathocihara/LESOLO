import unittest
import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.database.conexao import Base
from app.models import PreferenciaUsuario, Usuario
from app.repositories.preferencia_usuario_repositorio import PreferenciaUsuarioRepositorio
from app.services.preferencias_usuario import (
    DadosPreferenciasInvalidosError,
    ServicoPreferenciasUsuario,
)


class TesteServicoPreferenciasUsuario(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        fabrica_sessoes = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )
        self.sessao: Session = fabrica_sessoes()
        self.usuario_um = Usuario(
            nome="Usuário Um", email="um@example.test", senha_hash="hash-senha"
        )
        self.usuario_dois = Usuario(
            nome="Usuário Dois", email="dois@example.test", senha_hash="hash-senha"
        )
        self.sessao.add_all([self.usuario_um, self.usuario_dois])
        self.sessao.commit()
        self.servico = ServicoPreferenciasUsuario(self.sessao)

    def tearDown(self) -> None:
        self.sessao.rollback()
        self.sessao.close()
        self.engine.dispose()

    def test_busca_preferencias_existentes(self) -> None:
        repositorio = PreferenciaUsuarioRepositorio(self.sessao)
        salva = repositorio.salvar(
            PreferenciaUsuario(
                usuario_id=self.usuario_um.id,
                tema="claro",
                alto_contraste=True,
                notificacoes=False,
            )
        )
        self.sessao.commit()

        encontrada = self.servico.buscar(self.usuario_um.id)

        self.assertEqual(encontrada.id, salva.id)
        self.assertEqual(encontrada.tema, "claro")
        self.assertTrue(encontrada.alto_contraste)

    def test_cria_preferencias_padrao_automaticamente(self) -> None:
        preferencia = self.servico.buscarOuCriarPadrao(self.usuario_um.id)

        self.assertEqual(preferencia.tema, "escuro")
        self.assertFalse(preferencia.alto_contraste)
        self.assertFalse(preferencia.notificacoes)
        self.assertEqual(self.servico.buscar(self.usuario_um.id).id, preferencia.id)
        self.assertEqual(
            len(
                self.sessao.scalars(
                    select(PreferenciaUsuario).where(
                        PreferenciaUsuario.usuario_id == self.usuario_um.id
                    )
                ).all()
            ),
            1,
        )

    def test_atualiza_tema_escuro_e_claro(self) -> None:
        escura = self.servico.atualizarTema(self.usuario_um.id, " CLARO ")
        self.assertEqual(escura.tema, "claro")
        clara = self.servico.atualizarTema(self.usuario_um.id, "escuro")

        self.assertEqual(clara.tema, "escuro")
        with self.assertRaises(DadosPreferenciasInvalidosError):
            self.servico.atualizarTema(self.usuario_um.id, "automático")

    def test_ativa_e_desativa_alto_contraste(self) -> None:
        ativada = self.servico.definirAltoContraste(self.usuario_um.id, True)
        self.assertTrue(ativada.alto_contraste)
        desativada = self.servico.definirAltoContraste(self.usuario_um.id, False)

        self.assertFalse(desativada.alto_contraste)
        with self.assertRaises(DadosPreferenciasInvalidosError):
            self.servico.definirAltoContraste(self.usuario_um.id, 1)

    def test_ativa_e_desativa_notificacoes(self) -> None:
        ativadas = self.servico.definirNotificacoes(self.usuario_um.id, True)
        self.assertTrue(ativadas.notificacoes)
        desativadas = self.servico.definirNotificacoes(self.usuario_um.id, False)

        self.assertFalse(desativadas.notificacoes)
        with self.assertRaises(DadosPreferenciasInvalidosError):
            self.servico.definirNotificacoes(self.usuario_um.id, "sim")

    def test_isola_preferencias_por_usuario(self) -> None:
        preferencia_um = self.servico.buscar(self.usuario_um.id)
        preferencia_dois = self.servico.buscar(self.usuario_dois.id)

        self.servico.atualizar(
            self.usuario_um.id,
            tema="claro",
            altoContraste=True,
            notificacoes=True,
        )
        preferencia_dois_atualizada = self.servico.buscar(self.usuario_dois.id)

        self.assertNotEqual(preferencia_um.id, preferencia_dois.id)
        self.assertEqual(preferencia_dois_atualizada.id, preferencia_dois.id)
        self.assertEqual(preferencia_dois_atualizada.tema, "escuro")
        self.assertFalse(preferencia_dois_atualizada.alto_contraste)
        self.assertFalse(preferencia_dois_atualizada.notificacoes)

    def test_persiste_alteracoes_entre_sessoes(self) -> None:
        self.servico.atualizar(
            self.usuario_um.id,
            tema="claro",
            altoContraste=True,
            notificacoes=True,
        )
        sessao_verificacao = sessionmaker(bind=self.engine, expire_on_commit=False)()
        try:
            persistida = sessao_verificacao.scalar(
                select(PreferenciaUsuario).where(
                    PreferenciaUsuario.usuario_id == self.usuario_um.id
                )
            )
            self.assertIsNotNone(persistida)
            self.assertEqual(persistida.tema, "claro")
            self.assertTrue(persistida.alto_contraste)
            self.assertTrue(persistida.notificacoes)
        finally:
            sessao_verificacao.close()

    def test_uuid_invalido_e_rejeitado(self) -> None:
        with self.assertRaises(DadosPreferenciasInvalidosError):
            self.servico.buscar(uuid.uuid4().hex)


if __name__ == "__main__":
    unittest.main()
