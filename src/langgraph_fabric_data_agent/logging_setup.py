"""Logging configuration utilities."""

import logging
from contextvars import ContextVar

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


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger for predictable debugging output."""
    formatter = logging.Formatter(
        fmt=(
            "%(asctime)s | %(levelname)s | %(name)s | "
            "inv=%(invocation_id)s channel=%(channel)s mode=%(mode)s user=%(user_id)s | %(message)s"
        )
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(ContextFilter())

    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers.clear()
    root.addHandler(handler)


def set_log_context(*, invocation_id: str, channel: str, mode: str, user_id: str) -> None:
    """Set contextual log values for the current async flow."""
    _invocation_id.set(invocation_id)
    _channel.set(channel)
    _mode.set(mode)
    _user_id.set(user_id)
