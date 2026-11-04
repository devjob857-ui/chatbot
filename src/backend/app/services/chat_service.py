"""Servicio de chat.

Por ahora responde directamente con el modelo local. El flujo completo
(intención → RAG → SQL validado → LLM, ver AGENTS.md sección 3) se agregará
detrás de esta misma firma: el resto de la aplicación no debe cambiar.
"""

from collections.abc import AsyncIterator, Sequence

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from app.core.config import get_settings
from app.database.connection import build_engine
from app.database.query_executor import buscar_factura
from app.llm.client import get_chat_model
from app.prompts.answer import SYSTEM_PROMPT
from app.services.intent_service import herramienta_glosa, resumir_glosa


async def stream_answer(
    question: str, history: Sequence[tuple[str, str]] | None = None
) -> AsyncIterator[str]:
    """Emite la respuesta del modelo en fragmentos de texto, a medida que se genera.

    `history` son turnos previos (rol, texto), en orden; el rol es "user" o "assistant".
    """
    model = get_chat_model().bind_tools([herramienta_glosa()])
    messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]
    for role, content in history or []:
        message_class = HumanMessage if role == "user" else AIMessage
        messages.append(message_class(content=content))
    messages.append(HumanMessage(content=question))

    primera: AIMessage | None = None
    async for chunk in model.astream(messages):
        primera = chunk if primera is None else primera + chunk
        yield chunk.content

    if primera is None or not primera.tool_calls:
        return

    llamada = primera.tool_calls[0]
    with build_engine(get_settings()).connect() as conexion:
        filas = buscar_factura(conexion, llamada["args"]["prefijo"], llamada["args"]["numero"])
    messages.append(primera)
    messages.append(ToolMessage(content=resumir_glosa(filas), tool_call_id=llamada["id"]))
    async for chunk in model.astream(messages):
        yield chunk.content
