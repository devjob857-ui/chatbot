"""Obtiene datos de MariaDB a partir de una pregunta en lenguaje natural.

Flujo: el modelo SQL decide si hace falta consultar y escribe un SELECT → se valida →
se ejecuta con un usuario de solo lectura. Si la validación o la ejecución fallan,
se le muestra el error al modelo y se reintenta una vez.
"""

import asyncio
import re
from collections.abc import Sequence
from dataclasses import dataclass

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.database.query_executor import QueryResult, run_select
from app.database.schema_inspector import load_data_dictionary
from app.llm.client import get_sql_model
from app.prompts.sql_generation import (
    NO_DATA_ANSWER,
    build_sql_retry_prompt,
    build_sql_system_prompt,
)
from app.security.sql_validator import UnsafeSQLError, validate_select

logger = get_logger(__name__)

MAX_ATTEMPTS = 2
# Turnos previos que ve el modelo SQL: suficientes para resolver "¿y esa factura?".
HISTORY_TURNS = 6
MAX_ERROR_LENGTH = 300

_FENCED_SQL = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
# Inicio de una sentencia SQL en una línea. Incluye sentencias de escritura a propósito:
# así llegan al validador, se rechazan y el modelo recibe el motivo, en vez de ignorarse.
_STATEMENT_START = re.compile(
    r"^\s*(SELECT|WITH|INSERT|UPDATE|DELETE|REPLACE|MERGE|DROP|ALTER|CREATE|TRUNCATE|"
    r"RENAME|GRANT|REVOKE|SET|SHOW|CALL|DO|HANDLER|LOAD|EXPLAIN|DESCRIBE|USE|LOCK)\b",
    re.IGNORECASE | re.MULTILINE,
)
_SELECT_ANYWHERE = re.compile(r"\bSELECT\b", re.IGNORECASE)


@dataclass(frozen=True)
class DataResult:
    """Resultado de consultar la base. `result` es None si no se pudo obtener."""

    sql: str | None
    result: QueryResult | None

    @property
    def failed(self) -> bool:
        return self.result is None


def extract_sql(reply: str) -> str | None:
    """Saca el SQL de la respuesta del modelo. None si el modelo dijo que no hacen falta datos."""
    text = reply.strip()
    fenced = _FENCED_SQL.search(text)
    if fenced:
        text = fenced.group(1).strip()
    if text.strip(" .\n").upper() == NO_DATA_ANSWER:
        return None
    match = _STATEMENT_START.search(text) or _SELECT_ANYWHERE.search(text)
    if match is None:
        # Ni SQL ni la palabra acordada: se trata como pregunta sin datos.
        return None
    return text[match.start():].strip().rstrip(";").strip()


def _build_messages(
    dictionary: str, question: str, history: Sequence[tuple[str, str]]
) -> list[BaseMessage]:
    # El historial va como texto de contexto, no como turnos de chat: si el modelo ve
    # respuestas previas en prosa, tiende a imitarlas en vez de devolver SQL.
    recent = list(history)[-HISTORY_TURNS:]
    if recent:
        lines = [f"{'Usuario' if role == 'user' else 'Asistente'}: {content}" for role, content in recent]
        content = (
            "Conversación previa (solo como contexto):\n"
            + "\n".join(lines)
            + f"\n\nÚltima pregunta del usuario: {question}"
        )
    else:
        content = question
    return [SystemMessage(content=build_sql_system_prompt(dictionary)), HumanMessage(content=content)]


def _database_error_message(error: SQLAlchemyError) -> str:
    # Solo el mensaje de MariaDB (p. ej. "Unknown column 'x'"), sin la consulta ni parámetros.
    original = getattr(error, "orig", None)
    message = str(original.args[-1]) if original is not None and original.args else type(error).__name__
    return message[:MAX_ERROR_LENGTH]


async def fetch_data(
    question: str, history: Sequence[tuple[str, str]] | None = None
) -> DataResult | None:
    """Devuelve los datos para responder la pregunta, o None si la pregunta no los necesita."""
    if not get_settings().database_configured:
        return None

    dictionary = load_data_dictionary()
    model = get_sql_model()
    messages = _build_messages(dictionary.text, question, history or [])
    max_rows = get_settings().sql_max_rows
    sql: str | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        reply = await model.ainvoke(messages)
        reply_text = reply.content if isinstance(reply.content, str) else str(reply.content)
        sql = extract_sql(reply_text)
        if sql is None:
            logger.info("La pregunta no requiere consultar la base de datos")
            return None

        try:
            safe_sql = validate_select(sql, dictionary.tables, max_rows)
            logger.info("Consulta generada (intento %d): %s", attempt, safe_sql)
            result = await asyncio.to_thread(run_select, safe_sql)
            return DataResult(sql=safe_sql, result=result)
        except UnsafeSQLError as error:
            feedback = str(error)
            logger.warning("Consulta rechazada (intento %d): %s | %s", attempt, feedback, sql)
        except SQLAlchemyError as error:
            feedback = _database_error_message(error)
            logger.warning("Error de la base de datos (intento %d): %s | %s", attempt, feedback, sql)

        messages.append(AIMessage(content=reply_text))
        messages.append(HumanMessage(content=build_sql_retry_prompt(feedback)))

    return DataResult(sql=sql, result=None)
