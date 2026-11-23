import unittest

from sqlalchemy import text

from app.config.settings import settings
from app.database.conexao import criar_engine


@unittest.skipUnless(settings.DATABASE_URL, "Configure DATABASE_URL para testar a conexão.")
class TesteConexaoBanco(unittest.TestCase):
    def test_conecta_ao_banco_geodados(self):
        engine = criar_engine()
        try:
            with engine.connect() as conexao:
                banco_atual = conexao.execute(text("SELECT current_database()")).scalar_one()
        finally:
            engine.dispose()

        self.assertEqual(banco_atual, "geodados")


if __name__ == "__main__":
    unittest.main()
