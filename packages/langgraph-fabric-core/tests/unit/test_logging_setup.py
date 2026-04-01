import logging

import pytest
from langgraph_fabric_core.core.logging import _ColorFormatter, configure_logging


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

    assert "\x1b[31mERROR\x1b[0m" in formatted


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
