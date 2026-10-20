import contextvars
import json
import logging
import re
import sys
from datetime import UTC, datetime

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

PAN_REGEX = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)
AADHAAR_REGEX = re.compile(r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b")
CARD_REGEX = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
PHONE_REGEX = re.compile(r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b")


def redact_pii(text: str) -> str:
    """Mask sensitive PII fields (PAN, Aadhaar, card numbers, phone numbers) with redaction tokens."""
    if not isinstance(text, str):
        return text
    text = PAN_REGEX.sub("[REDACTED_PAN]", text)
    text = AADHAAR_REGEX.sub("[REDACTED_AADHAAR]", text)
    text = CARD_REGEX.sub("[REDACTED_CARD]", text)
    text = PHONE_REGEX.sub("[REDACTED_PHONE]", text)
    return text


class StructuredJSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = record.getMessage()
        safe_msg = redact_pii(msg)
        req_id = request_id_ctx.get()

        log_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": safe_msg,
            "request_id": req_id or getattr(record, "request_id", None),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJSONFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)

    return logging.getLogger("riskwise")


logger = setup_logging()
