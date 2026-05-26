import logging
import os
import json
import time
from datetime import datetime
from functools import wraps

# Load log level from config or environment variable
LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)

# Optional structured (JSON) log output — set LOG_FORMAT=json in .env
LOG_FORMAT_STR = os.getenv("LOG_FORMAT", "text").lower()


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(LOG_LEVEL)

        handler = logging.StreamHandler()

        if LOG_FORMAT_STR == "json":
            # Structured JSON — machine-readable for log aggregators
            formatter = logging.Formatter(
                '{"time":"%(asctime)s","level":"%(levelname)s",'
                '"logger":"%(name)s","msg":"%(message)s"}'
            )
        else:
            formatter = logging.Formatter(
                "[%(asctime)s] %(levelname)s - %(name)s - %(message)s"
            )

        handler.setFormatter(formatter)
        logger.addHandler(handler)
    else:
        logger.setLevel(LOG_LEVEL)

    return logger


def log_event(logger: logging.Logger, event: str, data: dict | None = None) -> None:
    timestamp = datetime.utcnow().isoformat()

    if LOG_FORMAT_STR == "json":
        payload = {"event": event, "time": timestamp}
        if data:
            payload.update(data)
        logger.info(json.dumps(payload))
    else:
        message = f"[EVENT] {timestamp} | {event}"
        if data:
            message += f" | {data}"
        logger.info(message)


def trace_agent(agent_name: str):
    """
    Decorator that wraps an agent function with automatic start/complete/fail
    logging and elapsed-time tracking.

    Usage:
        @trace_agent("reader")
        def process_paper(paper_meta, pdf_path): ...
    """
    _logger = get_logger(f"agent.{agent_name}")

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            t0 = time.perf_counter()
            _logger.info(f"[{agent_name.upper()}] START — {func.__name__}()")
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - t0
                _logger.info(
                    f"[{agent_name.upper()}] COMPLETE — {func.__name__}() "
                    f"in {elapsed:.2f}s"
                )
                return result
            except Exception as exc:
                elapsed = time.perf_counter() - t0
                _logger.error(
                    f"[{agent_name.upper()}] FAILED — {func.__name__}() "
                    f"after {elapsed:.2f}s: {exc}"
                )
                raise
        return wrapper
    return decorator