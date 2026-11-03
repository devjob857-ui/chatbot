from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación, leída desde variables de entorno y .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Orígenes permitidos por CORS. Vacío = sin CORS (la UI se sirve desde el mismo origen).
    # Ejemplo en .env: CORS_ORIGINS=["http://localhost:3000"]
    cors_origins: list[str] = []


@lru_cache
def get_settings() -> Settings:
    return Settings()
