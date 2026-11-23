import unittest
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.conexao import Base
from app.models import DadosGeograficos, RegistroConsulta, StatusRegistro, Usuario
from app.repositories.usuario_repositorio import UsuarioRepositorio
from app.services.registro import (
    RegistroConsultaNaoEncontradoError,
    ServicoRegistro,
)


class TesteServicoRegistro(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        fabrica_sessoes = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )
        self.sessao: Session = fabrica_sessoes()
        usuarios = UsuarioRepositorio(self.sessao)
        self.usuario = usuarios.salvar(
            Usuario(nome="Usuário Um", email="um@example.test", senha_hash="hash-senha")
        )
        self.outro_usuario = usuarios.salvar(
            Usuario(nome="Usuário Dois", email="dois@example.test", senha_hash="hash-senha")
        )
        self.sessao.commit()
        self.servico = ServicoRegistro(
            self.sessao,
            prazoExpiracaoTemporario=timedelta(days=14),
        )

    def tearDown(self) -> None:
        self.sessao.rollback()
        self.sessao.close()
        self.engine.dispose()

    @staticmethod
    def _dados_geograficos() -> DadosGeograficos:
        return DadosGeograficos(
            mde=Decimal("900.250"),
            declividade=Decimal("12.500"),
            tipo_solo="Latossolo",
            aptidao_agricola="A1",
        )

    def _criar_temporario(
        self,
        usuario_id: uuid.UUID | None = None,
        data_consulta: datetime | None = None,
    ) -> RegistroConsulta:
        return self.servico.criarTemporario(
            usuarioId=usuario_id or self.usuario.id,
            latitude=Decimal("-25.430000"),
            longitude=Decimal("-49.270000"),
            dadosGeograficos=self._dados_geograficos(),
            dataConsulta=data_consulta or datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

    def test_cria_consulta_temporaria_com_expiracao_e_campos_geograficos(self) -> None:
        data_consulta = datetime(2026, 1, 2, 12, tzinfo=timezone.utc)

        registro = self._criar_temporario(data_consulta=data_consulta)

        self.assertEqual(registro.usuario_id, self.usuario.id)
        self.assertEqual(registro.status, StatusRegistro.TEMPORARIO)
        self.assertEqual(registro.data_consulta, data_consulta)
        self.assertEqual(registro.data_expiracao, data_consulta + timedelta(days=14))
        self.assertEqual(registro.altitude_m, Decimal("900.250"))
        self.assertEqual(registro.declividade_percentual, Decimal("12.500"))
        self.assertEqual(registro.tipo_solo, "Latossolo")
        self.assertEqual(registro.aptidao_agricola, "A1")
        self.assertFalse(hasattr(registro, "explicacao"))

    def test_salva_como_permanente_e_remove_expiracao(self) -> None:
        temporario = self._criar_temporario()

        permanente = self.servico.salvarComoPermanente(
            temporario.id, self.usuario.id, "  Talhão Norte  "
        )

        self.assertEqual(permanente.status, StatusRegistro.PERMANENTE)
        self.assertEqual(permanente.nome, "Talhão Norte")
        self.assertIsNone(permanente.data_expiracao)

    def test_gera_nome_automatico_sequencial_quando_nome_ausente(self) -> None:
        primeiro = self._criar_temporario()
        segundo = self._criar_temporario(data_consulta=datetime(2026, 1, 2, tzinfo=timezone.utc))

        permanente_um = self.servico.salvarComoPermanente(primeiro.id, self.usuario.id, None)
        permanente_dois = self.servico.salvarComoPermanente(segundo.id, self.usuario.id)

        self.assertEqual(permanente_um.nome, "Consulta 1")
        self.assertEqual(permanente_dois.nome, "Consulta 2")
        self.assertEqual(self.servico.gerarNomeAutomatico(self.outro_usuario.id), "Consulta 1")

    def test_lista_historico_filtra_status_isola_usuario_e_ordena(self) -> None:
        permanente_antigo = self._criar_temporario(
            data_consulta=datetime(2026, 1, 1, tzinfo=timezone.utc)
        )
        permanente_antigo = self.servico.salvarComoPermanente(
            permanente_antigo.id, self.usuario.id, "Antigo"
        )
        temporario = self._criar_temporario(
            data_consulta=datetime(2026, 1, 2, tzinfo=timezone.utc)
        )
        permanente_novo = self._criar_temporario(
            data_consulta=datetime(2026, 1, 3, tzinfo=timezone.utc)
        )
        permanente_novo = self.servico.salvarComoPermanente(
            permanente_novo.id, self.usuario.id, "Novo"
        )
        registro_alheio = self._criar_temporario(
            usuario_id=self.outro_usuario.id,
            data_consulta=datetime(2026, 1, 4, tzinfo=timezone.utc),
        )

        historico = self.servico.listarRegistrosDoUsuario(self.usuario.id)
        temporarios = self.servico.listarRegistrosDoUsuario(
            self.usuario.id, StatusRegistro.TEMPORARIO
        )
        todos = self.servico.listarRegistrosDoUsuario(self.usuario.id, None)

        self.assertEqual(
            [registro.id for registro in historico],
            [permanente_novo.id, permanente_antigo.id],
        )
        self.assertEqual([registro.id for registro in temporarios], [temporario.id])
        self.assertEqual(
            {registro.id for registro in todos},
            {permanente_antigo.id, temporario.id, permanente_novo.id},
        )
        self.assertNotIn(registro_alheio.id, {registro.id for registro in todos})

    def test_salvar_e_excluir_respeitam_proprietario(self) -> None:
        registro = self._criar_temporario()

        with self.assertRaises(RegistroConsultaNaoEncontradoError):
            self.servico.salvarComoPermanente(registro.id, self.outro_usuario.id, "Alheio")
        with self.assertRaises(RegistroConsultaNaoEncontradoError):
            self.servico.excluirRegistro(registro.id, self.outro_usuario.id)
        self.assertEqual(
            [item.id for item in self.servico.listarRegistrosDoUsuario(self.usuario.id, None)],
            [registro.id],
        )

        self.assertIsNone(self.servico.excluirRegistro(registro.id, self.usuario.id))
        self.assertEqual(self.servico.listarRegistrosDoUsuario(self.usuario.id, None), [])
        with self.assertRaises(RegistroConsultaNaoEncontradoError):
            self.servico.excluirRegistro(registro.id, self.usuario.id)


if __name__ == "__main__":
    unittest.main()
