"""Structured logging helpers.

Provides a factory function for obtaining a consistently configured logger
that integrates with both Python's ``logging`` module and Prefect's built-in
log capture.
"""

from __future__ import annotations

import logging

from yhovi_pipeline.config import get_settings

_FORMATTER = logging.Formatter(
    "%(asctime)s %(levelname)-8s %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger configured at the level set in ``Settings``.

    Adds a ``StreamHandler`` with a consistent timestamp formatter on first
    call for a given name. Subsequent calls return the cached logger unchanged.

    Args:
        name: Logger name - conventionally ``__name__`` of the calling module.

    Returns:
        Configured ``logging.Logger`` instance.
    """
    settings = get_settings()
    level = settings.log_level.upper()

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        handler.setFormatter(_FORMATTER)
        logger.addHandler(handler)

    return logger
