"""Descripción de la base de datos que se entrega al modelo (diccionario de datos)."""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings

_TABLE_HEADING = re.compile(r"^##\s+Tabla:\s*`?([A-Za-z0-9_]+)`?\s*$", re.MULTILINE)


@dataclass(frozen=True)
class DataDictionary:
    text: str
    tables: frozenset[str]


def parse_data_dictionary(text: str) -> DataDictionary:
    """Las tablas consultables son las que tienen una sección `## Tabla: <nombre>`."""
    tables = frozenset(name.lower() for name in _TABLE_HEADING.findall(text))
    return DataDictionary(text=text, tables=tables)


@lru_cache
def _load(path: Path, modified: float) -> DataDictionary:
    return parse_data_dictionary(path.read_text(encoding="utf-8"))


def load_data_dictionary() -> DataDictionary:
    """Lee el diccionario. Se vuelve a leer si el archivo cambia, sin reiniciar la app."""
    path = get_settings().data_dictionary_path
    return _load(path, path.stat().st_mtime)
