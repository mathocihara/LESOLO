import unittest
from unittest.mock import patch

from app.services import processamento_geo


class TesteConsultaGeograficaParcial(unittest.TestCase):
    def _consultar(self, raster, vetorial):
        with patch.object(processamento_geo, "consultar_raster", side_effect=raster), patch.object(
            processamento_geo, "consultar_gpkg", side_effect=vetorial
        ):
            return processamento_geo.consultar_coordenada(-25.0, -49.0)

    def test_todas_as_fontes_retorna_consulta_completa(self):
        resultado = self._consultar([100, 12], ["Latossolo", "A1"])

        self.assertEqual(resultado["status_consulta"], "COMPLETA")
        self.assertEqual(resultado["dados_ausentes"], [])
        self.assertEqual(resultado["falhas_fontes"], [])

    def test_falha_em_uma_fonte_preserva_as_outras(self):
        resultado = self._consultar([OSError("indisponível"), 12], ["Latossolo", "A1"])

        self.assertEqual(resultado["status_consulta"], "PARCIAL")
        self.assertIsNone(resultado["altitude_m"])
        self.assertEqual(resultado["declividade_percentual"], 12)
        self.assertEqual(resultado["tipo_solo"], "Latossolo")
        self.assertEqual(resultado["aptidao_agricola"], "A1")
        self.assertEqual(resultado["dados_ausentes"], ["altitude_m"])
        self.assertEqual(resultado["falhas_fontes"], ["altitude_m"])

    def test_falhas_em_multiplas_fontes_mantem_resultado_disponivel(self):
        resultado = self._consultar([OSError("raster indisponível"), 12], [OSError("gpkg indisponível"), "A1"])

        self.assertEqual(resultado["status_consulta"], "PARCIAL")
        self.assertEqual(resultado["falhas_fontes"], ["altitude_m", "tipo_solo"])
        self.assertEqual(resultado["aptidao_agricola"], "A1")

    def test_fontes_sem_dados_nao_sao_classificadas_como_falha(self):
        resultado = self._consultar([None, None], [None, None])

        self.assertEqual(resultado["status_consulta"], "SEM_RESULTADOS")
        self.assertEqual(resultado["dados_ausentes"], [
            "altitude_m", "declividade_percentual", "tipo_solo", "aptidao_agricola"
        ])
        self.assertEqual(resultado["falhas_fontes"], [])

    def test_falha_de_todas_as_fontes_e_sem_resultados_com_falhas_registradas(self):
        erro = OSError("fonte indisponível")
        resultado = self._consultar([erro, erro], [erro, erro])

        self.assertEqual(resultado["status_consulta"], "SEM_RESULTADOS")
        self.assertEqual(len(resultado["falhas_fontes"]), 4)
        self.assertTrue(all(resultado[campo] is None for campo in resultado["falhas_fontes"]))


if __name__ == "__main__":
    unittest.main()
