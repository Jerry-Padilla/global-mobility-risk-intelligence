import json
import logging


class JsonFormatter(logging.Formatter):
    def format(self, record):
        value = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            value["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "pipeline"):
            value["pipeline"] = record.pipeline
        return json.dumps(value)
