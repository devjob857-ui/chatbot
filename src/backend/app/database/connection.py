"""Conexión a MariaDB. El usuario configurado debe tener solo permiso SELECT."""

from functools import lru_cache

from sqlalchemy import URL, Engine, create_engine, event

from app.core.config import Settings, get_settings


def _statement_timeout_sql(server_version: str, seconds: int) -> str:
    """Límite de tiempo por consulta. MariaDB y MySQL usan variables distintas."""
    if "mariadb" in server_version.lower():
        return f"SET SESSION max_statement_time = {int(seconds)}"
    # MySQL: milisegundos, solo aplica a SELECT (justo lo que se ejecuta aquí).
    return f"SET SESSION max_execution_time = {int(seconds) * 1000}"


def build_engine(settings: Settings) -> Engine:
    url = URL.create(
        drivername="mysql+pymysql",
        username=settings.db_user,
        password=settings.db_password.get_secret_value(),
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
    )
    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": 10,
            "read_timeout": settings.sql_timeout_seconds + 5,
            "charset": "utf8mb4",
        },
    )

    timeout = settings.sql_timeout_seconds

    @event.listens_for(engine, "connect")
    def _restrict_session(dbapi_connection, _record) -> None:
        # Defensa extra: aunque el usuario solo tenga SELECT, la sesión no permite escribir
        # y MariaDB corta las consultas que tarden demasiado.
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SET SESSION TRANSACTION READ ONLY")
            cursor.execute(_statement_timeout_sql(dbapi_connection.get_server_info(), timeout))

    return engine


@lru_cache
def get_engine() -> Engine:
    """Engine compartido, creado la primera vez que se necesita."""
    return build_engine(get_settings())
