#!/usr/bin/env python3
"""
AI Industry Daily Brief — cron-friendly entry point.

Usage:
  python -m ai_news_bot.main
  python -m ai_news_bot.main --dry-run
  python -m ai_news_bot.main --no-push
  python -m ai_news_bot.main --crawl-only
  python -m ai_news_bot.main --preview-card output/card.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ai_news_bot.paths import ENV_FILE, LOGS_DIR, OUTPUT_DIR, PROJECT_ROOT

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ENV_FILE, override=True)
except ImportError:
    pass

from ai_news_bot.classifier import classify_all, classification_stats
from ai_news_bot.crawler import crawl_with_report
from ai_news_bot.feishu_card import format_source_links, save_card_json, send_feishu_card
from ai_news_bot.logging_config import setup_logging
from ai_news_bot.summarizer import DailyBrief, summarize_news

logger = logging.getLogger("ai_news_bot")


def _print_console_report(brief: DailyBrief) -> None:
    print("\n" + "=" * 60)
    print("🧭 AI行业情报与机会发现（控制台预览）")
    print("=" * 60)

    print("\n🔥 今日最重要 TOP5：")
    for i, art in enumerate(brief.top_hot or brief.sorted_articles()[:5], 1):
        print(f"  {i}. [{art.importance}/10] {art.title}")
        print(f"     摘要：{art.summary}")
        print(f"     为什么重要：{art.why_important}")
        print(f"     意味着什么：{art.industry_impact}")
        print(f"     {format_source_links(art.link, art.content_lang)}\n")

    print("📈 今日趋势观察：")
    for i, t in enumerate(brief.trends, 1):
        print(f"  趋势{i}：{t.title}")
        print(f"     {t.description}\n")

    print("🛠 今日 AI 工具推荐：")
    for i, tool in enumerate(brief.tools, 1):
        print(f"  {i}. {tool.name} — {tool.use_case}")
        print(f"     推荐理由：{tool.reason}\n")

    if brief.opportunity:
        o = brief.opportunity
        print("💰 今日机会观察：")
        print(f"  {o.name}")
        print(f"  {o.description}")
        print(f"  值得关注：{o.why_watch}")

    if brief.overview:
        print(f"\n（内部备注）{brief.overview[:300]}")


def _save_brief_json(brief: DailyBrief, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now().isoformat(),
        "overview": brief.overview,
        "top_hot": [a.to_dict() for a in brief.top_hot],
        "trends": [t.to_dict() for t in brief.trends],
        "tools": [t.to_dict() for t in brief.tools],
        "opportunity": brief.opportunity.to_dict() if brief.opportunity else None,
        "articles": [a.to_dict() for a in brief.sorted_articles()],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved brief JSON to %s", path)


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Industry Daily Brief Bot")
    parser.add_argument("--dry-run", action="store_true", help="Skip OpenAI and Feishu push")
    parser.add_argument("--no-push", action="store_true", help="Summarize but do not push to Feishu")
    parser.add_argument("--crawl-only", action="store_true", help="Only crawl and classify, then exit")
    parser.add_argument("--save-json", type=str, default="", help="Save brief JSON to path")
    parser.add_argument(
        "--preview-card",
        type=str,
        default="",
        help="Save Feishu card payload JSON (default: output/card.json when set without path)",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default="",
        help="Log file path (default: logs/brief-YYYYMMDD.log when --log-file is flag only)",
    )
    args = parser.parse_args()

    log_path: Path | None = None
    if args.log_file:
        log_path = Path(args.log_file) if args.log_file != "1" else (
            LOGS_DIR / f"brief-{datetime.now().strftime('%Y%m%d')}.log"
        )
    setup_logging(log_path)

    logger.info("=== AI Daily Brief Bot started ===")

    # Phase 1: Crawl
    report = crawl_with_report()
    if report.total == 0:
        logger.error("No news fetched from any source")
        if report.errors:
            for src, err in report.errors.items():
                logger.error("  %s: %s", src, err)
        print(
            "[main] FATAL: crawl returned 0 items. "
            "On GitHub Actions, Chinese RSS/Google News are often blocked — "
            "ensure secrets FEISHU_WEBHOOK_URL / OPENAI_API_KEY are set, then re-run."
        )
        print("[main] EXIT 1: RSS crawl returned 0 items")
        return 1

    # Phase 2: Classify
    grouped = classify_all(report.items)
    stats = classification_stats(report.total, grouped)
    logger.info(
        "Classified: %d unique (removed %d dupes) in %d categories",
        stats["unique"],
        stats["removed_duplicates"],
        stats["categories"],
    )
    for cat in grouped:
        logger.info("  [%s] %d items", cat, len(grouped[cat]))

    if args.crawl_only:
        print(json.dumps({"per_source": report.per_source, "stats": stats}, ensure_ascii=False, indent=2))
        return 0

    # Phase 3: Summarize
    try:
        brief = summarize_news(grouped, dry_run=args.dry_run)
    except Exception as e:
        if args.dry_run:
            raise
        logger.warning("OpenAI failed (%s), falling back to dry-run summary", e)
        brief = summarize_news(grouped, dry_run=True)
        brief.overview = f"【注意】AI 总结暂不可用（{e}），以下为 RSS 预览。\n\n" + brief.overview
    logger.info(
        "Brief: top=%d, internal=%d, trends=%d, tools=%d",
        len(brief.top_hot),
        len(brief.articles),
        len(brief.trends),
        len(brief.tools),
    )
    if not os.getenv("GITHUB_ACTIONS"):
        _print_console_report(brief)
    else:
        logger.info(
            "Brief ready (CI): top=%s, trends=%s, tools=%s",
            len(brief.top_hot),
            len(brief.trends),
            len(brief.tools),
        )

    # Phase 5: Persist outputs
    json_path = Path(args.save_json) if args.save_json else None
    if not json_path and not args.dry_run:
        json_path = OUTPUT_DIR / f"brief-{datetime.now().strftime('%Y%m%d')}.json"
    if json_path:
        _save_brief_json(brief, json_path)

    if args.preview_card:
        card_path = (
            Path(args.preview_card)
            if args.preview_card not in ("1", "true")
            else OUTPUT_DIR / "card.json"
        )
        save_card_json(brief, card_path)
        logger.info("Saved Feishu card preview to %s", card_path)

    # Phase 4: Feishu push
    if args.no_push or args.dry_run:
        send_feishu_card(brief, dry_run=True)
    else:
        if not send_feishu_card(brief):
            logger.error("Feishu push failed — check FEISHU_WEBHOOK_URL secret")
            print("[main] EXIT 2: Feishu webhook send failed (see [feishu] lines above)")
            return 2
        _mark_sent_today()

    logger.info("Done.")
    return 0


def _mark_sent_today() -> None:
    """Record successful push so login catch-up does not duplicate."""
    try:
        day = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d")
    except Exception:
        day = datetime.now().strftime("%Y%m%d")
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = LOGS_DIR / f"sent-{day}.stamp"
    stamp.write_text(datetime.now().isoformat(), encoding="utf-8")
    logger.info("Marked daily send: %s", stamp.name)


if __name__ == "__main__":
    raise SystemExit(main())
