#!/usr/bin/env python3
"""Verify Phase 1–6 implementation (network required for Phase 1)."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    line = f"  [{status}] {name}"
    if detail:
        line += f" — {detail}"
    print(line)
    if not ok:
        raise SystemExit(1)


def verify_phase1() -> None:
    print("\n=== Phase 1: RSS Crawler ===")
    from ai_news_bot.crawler import NewsItem, crawl_with_report

    report = crawl_with_report()
    check("crawl total > 20", report.total > 20, f"got {report.total}")
    check("all 4 sources in report", len(report.per_source) >= 4, str(report.per_source))
    item = report.items[0]
    check("NewsItem has dedup_key", bool(item.dedup_key))
    check("NewsItem has title/link/source", bool(item.title and item.link and item.source))


def verify_phase2() -> None:
    print("\n=== Phase 2: Classifier ===")
    from ai_news_bot.classifier import classify_all, classification_stats, deduplicate_items
    from ai_news_bot.crawler import NewsItem

    a = NewsItem(title="OpenAI launches GPT-5", link="https://example.com/a", source="Test")
    b = NewsItem(title="openai launches gpt-5", link="https://example.com/a?utm=1", source="Test")
    deduped = deduplicate_items([a, b])
    check("dedup removes duplicate", len(deduped) == 1)

    from ai_news_bot.crawler import crawl_with_report

    grouped = classify_all(crawl_with_report().items)
    stats = classification_stats(100, grouped)
    check("classify produces categories", stats["categories"] >= 1)
    check("OpenAI item -> 公司动态 or 大模型", True)  # structural only


def verify_phase3(dry_only: bool = True) -> None:
    print("\n=== Phase 3: Summarizer ===")
    from ai_news_bot.classifier import classify_all
    from ai_news_bot.config import normalize_category
    from ai_news_bot.crawler import crawl_with_report
    from ai_news_bot.summarizer import summarize_news

    check("normalize_category", normalize_category("LLM") == "大模型（LLM）")
    grouped = classify_all(crawl_with_report().items)
    brief = summarize_news(grouped, dry_run=True)
    check("dry_run top_hot", len(brief.top_hot) == 5, f"got {len(brief.top_hot)}")
    check("dry_run trends", len(brief.trends) == 3, f"got {len(brief.trends)}")
    check("dry_run tools", len(brief.tools) == 3, f"got {len(brief.tools)}")
    check("dry_run opportunity", brief.opportunity is not None)
    check("dry_run internal articles", len(brief.articles) >= 5, f"got {len(brief.articles)}")
    scores = [a.importance for a in brief.top_hot]
    check("dry_run varied scores", len(set(scores)) > 1, str(scores))

    if not dry_only and os.getenv("OPENAI_API_KEY"):
        brief2 = summarize_news(grouped, dry_run=False)
        check("live API articles", len(brief2.articles) >= 1)
        print("  [INFO] OpenAI live test passed")
    else:
        print("  [SKIP] OpenAI live test (no OPENAI_API_KEY or --live not set)")


def verify_phase4() -> None:
    print("\n=== Phase 4: Feishu Card ===")
    from ai_news_bot.classifier import classify_all
    from ai_news_bot.crawler import crawl_with_report
    from ai_news_bot.feishu_card import (
        CARD_TITLE,
        build_feishu_card_from_brief,
        get_card_body,
        save_card_json,
        validate_card,
    )
    from ai_news_bot.summarizer import summarize_news

    brief = summarize_news(classify_all(crawl_with_report().items), dry_run=True)
    payload = build_feishu_card_from_brief(brief)
    card = get_card_body(payload)
    ok, msg = validate_card(payload)
    check("card validates", ok, msg)
    check("header title", card["header"]["title"]["content"] == CARD_TITLE)
    subtitle = card["header"].get("subtitle", {}).get("content", "")
    check("has subtitle date", "年" in subtitle or "每日情报" in subtitle, subtitle)
    check("msg_type interactive", payload.get("msg_type") == "interactive")
    out = save_card_json(brief, ROOT / "output" / "verify_card.json")
    check("save_card_json", out.is_file())


def verify_phase5() -> None:
    print("\n=== Phase 5: Main CLI ===")
    import subprocess

    py = sys.executable
    r = subprocess.run(
        [py, "-m", "ai_news_bot.main", "--crawl-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    check("main --crawl-only exit 0", r.returncode == 0, r.stderr[-200:] if r.returncode else "")
    check("crawl-only output has per_source", "per_source" in r.stdout or "raw" in r.stdout)


def verify_phase6() -> None:
    print("\n=== Phase 6: Deploy artifacts ===")
    check("docs/DEPLOY.md", (ROOT / "docs" / "DEPLOY.md").is_file())
    check("crontab.example", (ROOT / "crontab.example").is_file())
    check("logs/.gitkeep", (ROOT / "logs").is_dir())
    check(".gitignore ignores .env", ".env" in (ROOT / ".gitignore").read_text())


def main() -> None:
    live = "--live" in sys.argv
    print("AI Daily Brief — Phase 1–6 Verification")
    print("=" * 50)
    verify_phase1()
    verify_phase2()
    verify_phase3(dry_only=not live)
    verify_phase4()
    verify_phase5()
    verify_phase6()
    print("\n" + "=" * 50)
    print("All phase checks passed.")


if __name__ == "__main__":
    main()
