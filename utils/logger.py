import logging
from datetime import datetime


def get_logger(name: str):
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()

        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s - %(name)s - %(message)s"
        )

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def log_event(logger, event: str, data=None):
    timestamp = datetime.utcnow().isoformat()

    message = f"[EVENT] {timestamp} | {event}"

    if data:
        message += f" | {data}"

    logger.info(message)