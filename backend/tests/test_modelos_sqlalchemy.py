import uuid
import unittest
from decimal import Decimal

from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable
from sqlalchemy.orm import configure_mappers

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


class TesteModelosSQLAlchemy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configure_mappers()

    def test_metadata_contem_apenas_as_tabelas_persistentes_previstas(self):
        self.assertEqual(
            set(Base.metadata.tables),
            {
                "usuarios",
                "sessoes",
                "tokens_redefinicao_senha",
                "registros_consulta",
                "preferencias_usuario",
            },
        )

    def test_relacionamentos_e_chaves_estrangeiras(self):
        relacoes_usuario = inspect(Usuario).relationships
        self.assertTrue(relacoes_usuario["sessoes"].uselist)
        self.assertTrue(relacoes_usuario["tokens_redefinicao"].uselist)
        self.assertTrue(relacoes_usuario["registros_consulta"].uselist)
        self.assertFalse(relacoes_usuario["preferencia"].uselist)

        for modelo in (Sessao, TokenRedefinicaoSenha, RegistroConsulta, PreferenciaUsuario):
            chaves = modelo.__table__.foreign_keys
            self.assertEqual(len(chaves), 1)
            chave = next(iter(chaves))
            self.assertEqual(chave.target_fullname, "usuarios.id")
            self.assertEqual(chave.ondelete, "CASCADE")

    def test_chaves_uuid_e_email_unico(self):
        for modelo in (Usuario, Sessao, RegistroConsulta, PreferenciaUsuario):
            self.assertIs(modelo.__table__.c.id.type.python_type, uuid.UUID)

        self.assertTrue(Usuario.__table__.c.email.unique)
        self.assertTrue(PreferenciaUsuario.__table__.c.usuario_id.unique)

    def test_enum_e_dados_geograficos(self):
        enum_status = RegistroConsulta.__table__.c.status.type
        self.assertIs(enum_status.python_type, StatusRegistro)
        self.assertEqual(enum_status.enums, ["TEMPORARIO", "PERMANENTE"])
        self.assertEqual(
            [campo.name for campo in DadosGeograficos.__dataclass_fields__.values()],
            ["mde", "declividade", "tipo_solo", "aptidao_agricola"],
        )
        self.assertTrue(
            {"altitude_m", "declividade_percentual", "tipo_solo", "aptidao_agricola"}
            <= set(RegistroConsulta.__table__.c.keys())
        )
        self.assertNotIn("explicacao", RegistroConsulta.__table__.c)

    def test_token_persistido_somente_com_hash(self):
        self.assertEqual(TokenRedefinicaoSenha.__table__.primary_key.columns.keys(), ["valor_hash"])
        self.assertNotIn("valor", TokenRedefinicaoSenha.__table__.c)

    def test_tabelas_compilam_para_postgresql(self):
        for tabela in Base.metadata.sorted_tables:
            ddl = str(CreateTable(tabela).compile(dialect=postgresql.dialect()))
            self.assertIn(f"CREATE TABLE {tabela.name}", ddl)

    def test_valores_geograficos_expostos_com_nomes_da_api(self):
        registro = RegistroConsulta(
            usuario_id=uuid.uuid4(),
            latitude=Decimal("-25.430000"),
            longitude=Decimal("-49.270000"),
            dados_geograficos=DadosGeograficos(
                mde=Decimal("900.250"),
                declividade=Decimal("12.500"),
                tipo_solo="Latossolo",
                aptidao_agricola="A1",
            ),
        )

        self.assertEqual(registro.altitude_m, Decimal("900.250"))
        self.assertEqual(registro.declividade_percentual, Decimal("12.500"))
        self.assertEqual(registro.tipo_solo, "Latossolo")
        self.assertEqual(registro.aptidao_agricola, "A1")


if __name__ == "__main__":
    unittest.main()
