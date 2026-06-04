"""Configuration for AI Daily Brief bot."""

import os
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class RSSSource:
    name: str
    url: str


# RSS：中国视角 + 全球视角（均衡采集）
RSS_FEEDS_CHINA: List[RSSSource] = [
    RSSSource(
        name="Google News 中文",
        url="https://news.google.com/rss/search?q=人工智能+OR+大模型+OR+AI+OR+OpenAI&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
    ),
    RSSSource(
        name="36氪",
        url="https://36kr.com/feed",
    ),
    RSSSource(
        name="机器之心",
        url="https://www.jiqizhixin.com/rss",
    ),
    RSSSource(
        name="量子位",
        url="https://www.qbitai.com/feed",
    ),
]

RSS_FEEDS_GLOBAL: List[RSSSource] = [
    RSSSource(
        name="Google News 全球",
        url="https://news.google.com/rss/search?q=artificial+intelligence+OR+AI+OR+LLM&hl=en-US&gl=US&ceid=US:en",
    ),
    RSSSource(
        name="TechCrunch AI",
        url="https://techcrunch.com/category/artificial-intelligence/feed/",
    ),
    RSSSource(
        name="Hacker News",
        url="https://hnrss.org/newest?q=AI+OR+LLM+OR+GPT+OR+machine+learning",
    ),
    RSSSource(
        name="arXiv AI",
        url="http://export.arxiv.org/rss/cs.AI",
    ),
]

RSS_FEEDS_ALL: List[RSSSource] = RSS_FEEDS_CHINA + RSS_FEEDS_GLOBAL

# GitHub Actions 机房常无法访问国内源 / Google News，仅用海外稳定源
RSS_FEEDS_CI: List[RSSSource] = RSS_FEEDS_GLOBAL


def get_rss_feeds() -> List[RSSSource]:
    """Pick feed list: full list locally, CI-safe list on GitHub Actions."""
    if os.getenv("GITHUB_ACTIONS", "").lower() == "true":
        return list(RSS_FEEDS_CI)
    if os.getenv("RSS_MODE", "").lower() == "ci":
        return list(RSS_FEEDS_CI)
    return list(RSS_FEEDS_ALL)

# Fallback URLs when Hacker News primary feed fails
HACKER_NEWS_FALLBACK_URLS: List[str] = [
    "https://hnrss.org/newest",
    "https://hnrss.org/frontpage",
]

# Topic categories (display order)
CATEGORIES: List[str] = [
    "大模型（LLM）",
    "公司动态",
    "AI产品发布",
    "AI论文 / 技术突破",
    "AI投资 / 融资",
    "其他",
]

# Keyword rules for rule-based pre-classification (refined by LLM)
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "大模型（LLM）": [
        "llm", "gpt", "claude", "gemini", "large language", "大模型", "语言模型",
        "transformer", "fine-tun", "prompt", "rag", "embedding",
    ],
    "公司动态": [
        "openai", "google", "meta", "anthropic", "microsoft", "nvidia",
        "deepmind", "xai", "mistral", "cohere", "ceo", "layoff", "partnership",
    ],
    "AI产品发布": [
        "launch", "release", "unveil", "announce", "beta", "api", "app",
        "copilot", "chatbot", "agent", "产品", "发布",
    ],
    "AI论文 / 技术突破": [
        "arxiv", "paper", "research", "breakthrough", "benchmark", "dataset",
        "neural", "diffusion", "multimodal", "论文", "技术",
    ],
    "AI投资 / 融资": [
        "funding", "raise", "investment", "valuation", "series", "venture",
        "acquisition", "ipo", "million", "billion", "融资", "投资",
    ],
}

# LLM — any OpenAI-compatible API (OpenAI / DeepSeek / Moonshot / Ollama / …)
# Set LLM_PROVIDER to a preset name, or leave empty and configure BASE_URL + MODEL yourself.
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "").strip().lower()
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "").rstrip("/")
OPENAI_MAX_RETRIES: int = int(os.getenv("OPENAI_MAX_RETRIES", "2"))

# Preset providers (see docs/MODEL_PROVIDERS.md)
LLM_PROVIDER_PRESETS: Dict[str, Dict[str, str]] = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "api_key_placeholder": "sk-...",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "api_key_placeholder": "sk-... (platform.deepseek.com)",
    },
    "moonshot": {
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
        "api_key_placeholder": "sk-... (platform.moonshot.cn)",
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
        "api_key_placeholder": "... (open.bigmodel.cn)",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "api_key_placeholder": "gsk_... (console.groq.com)",
    },
    "ollama": {
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "qwen2.5:7b",
        "api_key_placeholder": "ollama (任意非空字符串)",
    },
}


def resolve_llm_settings() -> Dict[str, str]:
    """
    Resolve API key, base URL, and model.
    LLM_PROVIDER preset applies when BASE_URL / MODEL are not customized.
    Reads os.environ at call time so .env (override=True) always wins.
    """
    api_key = (
        os.getenv("OPENAI_API_KEY", "")
        or os.getenv("DEEPSEEK_API_KEY", "")
        or os.getenv("Deepseek_API_KEY", "")
    ).strip().strip("\ufeff")
    base_url = os.getenv("OPENAI_BASE_URL", "").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()

    if provider in LLM_PROVIDER_PRESETS:
        preset = LLM_PROVIDER_PRESETS[provider]
        if not base_url:
            base_url = preset["base_url"]
        # If user only kept default OpenAI model name, swap to preset model
        if model == "gpt-4o-mini" and provider != "openai":
            model = preset["model"]
        if provider == "ollama" and not api_key:
            api_key = "ollama"

    if not api_key and provider != "ollama":
        hint = ""
        if provider in LLM_PROVIDER_PRESETS:
            hint = f" (expected: {LLM_PROVIDER_PRESETS[provider]['api_key_placeholder']})"
        raise ValueError(f"OPENAI_API_KEY is not set{hint}")

    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "provider": provider or "custom",
    }

# Feishu push: "app" = personal DM via enterprise app; "webhook" = group custom bot
FEISHU_PUSH_MODE: str = os.getenv("FEISHU_PUSH_MODE", "app").strip().lower()
FEISHU_WEBHOOK_URL: str = os.getenv("FEISHU_WEBHOOK_URL", "")

# Personal push (Open Platform app) — https://open.feishu.cn/app
FEISHU_APP_ID: str = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET: str = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_RECEIVE_ID: str = os.getenv("FEISHU_RECEIVE_ID", "")  # your open_id (recommended)
FEISHU_RECEIVE_ID_TYPE: str = os.getenv("FEISHU_RECEIVE_ID_TYPE", "open_id")
FEISHU_USER_EMAIL: str = os.getenv("FEISHU_USER_EMAIL", "")  # or lookup open_id by email

# HTTP / crawler
USER_AGENT: str = "AI-Daily-Brief-Bot/1.0 (+https://github.com/ai-daily-brief)"
MAX_ITEMS_PER_FEED: int = int(os.getenv("MAX_ITEMS_PER_FEED", "15"))
MAX_TOTAL_ITEMS: int = int(os.getenv("MAX_TOTAL_ITEMS", "75"))
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
CRAWL_MAX_WORKERS: int = int(os.getenv("CRAWL_MAX_WORKERS", "4"))
CRAWL_REQUEST_RETRIES: int = int(os.getenv("CRAWL_REQUEST_RETRIES", "2"))

# Intelligence brief limits (user-facing)
TOP_HOT_COUNT: int = int(os.getenv("TOP_HOT_COUNT", "5"))
TREND_COUNT: int = 3
TOOL_RECOMMENDATION_COUNT: int = 3
OPPORTUNITY_COUNT: int = 1

# Internal archive: categorized articles for JSON/debug only (not shown on Feishu)
INTERNAL_ARTICLE_COUNT: int = int(os.getenv("INTERNAL_ARTICLE_COUNT", "12"))

# Legacy env vars (ignored for display; kept so old .env does not break)
BRIEF_GLOBAL_COUNT: int = int(os.getenv("BRIEF_GLOBAL_COUNT", "7"))
BRIEF_CHINA_COUNT: int = int(os.getenv("BRIEF_CHINA_COUNT", "3"))


def normalize_category(category: str) -> str:
    """Map LLM/rule output to a valid CATEGORIES label."""
    if not category:
        return "其他"
    cat = category.strip()
    if cat in CATEGORIES:
        return cat
    aliases = {
        "llm": "大模型（LLM）",
        "大模型": "大模型（LLM）",
        "论文": "AI论文 / 技术突破",
        "技术突破": "AI论文 / 技术突破",
        "融资": "AI投资 / 融资",
        "投资": "AI投资 / 融资",
        "产品": "AI产品发布",
        "产品发布": "AI产品发布",
    }
    lower = cat.lower()
    for key, val in aliases.items():
        if key in lower or key in cat:
            return val
    return "其他"
