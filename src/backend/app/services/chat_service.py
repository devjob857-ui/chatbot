"""Servicio de chat.

Antes de responder, consulta MariaDB si la pregunta lo requiere (ver `sql_service`).
Los datos obtenidos se entregan al modelo de chat como contexto, y este redacta la
respuesta en lenguaje natural. El resto de la aplicación no depende de estos pasos.
"""

from collections.abc import AsyncIterator, Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.database.query_executor import QueryResult
from app.llm.client import get_chat_model
from app.prompts.answer import (
    DATA_CONTEXT,
    DATA_ERROR_CONTEXT,
    NO_ROWS_CONTEXT,
    SYSTEM_PROMPT,
    TRUNCATED_NOTE,
)
from app.services.sql_service import DataResult, fetch_data

logger = get_logger(__name__)


def format_rows(result: QueryResult) -> str:
    """Filas como `campo: valor`. Es menos ambiguo que una tabla para modelos pequeños
    (con una tabla, un conteo de 101 se leía como "la factura 101")."""
    labels = [column.replace("_", " ") for column in result.columns]
    blocks = []
    for number, values in enumerate(result.rows, start=1):
        fields = "; ".join(
            f"{label}: {value.replace(chr(10), ' ')}" for label, value in zip(labels, values)
        )
        blocks.append(fields if len(result.rows) == 1 else f"{number}. {fields}")
    return "\n".join(blocks)


def build_system_prompt(data: DataResult | None) -> str:
    """Instrucciones de sistema, con los datos consultados cuando los hay."""
    if data is None:
        return SYSTEM_PROMPT
    if data.failed:
        return SYSTEM_PROMPT + "\n" + DATA_ERROR_CONTEXT
    result = data.result
    if not result.rows:
        return SYSTEM_PROMPT + "\n" + NO_ROWS_CONTEXT
    note = TRUNCATED_NOTE.format(count=len(result.rows)) if result.truncated else ""
    return SYSTEM_PROMPT + "\n" + DATA_CONTEXT.format(
        count=len(result.rows), table=format_rows(result), note=note
    )


async def stream_answer(
    question: str, history: Sequence[tuple[str, str]] | None = None
) -> AsyncIterator[str]:
    """Emite la respuesta del modelo en fragmentos de texto, a medida que se genera.

    `history` son turnos previos (rol, texto), en orden; el rol es "user" o "assistant".
    """
    try:
        data = await fetch_data(question, history)
    except Exception:
        # Si falla la parte de datos (p. ej. Ollama o MariaDB caídos), se responde igual,
        # avisando que no se pudo consultar, en vez de cortar la conversación.
        logger.exception("Error obteniendo datos para la pregunta")
        data = DataResult(sql=None, result=None)

    model = get_chat_model()
    messages: list[BaseMessage] = [SystemMessage(content=build_system_prompt(data))]
    for role, content in history or []:
        message_class = HumanMessage if role == "user" else AIMessage
        messages.append(message_class(content=content))
    messages.append(HumanMessage(content=question))
    async for chunk in model.astream(messages):
        yield chunk.content
