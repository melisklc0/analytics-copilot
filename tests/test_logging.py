import json
import logging

from analytics_copilot.observability.logger import CustomJSONFormatter, setup_logging


def test_setup_logging_runs_without_error() -> None:
    setup_logging()

    logger = logging.getLogger("tests.logging")
    logger.info("logging smoke test", extra={"request_id": "req-test"})


def test_json_formatter_preserves_extra_fields() -> None:
    formatter = CustomJSONFormatter(
        fmt_keys={
            "level": "levelname",
            "message": "message",
            "logger": "name",
        },
        builtin_attrs=[
            "args",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
        ],
    )
    record = logging.LogRecord(
        name="tests.logging",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-123"

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "INFO"
    assert payload["message"] == "hello"
    assert payload["logger"] == "tests.logging"
    assert payload["request_id"] == "req-123"
