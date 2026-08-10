"""
Jan Vaani — Structured Logger
Uses Python's logging with a consistent format.
"""
import logging
import sys
from app.config import settings


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # already configured

    level = logging.DEBUG if settings.is_development else logging.INFO
    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    return logger
