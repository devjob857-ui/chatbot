from typing import Literal

from pydantic import BaseModel, Field

MAX_QUESTION_LENGTH = 2000
MAX_HISTORY_MESSAGES = 20


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=MAX_QUESTION_LENGTH)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_LENGTH)
    session_id: str | None = Field(default=None, max_length=64)
    history: list[ChatTurn] | None = Field(default=None, max_length=MAX_HISTORY_MESSAGES)


class ChatResponse(BaseModel):
    answer: str
