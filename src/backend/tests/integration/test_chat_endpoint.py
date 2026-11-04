import itertools
import json

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import Field

from app.main import create_app

FAKE_ANSWER = "Hola, soy el modelo de prueba."


class RecordingFakeChatModel(GenericFakeChatModel):
    """Modelo falso que guarda los mensajes recibidos en cada llamada."""

    received: list[list[BaseMessage]] = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        # El chat siempre enlaza la herramienta de glosa; este modelo no la usa.
        return self

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        self.received.append(messages)
        return super()._stream(messages, stop=stop, run_manager=run_manager, **kwargs)


@pytest.fixture
def fake_model() -> RecordingFakeChatModel:
    return RecordingFakeChatModel(messages=itertools.cycle([AIMessage(content=FAKE_ANSWER)]))


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, fake_model: RecordingFakeChatModel) -> TestClient:
    # Modelo falso: ninguna prueba depende de que Ollama esté corriendo.
    monkeypatch.setattr("app.services.chat_service.get_chat_model", lambda: fake_model)
    return TestClient(create_app())


def _parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        name, data = None, None
        for line in block.split("\n"):
            if line.startswith("event: "):
                name = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        events.append((name, data))
    return events


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_serves_frontend(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Medicalidad AI" in response.text


def test_chat_stream_emits_model_tokens_in_order_then_done(client: TestClient) -> None:
    response = client.post("/chat/stream", json={"question": "hola"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(response.text)
    names = [name for name, _ in events]
    assert names[-1] == "done"
    assert all(name == "token" for name in names[:-1])
    # Llega en varios fragmentos (streaming), no en un solo bloque.
    assert names.count("token") > 1

    text = "".join(data["text"] for name, data in events if name == "token")
    assert text == FAKE_ANSWER


def test_chat_full_response_returns_model_answer(client: TestClient) -> None:
    response = client.post("/chat", json={"question": "hola"})
    assert response.status_code == 200
    assert response.json()["answer"] == FAKE_ANSWER


def test_model_receives_the_user_question(
    client: TestClient, fake_model: RecordingFakeChatModel
) -> None:
    questions = ["¿Qué es Medicalidad?", "¿Qué servicios ofrecen?"]

    for question in questions:
        client.post("/chat/stream", json={"question": question})

    # Cada llamada al modelo termina con la pregunta del usuario que la originó.
    last_messages = [messages[-1] for messages in fake_model.received]
    assert all(isinstance(message, HumanMessage) for message in last_messages)
    assert [message.content for message in last_messages] == questions


def test_model_receives_spanish_system_instruction(
    client: TestClient, fake_model: RecordingFakeChatModel
) -> None:
    client.post("/chat/stream", json={"question": "hola"})

    first_message = fake_model.received[0][0]
    assert isinstance(first_message, SystemMessage)
    assert "español" in first_message.content.lower()


def test_model_receives_previous_turns_in_order_before_current_question(
    client: TestClient, fake_model: RecordingFakeChatModel
) -> None:
    history = [
        {"role": "user", "content": "¿Qué es la hipertensión?"},
        {"role": "assistant", "content": "Es la presión arterial alta."},
    ]

    client.post(
        "/chat/stream",
        json={"question": "¿Y cómo se previene?", "history": history},
    )

    messages = fake_model.received[0]
    assert isinstance(messages[0], SystemMessage)
    assert [type(message) for message in messages[1:]] == [
        HumanMessage,
        AIMessage,
        HumanMessage,
    ]
    assert [message.content for message in messages[1:]] == [
        "¿Qué es la hipertensión?",
        "Es la presión arterial alta.",
        "¿Y cómo se previene?",
    ]


def test_full_response_endpoint_also_uses_history(
    client: TestClient, fake_model: RecordingFakeChatModel
) -> None:
    history = [
        {"role": "user", "content": "¿Qué es la hipertensión?"},
        {"role": "assistant", "content": "Es la presión arterial alta."},
    ]

    response = client.post(
        "/chat",
        json={"question": "¿Y cómo se previene?", "history": history},
    )

    assert response.status_code == 200
    messages = fake_model.received[0]
    assert [message.content for message in messages[1:]] == [
        "¿Qué es la hipertensión?",
        "Es la presión arterial alta.",
        "¿Y cómo se previene?",
    ]


@pytest.mark.parametrize("question", ["", "x" * 2001])
def test_chat_rejects_invalid_question(client: TestClient, question: str) -> None:
    response = client.post("/chat", json={"question": question})
    assert response.status_code == 422


def test_chat_rejects_history_with_more_than_20_messages(client: TestClient) -> None:
    history = [
        {"role": "user" if index % 2 == 0 else "assistant", "content": f"mensaje {index}"}
        for index in range(21)
    ]

    response = client.post(
        "/chat/stream",
        json={"question": "¿Y ahora?", "history": history},
    )

    assert response.status_code == 422


def test_chat_rejects_history_message_longer_than_question_limit(client: TestClient) -> None:
    history = [{"role": "user", "content": "x" * 2001}]

    response = client.post(
        "/chat/stream",
        json={"question": "¿Y ahora?", "history": history},
    )

    assert response.status_code == 422
