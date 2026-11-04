from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# app/core/config.py -> core, app, backend, src, raíz del proyecto.
# Ruta absoluta para que .env se lea igual sin importar el directorio de ejecución.
_ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


class Settings(BaseSettings):
    """Configuración de la aplicación, leída desde variables de entorno y .env."""

    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    # Orígenes permitidos por CORS. Vacío = sin CORS (la UI se sirve desde el mismo origen).
    # Ejemplo en .env: CORS_ORIGINS=["http://localhost:3000"]
    cors_origins: list[str] = []

    # Modelo local servido por Ollama.
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "llama3.2:3b"

    # Conexión a MariaDB. El usuario debe tener solo permiso SELECT.
    # Vacíos por defecto: la app arranca sin base de datos; la capa de BD valida al conectar.
    db_host: str = "10.10.10.100"
    db_port: int = 3306
    db_name: str = ""
    db_user: str = ""
    db_password: SecretStr = SecretStr("")


@lru_cache
def get_settings() -> Settings:
    return Settings()
