#!/usr/bin/env python3
"""Look up your Feishu open_id for personal push (.env FEISHU_RECEIVE_ID)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from ai_news_bot.config import FEISHU_USER_EMAIL
from ai_news_bot.feishu_app import lookup_open_id_by_email


def main() -> int:
    email = FEISHU_USER_EMAIL or (sys.argv[1] if len(sys.argv) > 1 else "")
    if not email:
        print("Usage: python scripts/feishu_get_open_id.py your@company.com")
        print("Or set FEISHU_USER_EMAIL in .env")
        return 1

    try:
        open_id = lookup_open_id_by_email(email)
    except Exception as e:
        print(f"Error: {e}")
        print("\nCheck: FEISHU_APP_ID/SECRET in .env, app permissions, app published to you.")
        return 1

    print(f"Email:   {email}")
    print(f"open_id: {open_id}")
    print("\nAdd to .env:")
    print(f"FEISHU_RECEIVE_ID={open_id}")
    print("FEISHU_RECEIVE_ID_TYPE=open_id")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
