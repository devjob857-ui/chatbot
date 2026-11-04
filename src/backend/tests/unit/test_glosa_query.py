from typing import Any

from sqlalchemy import create_engine, text

from app.database.query_executor import buscar_factura


class FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> list[dict[str, Any]]:
        return self._rows


class FakeConnection:
    """Conexión falsa que guarda el SQL y los parámetros recibidos."""

    def __init__(self) -> None:
        self.statements: list[tuple[str, Any]] = []

    def execute(self, statement: Any, parameters: Any = None) -> FakeResult:
        self.statements.append((str(statement), parameters))
        return FakeResult([])


def test_consulta_recibe_prefijo_y_numero_como_parametros_no_como_texto() -> None:
    connection = FakeConnection()

    buscar_factura(connection, "FE", "1234")

    sql, parameters = connection.statements[0]
    assert "FE" not in sql
    assert "1234" not in sql
    assert parameters == {"prefijo": "FE", "numero": "1234"}


def test_glosa_nula_cuenta_como_cero() -> None:
    engine = create_engine("sqlite://")
    with engine.begin() as conexion:
        conexion.execute(
            text(
                "CREATE TABLE cabezafactura (proveedor TEXT, nit TEXT, PrefijoFact TEXT, "
                "NroFact TEXT, glosaparcial INTEGER, glosatotal INTEGER)"
            )
        )
        conexion.execute(
            text(
                "INSERT INTO cabezafactura VALUES "
                "('Clínica Ejemplo', '900123456', 'FE', '1234', NULL, 250000)"
            )
        )

    with engine.connect() as conexion:
        filas = buscar_factura(conexion, "FE", "1234")

    assert filas[0]["valor_glosado_total"] == 250000
