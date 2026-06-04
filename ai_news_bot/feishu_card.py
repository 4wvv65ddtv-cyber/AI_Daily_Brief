"""Build and send Feishu intelligence brief cards via webhook."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import requests

from ai_news_bot.config import REQUEST_TIMEOUT
from ai_news_bot.summarizer import DailyBrief, SummarizedArticle

CARD_TITLE = "🧭 AI行业情报与机会发现"
CARD_SUBTITLE_TAG = "每日情报"


def format_date_str() -> str:
    try:
        return datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y年%m月%d日")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


def _escape_md(text: str) -> str:
    return text.replace("|", "\\|")


def format_headline(title_zh: str) -> str:
    return f"**{_escape_md((title_zh or '').strip())}**"


def format_source_links(link: str, content_lang: str = "zh") -> str:
    url = (link or "").strip()
    if not url:
        return "_（无链接）_"
    if content_lang == "zh":
        return f"[原文]({url})"
    return f"[原文（英文）]({url})"


def _md_div(content: str) -> Dict[str, Any]:
    return {"tag": "div", "text": {"tag": "lark_md", "content": content}}


def _hr() -> Dict[str, Any]:
    return {"tag": "hr"}


def _clamp(text: str, max_len: int) -> str:
    t = (text or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _render_top5(top_hot: List[SummarizedArticle]) -> List[Dict[str, Any]]:
    elements: List[Dict[str, Any]] = [
        _md_div("🔥 **今日最重要 TOP5**"),
    ]
    if not top_hot:
        elements.append(_md_div("_暂无要闻_"))
        return elements

    for i, art in enumerate(top_hot[:5], 1):
        lang = art.content_lang
        block = (
            f"**{i}.** {format_headline(art.title)}  \n"
            f"⭐ **{art.importance}/10**  \n"
            f"📌 {_clamp(art.summary, 180)}  \n"
            f"💡 **为什么重要：** {_clamp(art.why_important, 100)}  \n"
            f"🔮 **意味着什么：** {_clamp(art.industry_impact, 100)}  \n"
            f"{format_source_links(art.link, lang)}"
        )
        elements.append(_md_div(block))
    return elements


def _render_trends(brief: DailyBrief) -> List[Dict[str, Any]]:
    elements: List[Dict[str, Any]] = [_md_div("📈 **今日趋势观察**")]
    if not brief.trends:
        elements.append(_md_div("_暂无趋势_"))
        return elements
    for i, t in enumerate(brief.trends[:3], 1):
        elements.append(
            _md_div(
                f"**趋势{i}：{_escape_md(t.title)}**  \n"
                f"说明：{_clamp(t.description, 100)}"
            )
        )
    return elements


def _render_tools(brief: DailyBrief) -> List[Dict[str, Any]]:
    elements: List[Dict[str, Any]] = [_md_div("🛠 **今日 AI 工具推荐**")]
    if not brief.tools:
        elements.append(_md_div("_暂无推荐_"))
        return elements
    for i, tool in enumerate(brief.tools[:3], 1):
        elements.append(
            _md_div(
                f"**{i}. {_escape_md(tool.name)}**  \n"
                f"适用场景：{_clamp(tool.use_case, 60)}  \n"
                f"推荐理由：{_clamp(tool.reason, 100)}"
            )
        )
    return elements


def _render_opportunity(brief: DailyBrief) -> List[Dict[str, Any]]:
    elements: List[Dict[str, Any]] = [_md_div("💰 **今日机会观察**")]
    opp = brief.opportunity
    if not opp:
        elements.append(_md_div("_暂无机会洞察_"))
        return elements
    elements.append(
        _md_div(
            f"**{_escape_md(opp.name)}**  \n"
            f"{_clamp(opp.description, 100)}  \n"
            f"**值得关注：** {_clamp(opp.why_watch, 80)}"
        )
    )
    return elements


def build_feishu_card_from_brief(
    brief: DailyBrief,
    date: Optional[str] = None,
) -> Dict[str, Any]:
    """Four modules only: TOP5, trends, tools, opportunity."""
    elements: List[Dict[str, Any]] = []
    elements.extend(_render_top5(brief.top_hot or brief.sorted_articles()[:5]))
    elements.append(_hr())
    elements.extend(_render_trends(brief))
    elements.append(_hr())
    elements.extend(_render_tools(brief))
    elements.append(_hr())
    elements.extend(_render_opportunity(brief))

    date_str = date or format_date_str()
    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": CARD_TITLE},
                "subtitle": {
                    "tag": "plain_text",
                    "content": f"{CARD_SUBTITLE_TAG} · {date_str}",
                },
                "template": "blue",
            },
            "elements": elements,
        },
    }


def get_card_body(payload: Dict[str, Any]) -> Dict[str, Any]:
    if "card" in payload:
        return payload["card"]
    return payload


def validate_card(payload: Dict[str, Any]) -> Tuple[bool, str]:
    card = get_card_body(payload)
    title = card.get("header", {}).get("title", {}).get("content", "")
    if title != CARD_TITLE:
        return False, f"unexpected title: {title!r}"

    elements = card.get("elements", [])
    if not elements:
        return False, "empty elements"

    texts = [
        e.get("text", {}).get("content", "")
        for e in elements
        if e.get("tag") == "div" and isinstance(e.get("text"), dict)
    ]
    required = ("TOP5", "趋势观察", "工具推荐", "机会观察")
    for marker in required:
        if not any(marker in t for t in texts):
            return False, f"missing section: {marker}"
    if not any(e.get("tag") == "hr" for e in elements):
        return False, "missing hr separators"
    if any("分类摘要" in t or "大模型（LLM）" in t for t in texts):
        return False, "legacy category section still present"

    return True, "ok"


def save_card_json(brief: DailyBrief, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_feishu_card_from_brief(brief)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _send_via_webhook(payload: Dict[str, Any], url: str) -> bool:
    print("[feishu] Sending intelligence card to webhook...")
    resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text}

    if resp.status_code == 200:
        code = body.get("code", body.get("StatusCode"))
        status_msg = str(body.get("msg", body.get("StatusMessage", ""))).lower()
        if code == 0 or status_msg == "success":
            print("[feishu] Webhook sent successfully")
            return True

    print(f"[feishu] Webhook send failed: {resp.status_code} {body}")
    if resp.status_code == 404:
        print("[feishu] Hint: Webhook URL invalid or bot removed — reset in Feishu group")
    return False


def _feishu_push_mode() -> str:
    return os.getenv("FEISHU_PUSH_MODE", "webhook").strip().lower()


def _feishu_webhook_url() -> str:
    return os.getenv("FEISHU_WEBHOOK_URL", "").strip().strip('"').strip("'")


def _configured_for_push() -> bool:
    if _feishu_push_mode() == "webhook":
        return bool(_feishu_webhook_url())
    return bool(
        os.getenv("FEISHU_APP_ID")
        and os.getenv("FEISHU_APP_SECRET")
        and (os.getenv("FEISHU_RECEIVE_ID") or os.getenv("FEISHU_USER_EMAIL"))
    )


def send_feishu_card(
    brief: DailyBrief,
    *,
    webhook_url: Optional[str] = None,
    dry_run: bool = False,
) -> bool:
    payload = build_feishu_card_from_brief(brief)
    ok, msg = validate_card(payload)
    if not ok:
        print(f"[feishu] Card validation warning: {msg}")

    if dry_run:
        print(f"[feishu] dry_run — skipping send (mode={_feishu_push_mode()})")
        print(json.dumps(payload, ensure_ascii=False, indent=2)[:5000])
        return False

    if not _configured_for_push():
        print("[feishu] Feishu not configured — see docs/FEISHU_PERSONAL.md")
        print(json.dumps(payload, ensure_ascii=False, indent=2)[:5000])
        return False

    if _feishu_push_mode() == "webhook":
        url = webhook_url or _feishu_webhook_url()
        if not url:
            print("[feishu] FEISHU_WEBHOOK_URL not set")
            return False
        return _send_via_webhook(payload, url)

    from ai_news_bot.feishu_app import send_card_to_user

    return send_card_to_user(get_card_body(payload))
