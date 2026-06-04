"""Detect whether a news item likely points to Chinese-language content."""

from __future__ import annotations

import re
from typing import Literal
from urllib.parse import urlparse

from ai_news_bot.crawler import NewsItem

ContentLang = Literal["zh", "en"]

# RSS source names treated as Chinese media
CHINESE_SOURCE_NAMES = frozenset(
    {
        "Google News 中文",
        "36氪",
        "机器之心",
        "量子位",
    }
)

# Domains that usually serve Chinese articles
CHINESE_DOMAIN_KEYWORDS = (
    ".cn",
    "36kr.com",
    "jiqizhixin.com",
    "qbitai.com",
    "leiphone.com",
    "huxiu.com",
    "caixin.com",
    "thepaper.cn",
    "zhihu.com",
    "sina.com.cn",
    "163.com",
    "qq.com",
    "ifanr.com",
    "pingwest.com",
    "tmtpost.com",
    "geekpark.net",
)


def _cjk_ratio(text: str) -> float:
    if not text:
        return 0.0
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    return cjk / max(len(text), 1)


def detect_content_lang(item: NewsItem) -> ContentLang:
    """Guess if the linked page is primarily Chinese."""
    if item.source in CHINESE_SOURCE_NAMES:
        return "zh"

    link = (item.link or "").lower()
    host = urlparse(link).netloc.lower()
    if any(kw in host or kw in link for kw in CHINESE_DOMAIN_KEYWORDS):
        return "zh"

    if _cjk_ratio(item.title) >= 0.15 or _cjk_ratio(item.summary) >= 0.2:
        return "zh"

    return "en"
