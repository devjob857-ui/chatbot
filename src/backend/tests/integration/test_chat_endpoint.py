import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
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


def test_chat_stream_emits_tokens_then_done(client: TestClient) -> None:
    response = client.post("/chat/stream", json={"question": "hola"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(response.text)
    names = [name for name, _ in events]
    assert names[-1] == "done"
    assert all(name == "token" for name in names[:-1])
    assert len(names) > 1

    text = "".join(data["text"] for name, data in events if name == "token")
    assert text.strip()


def test_chat_full_response(client: TestClient) -> None:
    response = client.post("/chat", json={"question": "hola"})
    assert response.status_code == 200
    assert response.json()["answer"].strip()


@pytest.mark.parametrize("question", ["", "x" * 2001])
def test_chat_rejects_invalid_question(client: TestClient, question: str) -> None:
    response = client.post("/chat", json={"question": question})
    assert response.status_code == 422
