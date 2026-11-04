import logging


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger del módulo. La configuración global se añadirá con la app."""
    return logging.getLogger(name)
