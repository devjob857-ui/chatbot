"""Servicio de chat.

Por ahora responde directamente con el modelo local. El flujo completo
(intención → RAG → SQL validado → LLM, ver AGENTS.md sección 3) se agregará
detrás de esta misma firma: el resto de la aplicación no debe cambiar.
"""

from collections.abc import AsyncIterator

from langchain_core.messages import HumanMessage, SystemMessage

from app.llm.client import get_chat_model
from app.prompts.answer import SYSTEM_PROMPT


async def stream_answer(question: str) -> AsyncIterator[str]:
    """Emite la respuesta del modelo en fragmentos de texto, a medida que se genera."""
    model = get_chat_model()
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=question)]
    async for chunk in model.astream(messages):
        yield chunk.content
