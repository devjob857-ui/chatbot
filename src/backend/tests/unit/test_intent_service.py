from app.services.intent_service import herramienta_glosa, resumir_glosa


def test_resumen_de_glosa_incluye_proveedor_nit_y_valor_formateado() -> None:
    filas = [
        {
            "proveedor": "Clínica Ejemplo",
            "nit": "900123456",
            "PrefijoFact": "FE",
            "NroFact": "1234",
            "valor_glosado_total": 1250000,
        }
    ]

    resumen = resumir_glosa(filas)

    assert "Clínica Ejemplo" in resumen
    assert "900123456" in resumen
    assert "$1.250.000" in resumen


def test_herramienta_glosa_pide_prefijo_y_numero_de_la_factura() -> None:
    herramienta = herramienta_glosa()

    assert herramienta["function"]["name"] == "consultar_valor_glosado"
    parametros = herramienta["function"]["parameters"]
    assert set(parametros["properties"]) == {"prefijo", "numero"}
    assert set(parametros["required"]) == {"prefijo", "numero"}
