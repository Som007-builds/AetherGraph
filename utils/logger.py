import logging
import os
from datetime import datetime

# Load log level from config or environment variable
LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)


def get_logger(name: str):
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(LOG_LEVEL)

        handler = logging.StreamHandler()

        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s - %(name)s - %(message)s"
        )

        handler.setFormatter(formatter)
        logger.addHandler(handler)
    else:
        logger.setLevel(LOG_LEVEL)

    return logger


def log_event(logger, event: str, data=None):
    timestamp = datetime.utcnow().isoformat()

    message = f"[EVENT] {timestamp} | {event}"

    if data:
        message += f" | {data}"

    logger.info(message)