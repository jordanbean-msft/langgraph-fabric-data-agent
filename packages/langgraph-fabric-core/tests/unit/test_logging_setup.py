import logging

import pytest
from langgraph_fabric_core.core.logging import (
    ContextFilter,
    _ColorFormatter,
    _should_use_color,
    configure_logging,
    set_log_context,
)


@pytest.fixture(autouse=True)
def restore_logging_state():
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level

    tracked_loggers = [
        "langgraph_fabric_core.graph",
        "azure.core",
        "test.invalid",
    ]

    for logger_name in tracked_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.NOTSET)
        logger.disabled = False

    yield

    root.handlers.clear()
    for handler in original_handlers:
        root.addHandler(handler)
    root.setLevel(original_level)

    for logger_name in tracked_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.NOTSET)
        logger.disabled = False


def test_configure_logging_applies_logger_overrides():
    configure_logging(
        "warning",
        "langgraph_fabric_core.graph:DEBUG,azure.core:ERROR",
    )

    assert logging.getLogger().level == logging.WARNING
    assert logging.getLogger("langgraph_fabric_core.graph").level == logging.DEBUG
    assert logging.getLogger("azure.core").level == logging.ERROR


def test_configure_logging_supports_off_override():
    configure_logging("INFO", "langgraph_fabric_core.graph:OFF")

    assert logging.getLogger("langgraph_fabric_core.graph").level > logging.CRITICAL


def test_configure_logging_ignores_invalid_override_level():
    configure_logging("INFO", "test.invalid:NOPE")

    assert logging.getLogger("test.invalid").level == logging.NOTSET


def test_color_formatter_colorizes_levelname_when_enabled():
    formatter = _ColorFormatter("%(levelname)s | %(message)s", use_color=True)
    logger = logging.getLogger("test.color")
    record = logger.makeRecord(
        logger.name,
        logging.ERROR,
        __file__,
        1,
        "boom",
        (),
        None,
    )

    formatted = formatter.format(record)

    assert "\x1b[31mERROR" in formatted
    assert "\x1b[0m" in formatted


def test_color_formatter_colorizes_logger_name_blue() -> None:
    formatter = _ColorFormatter("%(name)s | %(message)s", use_color=True)
    logger = logging.getLogger("test.color.blue")
    record = logger.makeRecord(logger.name, logging.INFO, __file__, 1, "hi", (), None)

    formatted = formatter.format(record)

    assert "\x1b[34mtest.color.blue\x1b[0m" in formatted


def test_color_formatter_colorizes_message_for_warning_and_above() -> None:
    formatter = _ColorFormatter("%(levelname)s | %(message)s", use_color=True)
    logger = logging.getLogger("test.color.msg")
    for level, color in [
        (logging.WARNING, "\x1b[33m"),
        (logging.ERROR, "\x1b[31m"),
        (logging.CRITICAL, "\x1b[1;31m"),
    ]:
        record = logger.makeRecord(logger.name, level, __file__, 1, "alert", (), None)
        formatted = formatter.format(record)
        assert f"{color}alert\x1b[0m" in formatted


def test_color_formatter_does_not_colorize_message_for_info_and_debug() -> None:
    formatter = _ColorFormatter("%(levelname)s | %(message)s", use_color=True)
    logger = logging.getLogger("test.color.msg")
    for level in (logging.INFO, logging.DEBUG):
        record = logger.makeRecord(logger.name, level, __file__, 1, "plain", (), None)
        formatted = formatter.format(record)
        # Message text should appear without color wrapping
        assert "plain" in formatted
        assert formatted.count("plain") == 1
        # The word "plain" should not be preceded by a color code
        idx = formatted.index("plain")
        assert formatted[idx - 4 : idx] != "\x1b[32m"


def test_color_formatter_dims_timestamp() -> None:
    formatter = _ColorFormatter(
        "%(asctime)s %(levelname)s %(message)s",
        use_color=True,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("test.color.ts")
    record = logger.makeRecord(logger.name, logging.INFO, __file__, 1, "ts", (), None)

    formatted = formatter.format(record)

    # Timestamp should start with dim code
    assert formatted.startswith("\x1b[2m")
    # Dim region should be closed before the level color
    dim_end = formatted.index("\x1b[0m")
    level_color_idx = formatted.index("\x1b[32m")  # green for INFO
    assert dim_end < level_color_idx


def test_color_formatter_uses_bold_red_for_critical() -> None:
    formatter = _ColorFormatter("%(levelname)s | %(message)s", use_color=True)
    logger = logging.getLogger("test.color.crit")
    record = logger.makeRecord(logger.name, logging.CRITICAL, __file__, 1, "fail", (), None)

    formatted = formatter.format(record)

    assert "\x1b[1;31mCRITICAL\x1b[0m" in formatted


def test_color_formatter_does_not_colorize_when_disabled():
    formatter = _ColorFormatter("%(levelname)s | %(message)s", use_color=False)
    logger = logging.getLogger("test.color")
    record = logger.makeRecord(
        logger.name,
        logging.WARNING,
        __file__,
        1,
        "watch out",
        (),
        None,
    )

    formatted = formatter.format(record)

    assert "WARNING | watch out" in formatted
    assert "\x1b[" not in formatted


def test_color_formatter_does_not_dim_timestamp_when_disabled() -> None:
    formatter = _ColorFormatter(
        "%(asctime)s | %(message)s",
        use_color=False,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("test.color.ts")
    record = logger.makeRecord(logger.name, logging.INFO, __file__, 1, "ts", (), None)

    formatted = formatter.format(record)

    assert "\x1b[2m" not in formatted


# ---------------------------------------------------------------------------
# configure_logging edge cases
# ---------------------------------------------------------------------------


def test_configure_logging_with_invalid_top_level_log_level_defaults_to_info() -> None:
    """An unrecognized level string falls back to INFO."""
    configure_logging("TOTALLY_INVALID_LEVEL")
    # _resolve_log_level returns logging.INFO for unknown names
    assert logging.getLogger().level == logging.INFO


def test_configure_logging_with_none_override_succeeds() -> None:
    """configure_logging(override=None) must not raise."""
    configure_logging("INFO", log_level_override=None)


def test_configure_logging_ignores_empty_pair_in_comma_separated_override() -> None:
    """Empty tokens produced by a leading/trailing/double comma are silently skipped."""
    configure_logging("INFO", log_level_override=",langgraph_fabric_core.graph:DEBUG,")
    assert logging.getLogger("langgraph_fabric_core.graph").level == logging.DEBUG


def test_configure_logging_warns_on_missing_colon_in_override() -> None:
    """An override entry without a colon emits a warning and is skipped."""
    from unittest.mock import patch

    module_logger = logging.getLogger("langgraph_fabric_core.core.logging")
    with patch.object(module_logger, "warning") as mock_warn:
        configure_logging("INFO", log_level_override="missing_colon_entry")
    assert mock_warn.called
    assert any("missing colon" in str(c).lower() for c in mock_warn.call_args_list)


def test_configure_logging_warns_on_empty_logger_name() -> None:
    """An override with an empty logger name emits a warning and is skipped."""
    from unittest.mock import patch

    module_logger = logging.getLogger("langgraph_fabric_core.core.logging")
    with patch.object(module_logger, "warning") as mock_warn:
        configure_logging("INFO", log_level_override=":DEBUG")
    assert mock_warn.called
    assert any("empty logger name" in str(c).lower() for c in mock_warn.call_args_list)


# ---------------------------------------------------------------------------
# set_log_context / ContextFilter
# ---------------------------------------------------------------------------


def test_set_log_context_values_are_reflected_by_context_filter() -> None:
    """Values written by set_log_context appear on the next filtered log record."""
    set_log_context(
        invocation_id="inv-999",
        channel="test-channel",
        mode="local",
        user_id="user-xyz",
    )

    ctx_filter = ContextFilter()
    logger = logging.getLogger("test.set_log_context")
    record = logger.makeRecord(logger.name, logging.INFO, __file__, 1, "msg", (), None)
    ctx_filter.filter(record)

    assert record.invocation_id == "inv-999"
    assert record.channel == "test-channel"
    assert record.mode == "local"
    assert record.user_id == "user-xyz"


def test_context_filter_returns_true() -> None:
    """ContextFilter.filter always returns True (records are never suppressed)."""
    ctx_filter = ContextFilter()
    logger = logging.getLogger("test.context_filter")
    record = logger.makeRecord(logger.name, logging.DEBUG, __file__, 1, "msg", (), None)
    assert ctx_filter.filter(record) is True


# ---------------------------------------------------------------------------
# _should_use_color
# ---------------------------------------------------------------------------


def test_should_use_color_returns_false_when_no_color_env_is_set(monkeypatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    stream = type("FakeStream", (), {"isatty": lambda self: True})()
    assert _should_use_color(stream) is False


def test_should_use_color_returns_false_for_dumb_terminal(monkeypatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "dumb")
    stream = type("FakeStream", (), {"isatty": lambda self: True})()
    assert _should_use_color(stream) is False


def test_should_use_color_returns_true_for_interactive_terminal(monkeypatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    stream = type("FakeStream", (), {"isatty": lambda self: True})()
    assert _should_use_color(stream) is True


def test_should_use_color_returns_false_for_non_tty(monkeypatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("TERM", raising=False)
    stream = type("FakeStream", (), {"isatty": lambda self: False})()
    assert _should_use_color(stream) is False
