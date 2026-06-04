#!/usr/bin/env python3
"""Phase 0 acceptance checks (see docs/IMPLEMENTATION_HANDBOOK.md)."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    msg = f"  [{status}] {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    if not ok:
        raise SystemExit(1)


def main() -> None:
    print("Phase 0 verification")
    print("-" * 40)

    # 0.1 Package import
    pkg = importlib.import_module("ai_news_bot")
    check("import ai_news_bot", True, f"version={getattr(pkg, '__version__', '?')}")

    # 0.1 Module files exist
    modules = [
        "ai_news_bot.config",
        "ai_news_bot.crawler",
        "ai_news_bot.classifier",
        "ai_news_bot.summarizer",
        "ai_news_bot.feishu_card",
        "ai_news_bot.main",
        "ai_news_bot.paths",
    ]
    for mod in modules:
        importlib.import_module(mod)
        check(f"import {mod}", True)

    # 0.2 Config files
    check(".env.example exists", (ROOT / ".env.example").is_file())
    check("requirements.txt exists", (ROOT / "requirements.txt").is_file())
    check("README.md exists", (ROOT / "README.md").is_file())
    check("pyproject.toml exists", (ROOT / "pyproject.toml").is_file())

    # 0.3 CLI skeleton (--help)
    from ai_news_bot.main import main as cli_main

    check("main() callable", callable(cli_main))

    # Directories
    check("logs/ directory", (ROOT / "logs").is_dir())
    check("output/ directory", (ROOT / "output").is_dir())

    print("-" * 40)
    print("All Phase 0 checks passed.")


if __name__ == "__main__":
    main()
