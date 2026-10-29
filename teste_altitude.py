### python teste_altitude.py


import os
import rasterio
import geopandas as gpd
import pandas as pd

from shapely.geometry import Point
from rasterio.warp import transform


# Caminhos dos arquivos
arquivo_altitude = r"C:\Users\Codigos\Desktop\pessoal\UTFPR\gloria_patricia\Aplicacao\vscode\Matheus\Altitude\Altitude.tif"
arquivo_declividade = r"C:\Users\Codigos\Desktop\pessoal\UTFPR\gloria_patricia\Aplicacao\vscode\Matheus\Declividade\Declividade.tif"
arquivo_tipo_solo = r"C:\Users\Codigos\Desktop\pessoal\UTFPR\gloria_patricia\Aplicacao\vscode\Matheus\Solos\Solos.gpkg"
arquivo_aptidao = r"C:\Users\Codigos\Desktop\pessoal\UTFPR\gloria_patricia\Aplicacao\vscode\Matheus\Apt_agricola\Apt_agricola.gpkg"

# Coluna do arquivo Solos.gpkg
campo_solo = "legenda"


# Verificar se os arquivos existem
print("=== VERIFICAÇÃO DOS ARQUIVOS ===")

for caminho in [
    arquivo_altitude,
    arquivo_declividade,
    arquivo_tipo_solo,
    arquivo_aptidao
]:
    existe = os.path.exists(caminho)
    print(f"{os.path.basename(caminho)}: {existe}")

    if not existe:
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")


# Consultar um valor em arquivo raster
def consultar_raster(src, latitude, longitude):
    if src.crs is None:
        raise ValueError("O raster não possui sistema de referência definido.")

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

    if pd.isna(valor) or getattr(valor, "mask", False):
        return None

    if src.nodata is not None and valor == src.nodata:
        return None

    return float(valor)


# Consultar um atributo em arquivo GeoPackage
def consultar_gpkg(gdf, latitude, longitude, campo):
    if gdf.crs is None:
        raise ValueError("O GeoPackage não possui CRS definido.")

    if campo not in gdf.columns:
        raise ValueError(
            f"Campo '{campo}' não encontrado. "
            f"Colunas disponíveis: {gdf.columns.tolist()}"
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


# Ler os arquivos vetoriais com GeoPandas
tipo_solo_gdf = gpd.read_file(arquivo_tipo_solo)
aptidao_gdf = gpd.read_file(arquivo_aptidao)

print("\nColunas de Solos.gpkg:")
print(tipo_solo_gdf.columns.tolist())

print("\nColunas de Apt_agricola.gpkg:")
print(aptidao_gdf.columns.tolist())


# Abrir somente os arquivos raster com Rasterio
with rasterio.open(arquivo_altitude) as altitude_src, \
     rasterio.open(arquivo_declividade) as declividade_src:

    print("\n=== CONSULTA GEOGRÁFICA ===")

    while True:
        try:
            latitude = float(input("Digite a latitude: "))
            longitude = float(input("Digite a longitude: "))

            if not -90 <= latitude <= 90:
                raise ValueError("Latitude deve estar entre -90 e 90.")

            if not -180 <= longitude <= 180:
                raise ValueError("Longitude deve estar entre -180 e 180.")

            altitude = consultar_raster(
                altitude_src, latitude, longitude
            )

            declividade = consultar_raster(
                declividade_src, latitude, longitude
            )

            tipo_solo = consultar_gpkg(
                tipo_solo_gdf, latitude, longitude, campo_solo
            )

            aptidao = consultar_gpkg(
                aptidao_gdf, latitude, longitude, "Legenda_Ap"
            )

            print("\n========== RESULTADO ==========")
            print(f"Latitude........: {latitude}")
            print(f"Longitude.......: {longitude}")

            print(
                f"Altitude........: "
                f"{f'{altitude:.2f} m' if altitude is not None else 'Não encontrada'}"
            )

            print(
                f"Declividade.....: "
                f"{f'{declividade:.2f} %' if declividade is not None else 'Não encontrada'}"
            )

            print(f"Tipo de Solo....: {tipo_solo or 'Não encontrado'}")
            print(f"Aptidão agrícola: {aptidao or 'Não encontrada'}")
            print("===============================\n")

        except Exception as erro:
            print("Erro durante a consulta:", erro)

        continuar = input(
            "Deseja consultar outra coordenada? (s/n): "
        )

        if continuar.strip().lower() != "s":
            break

