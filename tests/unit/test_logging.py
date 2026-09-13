import json
import logging

from app.api.main import JsonFormatter


def test_json_formatter_includes_request_context() -> None:
    record = logging.LogRecord(
        name="erp",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="http_request",
        args=(),
        exc_info=None,
    )
    record.request_id = "request-123"
    record.method = "GET"
    record.path = "/health/live"
    record.status_code = 200
    record.duration_ms = 1.25

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "erp"
    assert payload["message"] == "http_request"
    assert payload["request_id"] == "request-123"
    assert payload["method"] == "GET"
    assert payload["path"] == "/health/live"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == 1.25
