"""Ejecución de consultas SELECT ya validadas."""

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import text

from app.core.config import get_settings
from app.database.connection import get_engine


@dataclass(frozen=True)
class QueryResult:
    columns: list[str]
    rows: list[tuple[str, ...]]
    truncated: bool


def format_value(value: object) -> str:
    """Convierte un valor a texto legible, para que el modelo lo copie sin alterarlo."""
    if value is None:
        return "(vacío)"
    if isinstance(value, bool):
        return "sí" if value else "no"
    if isinstance(value, int):
        return f"{value:,}".replace(",", ".")
    if isinstance(value, (Decimal, float)):
        number = Decimal(str(value))
        if number == number.to_integral_value():
            return f"{int(number):,}".replace(",", ".")
        # Formato colombiano: punto de miles, coma decimal.
        return f"{number:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    if isinstance(value, dt.datetime):
        return value.strftime("%Y-%m-%d %H:%M") if (value.hour or value.minute) else value.strftime("%Y-%m-%d")
    if isinstance(value, dt.date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def run_select(sql: str) -> QueryResult:
    """Ejecuta un SELECT validado y devuelve como máximo `SQL_MAX_ROWS` filas."""
    max_rows = get_settings().sql_max_rows
    with get_engine().connect() as connection:
        result = connection.execute(text(sql))
        columns = list(result.keys())
        raw_rows = result.fetchmany(max_rows + 1)
    truncated = len(raw_rows) > max_rows
    rows = [tuple(format_value(value) for value in row) for row in raw_rows[:max_rows]]
    return QueryResult(columns=columns, rows=rows, truncated=truncated)
