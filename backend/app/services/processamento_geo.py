
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


# ==========================================
# CARREGAMENTO DOS DADOS VETORIAIS
# ==========================================

# Os arquivos GeoPackage sao carregados uma vez
# para evitar releitura em cada consulta.

tipo_solo_gdf = gpd.read_file(SOLOS_PATH)
aptidao_gdf = gpd.read_file(APTIDAO_PATH)


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

    return str(valor).strip()


# ==========================================
# PROCESSAMENTO DE UMA CONSULTA GEOGRAFICA
# ==========================================

def consultar_coordenada(latitude, longitude):

    # Validacao das coordenadas
    if not -90 <= latitude <= 90:
        raise ValueError("Latitude deve estar entre -90 e 90.")

    if not -180 <= longitude <= 180:
        raise ValueError("Longitude deve estar entre -180 e 180.")

    # Consulta dos arquivos raster
    altitude = consultar_raster(
        ALTITUDE_PATH,
        latitude,
        longitude
    )

    declividade = consultar_raster(
        DECLIVIDADE_PATH,
        latitude,
        longitude
    )

    # Consulta dos arquivos vetoriais
    tipo_solo = consultar_gpkg(
        tipo_solo_gdf,
        latitude,
        longitude,
        CAMPO_SOLO
    )

    aptidao = consultar_gpkg(
        aptidao_gdf,
        latitude,
        longitude,
        CAMPO_APTIDAO
    )

    # Retorno estruturado dos resultados
    resultado = {
        "latitude": latitude,
        "longitude": longitude,
        "altitude_m": altitude,
        "declividade_percentual": declividade,
        "tipo_solo": tipo_solo,
        "aptidao_agricola": aptidao
    }

    return resultado
