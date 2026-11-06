import asyncio
import datetime as dt
import itertools
from decimal import Decimal

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import Field
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.database.query_executor import QueryResult, format_value
from app.database.schema_inspector import parse_data_dictionary
from app.services import sql_service
from app.services.sql_service import extract_sql, fetch_data

DICTIONARY = parse_data_dictionary("## Tabla: cabezafactura\n\n## Tabla: detallefact\n")
ROWS = QueryResult(columns=["valor_glosado"], rows=[("1.250.000",)], truncated=False)


class RecordingSqlModel(GenericFakeChatModel):
    """Modelo SQL falso que guarda los mensajes recibidos en cada llamada."""

    received: list[list[BaseMessage]] = Field(default_factory=list)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.received.append(list(messages))
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


def make_model(*replies: str) -> RecordingSqlModel:
    return RecordingSqlModel(messages=iter([AIMessage(content=reply) for reply in replies]))


def configure(monkeypatch: pytest.MonkeyPatch, run_select) -> None:
    settings = Settings(_env_file=None, db_name="medicalidad", db_user="lector")
    monkeypatch.setattr(sql_service, "get_settings", lambda: settings)
    monkeypatch.setattr(sql_service, "load_data_dictionary", lambda: DICTIONARY)
    monkeypatch.setattr(sql_service, "run_select", run_select)


@pytest.fixture
def executed(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Base de datos falsa: guarda cada SQL ejecutado y devuelve ROWS."""
    calls: list[str] = []

    def fake_run_select(sql: str) -> QueryResult:
        calls.append(sql)
        return ROWS

    configure(monkeypatch, fake_run_select)
    return calls


def use_model(monkeypatch: pytest.MonkeyPatch, model: RecordingSqlModel) -> None:
    monkeypatch.setattr(sql_service, "get_sql_model", lambda: model)


def fetch(question: str, history=None):
    return asyncio.run(fetch_data(question, history))


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ("NINGUNA", None),
        ("ninguna.", None),
        ("Hola, ¿en qué te ayudo?", None),
        ("SELECT 1;", "SELECT 1"),
        ("```sql\nSELECT idcf FROM cabezafactura;\n```", "SELECT idcf FROM cabezafactura"),
        ("Aquí está la consulta:\nSELECT idcf FROM cabezafactura", "SELECT idcf FROM cabezafactura"),
        ("WITH c AS (SELECT 1) SELECT * FROM c", "WITH c AS (SELECT 1) SELECT * FROM c"),
        ("La consulta es SELECT 1", "SELECT 1"),
        # Las sentencias de escritura se extraen para que el validador las rechace.
        ("DELETE FROM cabezafactura", "DELETE FROM cabezafactura"),
        ("Claro:\nDROP TABLE cabezafactura;", "DROP TABLE cabezafactura"),
    ],
)
def test_extract_sql(reply: str, expected: str | None) -> None:
    assert extract_sql(reply) == expected


def test_question_without_data_does_not_touch_database(
    monkeypatch: pytest.MonkeyPatch, executed: list[str]
) -> None:
    use_model(monkeypatch, make_model("NINGUNA"))

    assert fetch("hola") is None
    assert executed == []


def test_valid_sql_is_validated_and_executed(
    monkeypatch: pytest.MonkeyPatch, executed: list[str]
) -> None:
    use_model(monkeypatch, make_model("SELECT glosatotal AS valor_glosado FROM cabezafactura"))

    data = fetch("¿Valor glosado de la FE-1234?")

    assert data is not None and data.result == ROWS
    assert executed == ["SELECT glosatotal AS valor_glosado FROM cabezafactura LIMIT 100"]


def test_unsafe_sql_is_never_executed_and_model_retries(
    monkeypatch: pytest.MonkeyPatch, executed: list[str]
) -> None:
    model = make_model("DELETE FROM cabezafactura", "SELECT idcf FROM cabezafactura")
    use_model(monkeypatch, model)

    data = fetch("¿Cuántas facturas hay?")

    assert data is not None and not data.failed
    assert executed == ["SELECT idcf FROM cabezafactura LIMIT 100"]
    # En el reintento, el modelo ve el error de validación.
    retry_messages = model.received[1]
    assert isinstance(retry_messages[-1], HumanMessage)
    assert "Solo se permiten consultas SELECT" in retry_messages[-1].content


def test_two_failures_return_failed_result(
    monkeypatch: pytest.MonkeyPatch, executed: list[str]
) -> None:
    use_model(monkeypatch, make_model("SELECT * FROM usuarios", "DROP TABLE cabezafactura"))

    data = fetch("dame los usuarios")

    assert data is not None and data.failed
    assert executed == []


def test_database_error_is_shown_to_model_on_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = itertools.count()

    def flaky_run_select(sql: str) -> QueryResult:
        if next(attempts) == 0:
            raise OperationalError(sql, {}, Exception(1054, "Unknown column 'valor' in 'field list'"))
        return ROWS

    configure(monkeypatch, flaky_run_select)
    model = make_model("SELECT valor FROM cabezafactura", "SELECT totalfactura FROM cabezafactura")
    use_model(monkeypatch, model)

    data = fetch("¿Total facturado?")

    assert data is not None and data.result == ROWS
    assert "Unknown column 'valor'" in model.received[1][-1].content


def test_sql_model_sees_dictionary_and_recent_history(
    monkeypatch: pytest.MonkeyPatch, executed: list[str]
) -> None:
    model = make_model("NINGUNA")
    use_model(monkeypatch, model)
    history = [("user" if i % 2 == 0 else "assistant", f"turno {i}") for i in range(10)]

    fetch("¿y esa factura?", history)

    system, user = model.received[0]
    assert isinstance(system, SystemMessage)
    assert "## Tabla: cabezafactura" in system.content
    # Un solo mensaje con los últimos 6 turnos como contexto y la pregunta al final.
    assert isinstance(user, HumanMessage)
    assert "turno 3" not in user.content
    assert all(f"turno {i}" in user.content for i in range(4, 10))
    assert user.content.endswith("Última pregunta del usuario: ¿y esa factura?")


def test_without_history_sql_model_receives_only_the_question(
    monkeypatch: pytest.MonkeyPatch, executed: list[str]
) -> None:
    model = make_model("NINGUNA")
    use_model(monkeypatch, model)

    fetch("hola")

    assert model.received[0][-1].content == "hola"


def test_without_database_configuration_no_model_is_called(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sql_service, "get_settings", lambda: Settings(_env_file=None, db_name="", db_user=""))

    def fail():
        raise AssertionError("no debe llamarse al modelo SQL")

    monkeypatch.setattr(sql_service, "get_sql_model", fail)

    assert fetch("¿Cuántas facturas hay?") is None


def test_parse_data_dictionary_finds_tables() -> None:
    text = "# Título\n## Tabla: cabezafactura\ntexto\n## Tabla: `DetalleFact`\n## Relaciones\n"
    assert parse_data_dictionary(text).tables == {"cabezafactura", "detallefact"}


def test_project_dictionary_declares_both_tables() -> None:
    path = Settings(_env_file=None).data_dictionary_path
    assert parse_data_dictionary(path.read_text(encoding="utf-8")).tables == {"cabezafactura", "detallefact"}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "(vacío)"),
        (1250000, "1.250.000"),
        (Decimal("1250000.00"), "1.250.000"),
        (Decimal("1234.5"), "1.234,50"),
        (dt.date(2026, 10, 5), "2026-10-05"),
        (dt.datetime(2026, 10, 5, 14, 30), "2026-10-05 14:30"),
        ("FE", "FE"),
    ],
)
def test_format_value(value: object, expected: str) -> None:
    assert format_value(value) == expected
