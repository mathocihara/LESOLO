
import rasterio
import numpy as np
from rasterio.warp import transform

arquivo = r"C:\Users\Codigos\Desktop\pessoal\UTFPR\gloria_patricia\vscode\Matheus\Declividade\Declividade.tif"

latitude = -24.9555
longitude = -53.4552

with rasterio.open(arquivo) as src:
    x, y = transform(
        "EPSG:4326",
        src.crs,
        [longitude],
        [latitude]
    )

    linha, coluna = src.index(x[0], y[0])

    janela = src.read(
        1,
        window=(
            (max(0, linha - 2), min(src.height, linha + 3)),
            (max(0, coluna - 2), min(src.width, coluna + 3))
        ),
        masked=True
    )

    valores = janela.compressed()

    print("Valores de declividade ao redor do ponto:")
    print(janela)
    print("Quantidade de pixels válidos:", len(valores))

    if len(valores) > 0:
        print("Mínimo local:", valores.min())
        print("Máximo local:", valores.max())
        print("Mediana local:", np.median(valores))
