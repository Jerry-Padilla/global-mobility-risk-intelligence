import json
import logging

from apps.core.logging import JsonFormatter


def test_pipeline_metrics_remain_structured():
    record = logging.LogRecord(
        "ingestion", logging.INFO, __file__, 1, "Ingestion completed", (), None
    )
    record.pipeline = {"loaded": 10, "rejected": 2, "duration_seconds": 1.5}
    parsed = json.loads(JsonFormatter().format(record))
    assert parsed["pipeline"]["loaded"] == 10
    assert parsed["pipeline"]["duration_seconds"] == 1.5
