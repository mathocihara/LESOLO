
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# ==========================================
# DIRETORIOS DO PROJETO
# ==========================================

# Identifica automaticamente a pasta backend.
BACKEND_DIR = Path(__file__).resolve().parents[2]

# Identifica a pasta backend/app.
BASE_DIR = Path(__file__).resolve().parents[1]


# ==========================================
# CONFIGURACOES DA APLICACAO
# ==========================================

class Settings(BaseSettings):

    # Aplicacao
    APP_NAME: str = "LESOLO"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # API
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000

    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"

    # Banco de dados
    DATABASE_URL: str | None = None

    # Inteligencia artificial
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str | None = None

    # Dados geoespaciais
    GEO_DATA_PATH: str ="Matheus"

    ALTITUDE_FILE: str = "Altitude.tif"
    DECLIVIDADE_FILE: str = "Declividade.tif"
    SOLOS_FILE: str = "Solos.gpkg"
    APTIDAO_FILE: str = "Apt_agricola.gpkg"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# ==========================================
# INSTANCIA DAS CONFIGURACOES
# ==========================================

settings = Settings()


# ==========================================
# CAMINHOS DOS DADOS GEOESPACIAIS
# ==========================================

# Os arquivos geoespaciais de referencia ficam
# organizados na pasta Matheus, dentro de app.
# Utilizamos caminhos relativos para evitar dependencia
# de caminhos absolutos especificos de cada computador.

GEO_DATA_DIR = (BACKEND_DIR / settings.GEO_DATA_PATH).resolve()

# Caminhos individuais dos arquivos geoespaciais.

ALTITUDE_PATH = GEO_DATA_DIR / "Altitude" / settings.ALTITUDE_FILE

DECLIVIDADE_PATH = GEO_DATA_DIR / "Declividade" / settings.DECLIVIDADE_FILE

SOLOS_PATH = GEO_DATA_DIR / "Solos" / settings.SOLOS_FILE

APTIDAO_PATH = GEO_DATA_DIR / "Apt_agricola" / settings.APTIDAO_FILE
