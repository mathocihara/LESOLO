"""Teste opcional em schema descartável de um banco PostgreSQL dedicado."""

from __future__ import annotations

import os
import unittest
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.database.conexao import Base
from app.models import Sessao
from app.routes.dependencias import _sessao_expirada
from app.services.autenticacao import ServicoAutenticacao


TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


@unittest.skipUnless(
    TEST_DATABASE_URL,
    "Defina TEST_DATABASE_URL para executar o teste PostgreSQL isolado.",
)
class TestePostgreSQLSessoes(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        url = make_url(TEST_DATABASE_URL)
        if url.drivername in {"postgres", "postgresql"}:
            url = url.set(drivername="postgresql+psycopg")
        if not url.drivername.startswith("postgresql"):
            raise RuntimeError("TEST_DATABASE_URL deve apontar para PostgreSQL.")
        database_name = (url.database or "").casefold()
        if database_name == "geodados" or "test" not in database_name:
            raise RuntimeError(
                "O teste exige um banco dedicado cujo nome contenha 'test'; geodados é proibido."
            )

        cls.url = url
        cls.schema = f"lesolo_test_{uuid.uuid4().hex}"
        cls.admin_engine = create_engine(url)
        with cls.admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{cls.schema}"'))

        cls.engine = create_engine(url)

        def definir_schema(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute(f'SET search_path TO "{cls.schema}"')
            cursor.close()

        event.listen(cls.engine, "connect", definir_schema)
        try:
            Base.metadata.create_all(cls.engine)
        except Exception:
            cls.engine.dispose()
            with cls.admin_engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{cls.schema}" CASCADE'))
            cls.admin_engine.dispose()
            raise
        cls.fabrica_sessoes = sessionmaker(
            bind=cls.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        if not hasattr(cls, "schema"):
            return
        cls.engine.dispose()
        with cls.admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{cls.schema}" CASCADE'))
        cls.admin_engine.dispose()

    def test_postgres_persiste_sessao_e_timestamp_com_fuso(self) -> None:
        with self.fabrica_sessoes() as sessao_banco:
            usuario = ServicoAutenticacao(sessao_banco).cadastrar(
                "Pessoa PostgreSQL",
                f"{uuid.uuid4().hex}@example.test",
                "senha-segura-123",
            )
            sessao = ServicoAutenticacao(sessao_banco).autenticar(
                usuario.email,
                "senha-segura-123",
            )
            sessao_id = sessao.id

        with self.fabrica_sessoes() as sessao_banco:
            persistida = sessao_banco.get(Sessao, sessao_id)
            self.assertIsNotNone(persistida)
            self.assertTrue(persistida.ativa)
            self.assertIsNotNone(persistida.data_criacao)
            self.assertIsNotNone(persistida.data_criacao.tzinfo)
            self.assertFalse(_sessao_expirada(persistida))


if __name__ == "__main__":
    unittest.main()
