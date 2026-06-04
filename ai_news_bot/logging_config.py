"""Logging setup for cron-friendly runs."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from ai_news_bot.paths import LOGS_DIR


def setup_logging(log_file: Optional[Path] = None, level: int = logging.INFO) -> None:
    """Configure root logger with console and optional file handler."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            logging.FileHandler(log_file, encoding="utf-8")
        )

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True,
    )
