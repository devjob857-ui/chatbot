import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.schemas.chat import ChatRequest, ChatResponse
from app.core.logging import get_logger
from app.services.chat_service import stream_answer

router = APIRouter(prefix="/chat", tags=["chat"])
logger = get_logger(__name__)


def _sse(event: str, data: dict) -> str:
    """Formatea un evento Server-Sent Events."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Respuesta completa, sin streaming."""
    history = [(turn.role, turn.content) for turn in request.history or []]
    parts = [chunk async for chunk in stream_answer(request.question, history)]
    return ChatResponse(answer="".join(parts).strip())


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Respuesta en streaming (text/event-stream).

    Eventos: `token` {"text"}, `done` {}, `error` {"message"}.
    """

    async def event_source() -> AsyncIterator[str]:
        try:
            history = [(turn.role, turn.content) for turn in request.history or []]
            async for chunk in stream_answer(request.question, history):
                yield _sse("token", {"text": chunk})
            yield _sse("done", {})
        except Exception:
            # No se exponen detalles internos al cliente; se registran en el servidor.
            logger.exception("Error generando la respuesta en streaming")
            yield _sse("error", {"message": "No se pudo generar la respuesta. Inténtalo de nuevo."})

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
