"""Consultas predefinidas y parametrizadas. No se genera SQL a partir del texto del usuario."""

from typing import Any

from sqlalchemy import text

_BUSCAR_FACTURA = text(
    """
    SELECT proveedor,
           nit,
           PrefijoFact,
           NroFact,
           COALESCE(glosaparcial, 0) + COALESCE(glosatotal, 0) AS valor_glosado_total
    FROM cabezafactura
    WHERE PrefijoFact = :prefijo
      AND NroFact = :numero
    """
)


def buscar_factura(connection: Any, prefijo: str, numero: str) -> list[dict[str, Any]]:
    result = connection.execute(_BUSCAR_FACTURA, {"prefijo": prefijo, "numero": numero})
    return [dict(row) for row in result.mappings()]
