"""Conexión a MariaDB. El usuario configurado debe tener solo permiso SELECT."""

from sqlalchemy import URL, Engine, create_engine

from app.core.config import Settings


def build_engine(settings: Settings) -> Engine:
    url = URL.create(
        drivername="mysql+pymysql",
        username=settings.db_user,
        password=settings.db_password.get_secret_value(),
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
    )
    return create_engine(url)
