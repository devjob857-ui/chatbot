"""Convierte el resultado de la consulta de glosa en texto para el modelo."""

from typing import Any

from pydantic import BaseModel


class ConsultarValorGlosado(BaseModel):
    """Prefijo y número de la factura cuyo valor glosado total se quiere conocer."""

    prefijo: str
    numero: str


def herramienta_glosa() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "consultar_valor_glosado",
            "description": "Consulta el valor glosado total de una factura por prefijo y número.",
            "parameters": ConsultarValorGlosado.model_json_schema(),
        },
    }


def _formatear_pesos(valor: int) -> str:
    return "$" + f"{valor:,}".replace(",", ".")


def resumir_glosa(filas: list[dict[str, Any]]) -> str:
    if not filas:
        return "No se encontró ninguna factura con ese prefijo y número."
    return "\n".join(
        f"Proveedor: {fila['proveedor']} (NIT {fila['nit']}). "
        f"Valor glosado total: {_formatear_pesos(fila['valor_glosado_total'])}."
        for fila in filas
    )
