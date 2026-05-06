"""Logging setup."""

import logging
from pathlib import Path


def configure_logging(level: str = "INFO", log_file: str | None = None) -> None:
    fmt = "%(asctime)s %(levelname)s %(name)s - %(message)s"
    log_level = getattr(logging, level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(level=log_level, format=fmt, handlers=handlers, force=True)
