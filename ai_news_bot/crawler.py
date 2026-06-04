"""RSS crawler for AI industry news."""

from __future__ import annotations

import hashlib
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse

import feedparser
import requests

from ai_news_bot.config import (
    CRAWL_MAX_WORKERS,
    CRAWL_REQUEST_RETRIES,
    HACKER_NEWS_FALLBACK_URLS,
    MAX_ITEMS_PER_FEED,
    MAX_TOTAL_ITEMS,
    REQUEST_TIMEOUT,
    RSS_FEEDS_ALL,
    USER_AGENT,
)


@dataclass
class NewsItem:
    title: str
    link: str
    source: str
    summary: str = ""
    published: str = ""
    dedup_key: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self.dedup_key:
            self.dedup_key = _make_dedup_key(self.title, self.link)


@dataclass
class CrawlReport:
    """Per-source crawl statistics."""

    items: List[NewsItem] = field(default_factory=list)
    per_source: Dict[str, int] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.items)


def _normalize_title(title: str) -> str:
    t = re.sub(r"\s+", " ", title.strip().lower())
    t = re.sub(r"[^\w\s\u4e00-\u9fff]", "", t)
    return t


def _canonical_link(link: str) -> str:
    """Normalize URLs for deduplication (strip tracking params)."""
    if not link:
        return ""
    try:
        parsed = urlparse(link.strip())
        if "news.google.com" in parsed.netloc and "url" in parse_qs(parsed.query):
            return parse_qs(parsed.query)["url"][0]
        qs = parse_qs(parsed.query)
        drop = ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ref")
        keep = {
            k: v
            for k, v in qs.items()
            if k.lower() not in drop and not k.lower().startswith("utm")
        }
        if keep:
            q = urlencode(keep, doseq=True)
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{q}"
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    except Exception:
        return link.strip()


def _make_dedup_key(title: str, link: str) -> str:
    canonical = _canonical_link(link)
    normalized = _normalize_title(title)
    raw = f"{normalized}|{canonical}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _extract_summary(entry: feedparser.FeedParserDict) -> str:
    if getattr(entry, "summary", None):
        text = entry.summary
    elif getattr(entry, "description", None):
        text = entry.description
    else:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()[:500]


def _extract_published(entry: feedparser.FeedParserDict) -> str:
    if getattr(entry, "published", None):
        return str(entry.published).strip()
    if getattr(entry, "updated", None):
        return str(entry.updated).strip()
    return ""


def _http_get(url: str) -> bytes:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    last_err: Optional[Exception] = None
    for attempt in range(CRAWL_REQUEST_RETRIES + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            last_err = e
            if attempt < CRAWL_REQUEST_RETRIES:
                time.sleep(1.5 * (attempt + 1))
    raise last_err  # type: ignore[misc]


def _fetch_feed(url: str, source_name: str) -> List[NewsItem]:
    try:
        content = _http_get(url)
        parsed = feedparser.parse(content)
    except Exception as e:
        print(f"[crawler] Failed to fetch {source_name}: {e}")
        return []

    items: List[NewsItem] = []
    for entry in parsed.entries[:MAX_ITEMS_PER_FEED]:
        title = (getattr(entry, "title", None) or "").strip()
        link = (getattr(entry, "link", None) or "").strip()
        if not title or not link:
            continue
        items.append(
            NewsItem(
                title=title,
                link=link,
                source=source_name,
                summary=_extract_summary(entry),
                published=_extract_published(entry),
            )
        )
    return items


def _fetch_hacker_news() -> Tuple[List[NewsItem], Optional[str]]:
    """Fetch HN with fallback URLs if the filtered feed is unavailable."""
    primary = next(f for f in RSS_FEEDS_ALL if f.name == "Hacker News")
    urls = [primary.url] + [u for u in HACKER_NEWS_FALLBACK_URLS if u != primary.url]
    last_error: Optional[str] = None
    for url in urls:
        batch = _fetch_feed(url, "Hacker News")
        if batch:
            if "q=" not in url:
                ai_kw = (
                    "ai", "llm", "gpt", "ml", "neural", "openai",
                    "anthropic", "model", "machine learning",
                )
                filtered = [n for n in batch if any(k in n.title.lower() for k in ai_kw)]
                if filtered:
                    batch = filtered[:MAX_ITEMS_PER_FEED]
            return batch, None
        last_error = f"empty from {url}"
    return [], last_error or "all HN URLs failed"


def _crawl_single_source(feed_name: str, url: str) -> Tuple[str, List[NewsItem], Optional[str]]:
    if feed_name == "Hacker News":
        items, err = _fetch_hacker_news()
        return feed_name, items, err
    items = _fetch_feed(url, feed_name)
    if not items:
        return feed_name, [], "empty feed"
    return feed_name, items, None


def crawl_all_feeds() -> List[NewsItem]:
    """Fetch news from all configured RSS feeds (parallel)."""
    report = crawl_with_report()
    return report.items


def crawl_with_report() -> CrawlReport:
    """Fetch all feeds and return items plus per-source stats."""
    report = CrawlReport()
    tasks = [(f.name, f.url) for f in RSS_FEEDS_ALL]

    print(f"[crawler] Fetching {len(tasks)} sources (workers={CRAWL_MAX_WORKERS})...")
    with ThreadPoolExecutor(max_workers=CRAWL_MAX_WORKERS) as pool:
        futures = {
            pool.submit(_crawl_single_source, name, url): name
            for name, url in tasks
        }
        for fut in as_completed(futures):
            name, items, err = fut.result()
            report.per_source[name] = len(items)
            if err:
                report.errors[name] = err
            report.items.extend(items)
            status = f"{len(items)} items" if items else f"0 items ({err})"
            print(f"[crawler]   {name}: {status}")

    if len(report.items) > MAX_TOTAL_ITEMS:
        report.items = report.items[:MAX_TOTAL_ITEMS]
        print(f"[crawler] Trimmed to MAX_TOTAL_ITEMS={MAX_TOTAL_ITEMS}")

    print(f"[crawler] Total: {report.total} items")
    return report
