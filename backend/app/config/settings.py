
from pathlib import Path
from ipaddress import ip_address
from urllib.parse import urlsplit

from pydantic import Field
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
    SESSION_TTL_SECONDS: int = Field(default=86400, ge=1)

    # Inteligencia artificial
    OLLAMA_URL: str = "http://localhost:11434/api/chat"
    OLLAMA_MODEL: str = "llama3.2:3b"
    OLLAMA_CONTEXT_LENGTH: int = Field(default=8192, ge=4096, le=131072)
    OLLAMA_NUM_PREDICT: int = Field(default=768, ge=128, le=4096)
    OLLAMA_TIMEOUT_SECONDS: float = Field(default=180, gt=0)
    IA_MAX_VALIDATION_ATTEMPTS: int = Field(default=1, ge=1, le=3)
    IA_MAX_REFERENCIAS_CONTEXTO: int = Field(default=1, ge=1, le=10)

    # Mantido preparado para uma implementação futura do provedor OpenAI.
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str | None = None

    @property
    def is_development(self) -> bool:
        return self.APP_ENV.casefold() in {"development", "dev", "test"}

    @property
    def secure_cookies(self) -> bool:
        return not self.is_development

    def frontend_origins(self) -> list[str]:
        """Retorna a origem explícita do frontend, rejeitando configurações inseguras."""
        configured_url = self.FRONTEND_URL.strip()
        if not configured_url or "*" in configured_url:
            raise ValueError("FRONTEND_URL deve definir uma origem específica.")

        parsed = urlsplit(configured_url)
        scheme = parsed.scheme.casefold()
        hostname = parsed.hostname
        try:
            port = parsed.port
        except ValueError as erro:
            raise ValueError("FRONTEND_URL contém uma porta inválida.") from erro

        if (
            scheme not in {"http", "https"}
            or hostname is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("FRONTEND_URL deve conter somente uma origem HTTP(S).")

        if not self.is_development:
            try:
                loopback = ip_address(hostname).is_loopback
            except ValueError:
                loopback = False
            if scheme != "https" or hostname.casefold() == "localhost" or loopback:
                raise ValueError("Produção exige uma origem HTTPS pública em FRONTEND_URL.")

        if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
            port = None
        host = f"[{hostname}]" if ":" in hostname else hostname.casefold()
        autoridade = f"{host}:{port}" if port is not None else host
        return [f"{scheme}://{autoridade}"]

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
