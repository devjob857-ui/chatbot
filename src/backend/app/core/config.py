from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# app/core/config.py -> core, app, backend, src, raíz del proyecto.
PROJECT_ROOT = Path(__file__).resolve().parents[4]
# Ruta absoluta para que .env se lea igual sin importar el directorio de ejecución.
_ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Configuración de la aplicación, leída desde variables de entorno y .env."""

    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    # Orígenes permitidos por CORS. Vacío = sin CORS (la UI se sirve desde el mismo origen).
    # Ejemplo en .env: CORS_ORIGINS=["http://localhost:3000"]
    cors_origins: list[str] = []

    # Modelo local servido por Ollama.
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "llama3.2:3b"
    # Modelo que escribe las consultas SQL. Conviene uno más grande y orientado a código.
    sql_model: str = "qwen2.5-coder:14b"

    # Conexión a MariaDB. El usuario debe tener solo permiso SELECT.
    # Vacíos por defecto: la app arranca sin base de datos y el chat responde sin datos.
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = ""
    db_user: str = ""
    db_password: SecretStr = SecretStr("")

    # Límites de las consultas generadas por el modelo.
    sql_max_rows: int = 100
    sql_timeout_seconds: int = 15

    # Descripción de las tablas que el modelo puede consultar.
    data_dictionary_path: Path = PROJECT_ROOT / "data" / "documents" / "diccionario_datos.md"

    @property
    def database_configured(self) -> bool:
        return bool(self.db_name and self.db_user)


@lru_cache
def get_settings() -> Settings:
    return Settings()
