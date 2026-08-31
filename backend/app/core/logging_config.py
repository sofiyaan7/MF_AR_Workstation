"""Application (technical) logging.

Business audit events go to the ``activity_logs`` table via ActivityService and
are deliberately kept separate from these logs. A redaction filter is installed
as a defence in depth so that a stray log call cannot leak a credential.
"""
import logging
import re
import sys

from app.core.config import settings

_SENSITIVE_PATTERNS = [
    re.compile(r'((?:password|passwd|pwd|secret|token|authorization|api[_-]?key)'
               r'["\']?\s*[:=]\s*["\']?)([^\s,;"\'}]+)', re.IGNORECASE),
    re.compile(r"(\$argon2[a-z]{1,3}\$)[^\s\"']+", re.IGNORECASE),
    re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    re.compile(r"\b(eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,})\b"),
]


class RedactingFilter(logging.Filter):
    """Masks anything that looks like a credential before it reaches a handler."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - defensive
            return True
        redacted = self.redact(message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True

    @staticmethod
    def redact(message: str) -> str:
        for pattern in _SENSITIVE_PATTERNS:
            if pattern.groups >= 2:
                message = pattern.sub(r"\1[REDACTED]", message)
            else:
                message = pattern.sub("[REDACTED]", message)
        return message


def configure_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.addFilter(RedactingFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(max(level, logging.WARNING))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
