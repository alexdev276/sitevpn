import logging
from pathlib import Path

import structlog

from src.core.config import Settings


def configure_logging(settings: Settings) -> None:
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]
    logging.basicConfig(level=getattr(logging, settings.app_log_level.upper(), logging.INFO))
    if settings.app_log_file:
        Path(settings.app_log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(settings.app_log_file)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        logging.getLogger().addHandler(file_handler)

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

