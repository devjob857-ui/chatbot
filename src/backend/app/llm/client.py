"""Creación de los modelos de chat. El resto de la app no necesita saber que es Ollama."""

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

from app.core.config import get_settings


def get_chat_model() -> BaseChatModel:
    """Modelo que conversa con el usuario."""
    settings = get_settings()
    return ChatOllama(base_url=settings.ollama_base_url, model=settings.llm_model)


def get_sql_model() -> BaseChatModel:
    """Modelo que escribe las consultas SQL. Temperatura 0: respuestas deterministas."""
    settings = get_settings()
    return ChatOllama(base_url=settings.ollama_base_url, model=settings.sql_model, temperature=0)
