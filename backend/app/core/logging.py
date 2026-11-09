"""Logging setup with secret redaction so tokens never end up in log output."""

from __future__ import annotations

import logging
import re

_REDACT_PATTERNS = [
    re.compile(r"(gh[pousr]_[A-Za-z0-9]{20,})"),
    re.compile(r"(github_pat_[A-Za-z0-9_]{20,})"),
    re.compile(r"(squ_[A-Za-z0-9]{20,}|sqp_[A-Za-z0-9]{20,})"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]+"),
    re.compile(r"(?i)(authorization['\"]?\s*[:=]\s*['\"]?)[^'\",\s]+"),
]


def redact(text: str) -> str:
    for pattern in _REDACT_PATTERNS:
        if pattern.groups == 1 and not pattern.pattern.startswith("(?i)"):
            text = pattern.sub("[REDACTED]", text)
        else:
            text = pattern.sub(lambda m: m.group(1) + "[REDACTED]", text)
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - defensive
            return True
        record.msg = redact(message)
        record.args = ()
        return True


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.addFilter(RedactingFilter())
    handler.set_name("shieldops")
    root = logging.getLogger()
    # Replace only our own handler so test/log-capture handlers stay intact.
    root.handlers = [h for h in root.handlers if h.get_name() != "shieldops"]
    root.addHandler(handler)
    root.setLevel(level)
