"""Servicio de chat.

Por ahora responde directamente con el modelo local. El flujo completo
(intención → RAG → SQL validado → LLM, ver AGENTS.md sección 3) se agregará
detrás de esta misma firma: el resto de la aplicación no debe cambiar.
"""

from collections.abc import AsyncIterator, Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.llm.client import get_chat_model
from app.prompts.answer import SYSTEM_PROMPT


async def stream_answer(
    question: str, history: Sequence[tuple[str, str]] | None = None
) -> AsyncIterator[str]:
    """Emite la respuesta del modelo en fragmentos de texto, a medida que se genera.

    `history` son turnos previos (rol, texto), en orden; el rol es "user" o "assistant".
    """
    model = get_chat_model()
    messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]
    for role, content in history or []:
        message_class = HumanMessage if role == "user" else AIMessage
        messages.append(message_class(content=content))
    messages.append(HumanMessage(content=question))
    async for chunk in model.astream(messages):
        yield chunk.content
