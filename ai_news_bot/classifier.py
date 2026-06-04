"""Deduplication and topic classification for news items."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from ai_news_bot.config import CATEGORIES, CATEGORY_KEYWORDS
from ai_news_bot.crawler import NewsItem


@dataclass
class ClassifiedNews:
    item: NewsItem
    category: str
    rule_score: float = 0.0


def deduplicate_items(items: List[NewsItem]) -> List[NewsItem]:
    """Remove duplicate articles by dedup_key, keeping first occurrence."""
    seen: Set[str] = set()
    unique: List[NewsItem] = []
    for item in items:
        if item.dedup_key in seen:
            continue
        seen.add(item.dedup_key)
        unique.append(item)
    return unique


def _score_category(text: str, keywords: List[str]) -> float:
    text_lower = text.lower()
    score = 0.0
    for kw in keywords:
        kw_l = kw.lower()
        if kw_l in text_lower:
            score += 1.0
            if re.search(rf"\b{re.escape(kw_l)}\b", text_lower):
                score += 0.5
    return score


def classify_item(item: NewsItem) -> Tuple[str, float]:
    """Rule-based classification; returns (category, score)."""
    blob = f"{item.title} {item.summary} {item.source}"
    best_cat = "其他"
    best_score = 0.0

    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = _score_category(blob, keywords)
        if score > best_score:
            best_score = score
            best_cat = cat

    if best_score <= 0:
        return "其他", 0.0
    return best_cat, best_score


def classify_all(items: List[NewsItem]) -> Dict[str, List[NewsItem]]:
    """Deduplicate and group items by category."""
    unique = deduplicate_items(items)
    grouped: Dict[str, List[NewsItem]] = defaultdict(list)

    for item in unique:
        cat, _ = classify_item(item)
        grouped[cat].append(item)

    result: Dict[str, List[NewsItem]] = {}
    for cat in CATEGORIES:
        if cat in grouped and grouped[cat]:
            result[cat] = grouped[cat]
    return result


def classification_stats(
    raw_count: int,
    grouped: Dict[str, List[NewsItem]],
) -> Dict[str, int]:
    """Return stats dict for logging and verification."""
    unique = sum(len(v) for v in grouped.values())
    stats: Dict[str, int] = {
        "raw": raw_count,
        "unique": unique,
        "removed_duplicates": max(0, raw_count - unique),
        "categories": len(grouped),
    }
    for cat in CATEGORIES:
        stats[f"cat_{cat}"] = len(grouped.get(cat, []))
    return stats


def flatten_grouped(grouped: Dict[str, List[NewsItem]]) -> List[NewsItem]:
    """Flatten grouped dict back to a list."""
    out: List[NewsItem] = []
    for cat in CATEGORIES:
        if cat in grouped:
            out.extend(grouped[cat])
    return out
