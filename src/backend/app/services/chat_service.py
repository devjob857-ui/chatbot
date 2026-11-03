"""Servicio de chat.

PROVISIONAL: el flujo real (intención → RAG → SQL validado → LLM, ver AGENTS.md
sección 3) aún no está implementado. Mientras tanto, `stream_answer` emite una
respuesta fija por palabras para poder probar el transporte SSE y la UI.
Al implementar el flujo real, sustituir el cuerpo de `stream_answer` y dejar
la misma firma: el resto de la aplicación no debe cambiar.
"""

import asyncio
from collections.abc import AsyncIterator

_PLACEHOLDER_ANSWER = (
    "El asistente aún no está conectado al flujo de RAG, SQL y LLM. "
    "Esta es una respuesta de prueba del transporte de streaming."
)


async def stream_answer(question: str) -> AsyncIterator[str]:
    """Emite la respuesta en fragmentos de texto."""
    for word in _PLACEHOLDER_ANSWER.split(" "):
        yield word + " "
        await asyncio.sleep(0.03)
