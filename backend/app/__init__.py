"""Configuração inicial do pacote do backend."""

import os
from importlib.util import find_spec
from pathlib import Path


# Define os dados do PROJ antes de importar qualquer submódulo do backend.
# find_spec localiza o PyProj do Python ativo sem carregar o próprio módulo.
_pyproj_spec = find_spec("pyproj")
if _pyproj_spec is None or _pyproj_spec.origin is None:
    raise RuntimeError("PyProj não está instalado no ambiente Python ativo.")

_proj_data_dir = (
    Path(_pyproj_spec.origin).resolve().parent / "proj_dir" / "share" / "proj"
)
if not (_proj_data_dir / "proj.db").is_file():
    raise RuntimeError(
        f"Banco de dados do PROJ não encontrado no diretório do PyProj: {_proj_data_dir}"
    )

_proj_data_path = str(_proj_data_dir)
os.environ["PROJ_DATA"] = _proj_data_path
os.environ["PROJ_LIB"] = _proj_data_path
