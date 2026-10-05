"""Logging: konsol + logs/ papkasi. Maxfiy ma'lumotlar (token) yashiriladi."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import Settings

FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


class RedactFilter(logging.Filter):
    def __init__(self, secrets: list[str]) -> None:
        super().__init__()
        self._secrets = [s for s in secrets if s]

    def filter(self, record: logging.LogRecord) -> bool:
        if self._secrets:
            msg = record.getMessage()
            for secret in self._secrets:
                if secret in msg:
                    msg = msg.replace(secret, "***")
            record.msg, record.args = msg, ()
        return True


def setup_logging(settings: Settings) -> None:
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    redact = RedactFilter([settings.bot_token])
    formatter = logging.Formatter(FORMAT)

    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(log_dir / "bot.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8"),
    ]
    errors = RotatingFileHandler(log_dir / "errors.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    errors.setLevel(logging.ERROR)
    handlers.append(errors)

    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    root.handlers.clear()
    for h in handlers:
        h.setFormatter(formatter)
        h.addFilter(redact)
        root.addHandler(h)

    audit = RotatingFileHandler(log_dir / "audit.log", maxBytes=5_000_000, backupCount=10, encoding="utf-8")
    audit.setFormatter(formatter)
    audit.addFilter(redact)
    logging.getLogger("audit").addHandler(audit)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
