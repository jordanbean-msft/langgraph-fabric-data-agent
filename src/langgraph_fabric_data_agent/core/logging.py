"""Logging configuration utilities."""

import logging
import os
from contextvars import ContextVar
from typing import ClassVar

_invocation_id: ContextVar[str] = ContextVar("invocation_id", default="-")
_channel: ContextVar[str] = ContextVar("channel", default="-")
_mode: ContextVar[str] = ContextVar("mode", default="-")
_user_id: ContextVar[str] = ContextVar("user_id", default="-")


class ContextFilter(logging.Filter):
    """Attach correlation metadata to each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.invocation_id = _invocation_id.get()
        record.channel = _channel.get()
        record.mode = _mode.get()
        record.user_id = _user_id.get()
        return True


class _ColorFormatter(logging.Formatter):
    """Optionally colorize log levels using ANSI escape sequences."""

    _reset: ClassVar[str] = "\x1b[0m"
    _level_colors: ClassVar[dict[int, str]] = {
        logging.DEBUG: "\x1b[36m",
        logging.INFO: "\x1b[32m",
        logging.WARNING: "\x1b[33m",
        logging.ERROR: "\x1b[31m",
        logging.CRITICAL: "\x1b[35m",
    }

    def __init__(self, *args: object, use_color: bool, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        if not self._use_color:
            return super().format(record)

        original_level_name = record.levelname
        color = self._level_colors.get(record.levelno)
        if color:
            record.levelname = f"{color}{original_level_name}{self._reset}"

        try:
            return super().format(record)
        finally:
            record.levelname = original_level_name


def _resolve_log_level(level: str) -> int:
    """Resolve a log level name to its numeric value."""
    numeric_level = getattr(logging, level.upper(), None)
    if numeric_level is None:
        return logging.INFO
    return numeric_level


def _should_use_color(stream: object) -> bool:
    """Enable ANSI colors only when writing to an interactive terminal."""
    if os.getenv("NO_COLOR") is not None:
        return False

    if os.getenv("TERM", "").lower() == "dumb":
        return False

    isatty = getattr(stream, "isatty", None)
    return bool(callable(isatty) and isatty())


def _apply_log_level_overrides(log_level_override: str | None) -> None:
    """Apply per-logger overrides from a comma-separated configuration string."""
    if not log_level_override:
        return

    logger = logging.getLogger(__name__)

    for pair in log_level_override.split(","):
        stripped_pair = pair.strip()
        if not stripped_pair:
            continue

        if ":" not in stripped_pair:
            logger.warning(
                "Invalid log level override format (missing colon): %s. Expected 'logger_name:LEVEL'",
                stripped_pair,
            )
            continue

        logger_name, level_name = stripped_pair.split(":", 1)
        logger_name = logger_name.strip()
        level_name = level_name.strip().upper()

        if not logger_name:
            logger.warning("Empty logger name in override pair: %s", stripped_pair)
            continue

        if level_name == "OFF":
            numeric_level = logging.CRITICAL + 1
        else:
            numeric_level = getattr(logging, level_name, None)
            if numeric_level is None:
                logger.warning(
                    "Invalid log level in override: %s (valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL, OFF)",
                    level_name,
                )
                continue

        logging.getLogger(logger_name).setLevel(numeric_level)
        logger.info("Logger level override applied: logger=%s level=%s", logger_name, level_name)


def configure_logging(level: str = "INFO", log_level_override: str | None = None) -> None:
    """Configure root logger for predictable debugging output."""
    handler = logging.StreamHandler()
    formatter = _ColorFormatter(
        fmt=(
            "%(asctime)s | %(levelname)s | %(name)s | "
            "inv=%(invocation_id)s channel=%(channel)s mode=%(mode)s user=%(user_id)s | %(message)s"
        ),
        use_color=_should_use_color(handler.stream),
    )

    handler.setFormatter(formatter)
    handler.addFilter(ContextFilter())

    root = logging.getLogger()
    root.setLevel(_resolve_log_level(level))
    root.handlers.clear()
    root.addHandler(handler)

    _apply_log_level_overrides(log_level_override)


def set_log_context(*, invocation_id: str, channel: str, mode: str, user_id: str) -> None:
    """Set contextual log values for the current async flow."""
    _invocation_id.set(invocation_id)
    _channel.set(channel)
    _mode.set(mode)
    _user_id.set(user_id)
