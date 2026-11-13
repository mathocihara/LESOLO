
import os
import sys
from pathlib import Path


def configurar_proj():
    """
    Configura automaticamente os arquivos de dados do PROJ
    utilizando a instalação PyProj do ambiente Python ativo.
    """

    try:
        import pyproj

        caminho_proj = (
            Path(pyproj.__file__).resolve().parent
            / "proj_dir"
            / "share"
            / "proj"
        )

        if not caminho_proj.exists():
            raise FileNotFoundError(
                f"Diretório PROJ não encontrado: {caminho_proj}"
            )

        os.environ["PROJ_DATA"] = str(caminho_proj)
        os.environ["PROJ_LIB"] = str(caminho_proj)

    except ImportError as erro:
        raise RuntimeError(
            "PyProj não está instalado no ambiente Python ativo."
        ) from erro


configurar_proj()
