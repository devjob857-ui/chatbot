from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from app.main import create_app


class FakeModeloConHerramienta(BaseChatModel):
    """Modelo falso que responde en orden y guarda los mensajes recibidos."""

    respuestas: list[AIMessage]
    recibidos: list[list[BaseMessage]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "fake-herramienta"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "FakeModeloConHerramienta":
        return self

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs: Any):
        self.recibidos.append(list(messages))
        return ChatResult(generations=[ChatGeneration(message=self.respuestas.pop(0))])


class FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> list[dict[str, Any]]:
        return self._rows


class FakeConnection:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self.parametros: list[dict[str, Any]] = []

    def execute(self, statement: Any, parameters: Any = None) -> FakeResult:
        self.parametros.append(parameters)
        return FakeResult(self._rows)


class FakeEngine:
    def __init__(self, connection: FakeConnection) -> None:
        self._connection = connection

    def connect(self) -> "FakeEngine":
        return self

    def __enter__(self) -> FakeConnection:
        return self._connection

    def __exit__(self, *args: object) -> None:
        return None


FILA_FE_1234 = {
    "proveedor": "Clínica Ejemplo",
    "nit": "900123456",
    "PrefijoFact": "FE",
    "NroFact": "1234",
    "valor_glosado_total": 1250000,
}


def test_valor_glosado_responde_con_total_y_proveedor(monkeypatch: pytest.MonkeyPatch) -> None:
    modelo = FakeModeloConHerramienta(
        respuestas=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "consultar_valor_glosado",
                        "args": {"prefijo": "FE", "numero": "1234"},
                        "id": "llamada-1",
                    }
                ],
            ),
            AIMessage(content="El valor glosado total de FE-1234 es $1.250.000 (Clínica Ejemplo)."),
        ]
    )
    conexion = FakeConnection([FILA_FE_1234])
    monkeypatch.setattr("app.services.chat_service.get_chat_model", lambda: modelo)
    monkeypatch.setattr("app.services.chat_service.build_engine", lambda settings: FakeEngine(conexion))
    client = TestClient(create_app())

    response = client.post(
        "/chat", json={"question": "¿Cuál fue el valor glosado total de la factura FE-1234?"}
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "El valor glosado total de FE-1234 es $1.250.000 (Clínica Ejemplo)."
    assert conexion.parametros == [{"prefijo": "FE", "numero": "1234"}]
    resultados = [m for m in modelo.recibidos[1] if isinstance(m, ToolMessage)]
    assert len(resultados) == 1
    assert "Clínica Ejemplo" in resultados[0].content
    assert "$1.250.000" in resultados[0].content


def test_factura_inexistente_avisa_que_no_se_encontro(monkeypatch: pytest.MonkeyPatch) -> None:
    modelo = FakeModeloConHerramienta(
        respuestas=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "consultar_valor_glosado",
                        "args": {"prefijo": "FE", "numero": "9999"},
                        "id": "llamada-2",
                    }
                ],
            ),
            AIMessage(content="No encontré la factura FE-9999."),
        ]
    )
    conexion = FakeConnection([])
    monkeypatch.setattr("app.services.chat_service.get_chat_model", lambda: modelo)
    monkeypatch.setattr("app.services.chat_service.build_engine", lambda settings: FakeEngine(conexion))
    client = TestClient(create_app())

    response = client.post(
        "/chat", json={"question": "¿Cuál fue el valor glosado de la factura FE-9999?"}
    )

    assert response.status_code == 200
    resultados = [m for m in modelo.recibidos[1] if isinstance(m, ToolMessage)]
    assert len(resultados) == 1
    assert "no se encontró" in resultados[0].content.lower()
    assert "$" not in resultados[0].content


def test_facturas_con_mismo_numero_listan_proveedor_nit_y_valor_de_cada_una(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    modelo = FakeModeloConHerramienta(
        respuestas=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "consultar_valor_glosado",
                        "args": {"prefijo": "FE", "numero": "1234"},
                        "id": "llamada-3",
                    }
                ],
            ),
            AIMessage(content="Hay dos facturas FE-1234."),
        ]
    )
    filas = [
        {
            "proveedor": "Clínica Norte",
            "nit": "900111111",
            "PrefijoFact": "FE",
            "NroFact": "1234",
            "valor_glosado_total": 500000,
        },
        {
            "proveedor": "Hospital Sur",
            "nit": "800222222",
            "PrefijoFact": "FE",
            "NroFact": "1234",
            "valor_glosado_total": 75000,
        },
    ]
    conexion = FakeConnection(filas)
    monkeypatch.setattr("app.services.chat_service.get_chat_model", lambda: modelo)
    monkeypatch.setattr("app.services.chat_service.build_engine", lambda settings: FakeEngine(conexion))
    client = TestClient(create_app())

    client.post("/chat", json={"question": "¿Cuál es el valor glosado de la factura FE-1234?"})

    resultados = [m for m in modelo.recibidos[1] if isinstance(m, ToolMessage)]
    contenido = resultados[0].content
    assert "Clínica Norte" in contenido
    assert "900111111" in contenido
    assert "$500.000" in contenido
    assert "Hospital Sur" in contenido
    assert "800222222" in contenido
    assert "$75.000" in contenido


def test_pregunta_general_no_consulta_la_base(monkeypatch: pytest.MonkeyPatch) -> None:
    respuesta = "Medicalidad es una empresa de servicios de salud."
    modelo = FakeModeloConHerramienta(respuestas=[AIMessage(content=respuesta)])
    conexiones_abiertas: list[object] = []
    monkeypatch.setattr("app.services.chat_service.get_chat_model", lambda: modelo)
    monkeypatch.setattr(
        "app.services.chat_service.build_engine",
        lambda settings: conexiones_abiertas.append(settings) or FakeEngine(FakeConnection([])),
    )
    client = TestClient(create_app())

    response = client.post("/chat", json={"question": "¿Qué es Medicalidad?"})

    assert response.status_code == 200
    assert response.json()["answer"] == respuesta
    assert conexiones_abiertas == []
    assert len(modelo.recibidos) == 1


def test_texto_junto_a_llamada_a_herramienta_se_emite_antes_de_la_respuesta_final(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Decisión: se mantiene el streaming de la primera llamada. Si el modelo escribe
    # texto junto a la llamada a herramienta, ese texto llega al usuario antes de la respuesta.
    modelo = FakeModeloConHerramienta(
        respuestas=[
            AIMessage(
                content="Consulto la factura.",
                tool_calls=[
                    {
                        "name": "consultar_valor_glosado",
                        "args": {"prefijo": "FE", "numero": "1234"},
                        "id": "llamada-4",
                    }
                ],
            ),
            AIMessage(content="Respuesta final."),
        ]
    )
    conexion = FakeConnection([FILA_FE_1234])
    monkeypatch.setattr("app.services.chat_service.get_chat_model", lambda: modelo)
    monkeypatch.setattr("app.services.chat_service.build_engine", lambda settings: FakeEngine(conexion))
    client = TestClient(create_app())

    response = client.post("/chat", json={"question": "¿Valor glosado de FE-1234?"})

    assert response.json()["answer"] == "Consulto la factura.Respuesta final."
