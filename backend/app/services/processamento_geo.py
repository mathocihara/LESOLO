
import logging

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

from shapely.geometry import Point
from rasterio.warp import transform

from app.config.settings import (
    ALTITUDE_PATH,
    DECLIVIDADE_PATH,
    SOLOS_PATH,
    APTIDAO_PATH
)


# ==========================================
# CONFIGURACOES DO PROCESSAMENTO GEOESPACIAL
# ==========================================

CAMPO_SOLO = "legenda"
CAMPO_APTIDAO = "Simb_Apt"
logger = logging.getLogger(__name__)


# ==========================================
# CARREGAMENTO DOS DADOS VETORIAIS
# ==========================================

# Os arquivos GeoPackage sao carregados uma vez
# para evitar releitura em cada consulta.

def _carregar_gpkg(caminho, rotulo):
    try:
        return gpd.read_file(caminho)
    except Exception:
        logger.exception("Não foi possível carregar a fonte geográfica %s.", rotulo)
        return None


tipo_solo_gdf = _carregar_gpkg(SOLOS_PATH, "tipo_solo")
aptidao_gdf = _carregar_gpkg(APTIDAO_PATH, "aptidao_agricola")


# ==========================================
# CONSULTA EM ARQUIVOS RASTER
# ==========================================

def consultar_raster(caminho, latitude, longitude):

    with rasterio.open(caminho) as src:

        if src.crs is None:
            raise ValueError(
                "O raster nao possui sistema de referencia definido."
            )

        x, y = transform(
            "EPSG:4326",
            src.crs,
            [longitude],
            [latitude]
        )

        valores = next(
            src.sample([(x[0], y[0])], masked=True)
        )

        valor = valores[0]

        if np.ma.is_masked(valor) or pd.isna(valor):
            return None

        return float(valor)


# ==========================================
# CONSULTA EM ARQUIVOS GEOPACKAGE
# ==========================================

def consultar_gpkg(gdf, latitude, longitude, campo):

    if gdf is None:
        raise RuntimeError("A camada geográfica não foi carregada.")

    if gdf.crs is None:
        raise ValueError(
            "O GeoPackage nao possui CRS definido."
        )

    if campo not in gdf.columns:
        raise ValueError(
            f"Campo '{campo}' nao encontrado. "
            f"Colunas disponiveis: {gdf.columns.tolist()}"
        )

    ponto = gpd.GeoSeries(
        [Point(longitude, latitude)],
        crs="EPSG:4326"
    ).to_crs(gdf.crs).iloc[0]

    selecionados = gdf.loc[
        gdf.geometry.notna()
        & gdf.geometry.intersects(ponto)
    ]

    if selecionados.empty:
        return None

    valor = selecionados.iloc[0][campo]

    if pd.isna(valor):
        return None

    texto = str(valor).strip()
    return texto or None


# ==========================================
# PROCESSAMENTO DE UMA CONSULTA GEOGRAFICA
# ==========================================

def consultar_coordenada(latitude, longitude):

    # Validacao das coordenadas
    if not -90 <= latitude <= 90:
        raise ValueError("Latitude deve estar entre -90 e 90.")

    if not -180 <= longitude <= 180:
        raise ValueError("Longitude deve estar entre -180 e 180.")

    fontes = {
        "altitude_m": lambda: consultar_raster(ALTITUDE_PATH, latitude, longitude),
        "declividade_percentual": lambda: consultar_raster(DECLIVIDADE_PATH, latitude, longitude),
        "tipo_solo": lambda: consultar_gpkg(tipo_solo_gdf, latitude, longitude, CAMPO_SOLO),
        "aptidao_agricola": lambda: consultar_gpkg(aptidao_gdf, latitude, longitude, CAMPO_APTIDAO),
    }
    resultado = {"latitude": latitude, "longitude": longitude}
    falhas = []
    for campo, consultar in fontes.items():
        try:
            resultado[campo] = consultar()
        except Exception as erro:
            logger.warning(
                "Falha na consulta da fonte geográfica %s (%s).",
                campo,
                type(erro).__name__,
            )
            resultado[campo] = None
            falhas.append(campo)

    ausentes = [campo for campo in fontes if resultado[campo] is None]
    disponiveis = len(fontes) - len(ausentes)
    estado = "COMPLETA" if not ausentes else "PARCIAL" if disponiveis else "SEM_RESULTADOS"
    resultado.update({
        "status_consulta": estado,
        "dados_ausentes": ausentes,
        "falhas_fontes": falhas,
    })
    return resultado
