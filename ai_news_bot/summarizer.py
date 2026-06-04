"""LLM-powered intelligence brief: insights, trends, tools, and opportunities."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from openai import OpenAI

from ai_news_bot.config import (
    CATEGORIES,
    INTERNAL_ARTICLE_COUNT,
    OPENAI_MAX_RETRIES,
    OPPORTUNITY_COUNT,
    TOP_HOT_COUNT,
    TREND_COUNT,
    TOOL_RECOMMENDATION_COUNT,
    normalize_category,
    resolve_llm_settings,
)
from ai_news_bot.crawler import NewsItem
from ai_news_bot.locale_utils import detect_content_lang


@dataclass
class SummarizedArticle:
    title: str
    link: str
    source: str
    category: str
    summary: str
    importance: int
    original_title: str = ""
    content_lang: str = "zh"
    why_important: str = ""
    industry_impact: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "link": self.link,
            "source": self.source,
            "category": self.category,
            "summary": self.summary,
            "importance": self.importance,
            "original_title": self.original_title or self.title,
            "content_lang": self.content_lang,
            "why_important": self.why_important,
            "industry_impact": self.industry_impact,
        }


@dataclass
class TrendObservation:
    title: str
    description: str

    def to_dict(self) -> Dict[str, str]:
        return {"title": self.title, "description": self.description}


@dataclass
class ToolRecommendation:
    name: str
    use_case: str
    reason: str

    def to_dict(self) -> Dict[str, str]:
        return {"name": self.name, "use_case": self.use_case, "reason": self.reason}


@dataclass
class OpportunityInsight:
    name: str
    description: str
    why_watch: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
            "why_watch": self.why_watch,
        }


@dataclass
class DailyBrief:
    """User-facing intelligence + internal categorized archive."""
    overview: str = ""
    articles: List[SummarizedArticle] = field(default_factory=list)
    top_hot: List[SummarizedArticle] = field(default_factory=list)
    trends: List[TrendObservation] = field(default_factory=list)
    tools: List[ToolRecommendation] = field(default_factory=list)
    opportunity: Optional[OpportunityInsight] = None

    def sorted_articles(self) -> List[SummarizedArticle]:
        return sorted(self.articles, key=lambda a: a.importance, reverse=True)


def _heuristic_importance(title: str, summary: str, source: str) -> int:
    blob = f"{title} {summary} {source}".lower()
    score = 3.0
    high_signal = (
        "openai", "anthropic", "google", "nvidia", "gpt", "claude",
        "funding", "billion", "launch", "breakthrough", "benchmark", "agent",
    )
    for kw in high_signal:
        if kw in blob:
            score += 1.2
    if source in ("Google News 中文", "36氪", "机器之心", "量子位"):
        score += 1.0
    if source in ("Google News 全球", "TechCrunch AI", "Hacker News"):
        score += 1.0
    return max(3, min(9, int(round(score))))


def _llm_config() -> Dict[str, str]:
    return resolve_llm_settings()


def _build_client() -> OpenAI:
    cfg = _llm_config()
    kwargs: Dict[str, Any] = {"api_key": cfg["api_key"]}
    if cfg["base_url"]:
        kwargs["base_url"] = cfg["base_url"]
    return OpenAI(**kwargs)


def _prepare_news_payload(
    grouped: Dict[str, List[NewsItem]], max_per_category: int = 8
) -> List[Dict[str, str]]:
    payload: List[Dict[str, str]] = []
    for category, items in grouped.items():
        for item in items[:max_per_category]:
            lang = detect_content_lang(item)
            payload.append(
                {
                    "title": item.title,
                    "link": item.link,
                    "source": item.source,
                    "category_hint": category,
                    "snippet": (item.summary or "")[:300],
                    "content_lang": lang,
                }
            )
    return payload


def _call_openai(
    client: OpenAI, system_prompt: str, user_content: str, model: str
) -> Dict[str, Any]:
    last_err: Exception | None = None
    for attempt in range(OPENAI_MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"今日新闻素材：\n{user_content}"},
                ],
                temperature=0.45,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
            return json.loads(raw)
        except Exception as e:
            last_err = e
            print(f"[summarizer] API attempt {attempt + 1} failed: {e}")
            if attempt < OPENAI_MAX_RETRIES:
                time.sleep(2.0 * (attempt + 1))
    raise last_err  # type: ignore[misc]


def _clamp_importance(value: Any) -> int:
    try:
        importance = int(value)
    except (TypeError, ValueError):
        importance = 5
    return max(1, min(10, importance))


def _article_from_raw(a: Dict[str, Any], *, with_insights: bool = False) -> SummarizedArticle:
    orig = (a.get("original_title") or a.get("title") or "").strip()
    title_zh = (a.get("title") or orig).strip()
    link = a.get("link", "")
    lang = a.get("content_lang") or detect_content_lang(
        NewsItem(title=orig, link=link, source=a.get("source", ""))
    )
    if lang not in ("zh", "en"):
        lang = detect_content_lang(
            NewsItem(title=orig, link=link, source=a.get("source", ""))
        )
    return SummarizedArticle(
        title=title_zh,
        link=link,
        source=a.get("source", ""),
        category=normalize_category(a.get("category", "其他")),
        summary=(a.get("summary") or "").strip(),
        importance=_clamp_importance(a.get("importance", 5)),
        original_title=orig,
        content_lang=lang,
        why_important=(a.get("why_important") or "").strip() if with_insights else "",
        industry_impact=(a.get("industry_impact") or a.get("what_it_means") or "").strip()
        if with_insights
        else "",
    )


def _parse_internal_articles(data: Dict[str, Any]) -> List[SummarizedArticle]:
    articles: List[SummarizedArticle] = []
    for a in data.get("internal_articles", data.get("articles", [])):
        articles.append(_article_from_raw(a, with_insights=False))
    articles.sort(key=lambda x: x.importance, reverse=True)
    return articles[:INTERNAL_ARTICLE_COUNT]


def _parse_top_events(data: Dict[str, Any]) -> List[SummarizedArticle]:
    events: List[SummarizedArticle] = []
    for a in data.get("top_events", data.get("top_hot", [])):
        events.append(_article_from_raw(a, with_insights=True))
    events.sort(key=lambda x: x.importance, reverse=True)
    return events[:TOP_HOT_COUNT]


def _parse_trends(data: Dict[str, Any]) -> List[TrendObservation]:
    trends: List[TrendObservation] = []
    for t in data.get("trends", []):
        title = (t.get("title") or "").strip()
        desc = (t.get("description") or t.get("explanation") or "").strip()
        if title and desc:
            trends.append(TrendObservation(title=title, description=desc[:120]))
    return trends[:TREND_COUNT]


def _parse_tools(data: Dict[str, Any]) -> List[ToolRecommendation]:
    tools: List[ToolRecommendation] = []
    for t in data.get("tool_recommendations", data.get("tools", [])):
        name = (t.get("name") or t.get("tool_name") or "").strip()
        use_case = (t.get("use_case") or t.get("scenario") or "").strip()
        reason = (t.get("reason") or t.get("recommendation_reason") or "").strip()
        if name:
            tools.append(
                ToolRecommendation(
                    name=name,
                    use_case=use_case[:80],
                    reason=reason[:120],
                )
            )
    return tools[:TOOL_RECOMMENDATION_COUNT]


def _parse_opportunity(data: Dict[str, Any]) -> Optional[OpportunityInsight]:
    raw = data.get("opportunity") or data.get("opportunity_insight")
    if not raw or not isinstance(raw, dict):
        return None
    name = (raw.get("name") or raw.get("title") or "").strip()
    desc = (raw.get("description") or "").strip()
    why = (raw.get("why_watch") or raw.get("why_important") or "").strip()
    if not name:
        return None
    return OpportunityInsight(
        name=name,
        description=desc[:120],
        why_watch=why[:80],
    )


def _article_from_news_entry(n: Dict[str, str]) -> SummarizedArticle:
    lang = n.get("content_lang", "zh")
    title = n["title"]
    snippet = (n.get("snippet") or "")[:120]
    return SummarizedArticle(
        title=title[:80],
        link=n["link"],
        source=n["source"],
        category=normalize_category(n.get("category_hint", "其他")),
        summary=snippet or "（待补充摘要）",
        importance=_heuristic_importance(title, snippet, n["source"]),
        original_title=title,
        content_lang=lang if lang in ("zh", "en") else "zh",
        why_important="（试运行）结合今日行业动态，该事件可能影响竞争格局或产品路线。",
        industry_impact="（试运行）值得持续跟踪后续产品落地与生态反应。",
    )


def _pick_top_from_pool(pool: List[SummarizedArticle], n: int) -> List[SummarizedArticle]:
    seen: set[str] = set()
    picked: List[SummarizedArticle] = []
    for art in sorted(pool, key=lambda a: a.importance, reverse=True):
        if art.link in seen:
            continue
        picked.append(art)
        seen.add(art.link)
        if len(picked) >= n:
            break
    return picked


def _dry_run_brief(pool: List[SummarizedArticle]) -> DailyBrief:
    top = _pick_top_from_pool(pool, TOP_HOT_COUNT)
    internal = _pick_top_from_pool(pool, INTERNAL_ARTICLE_COUNT)
    trends = [
        TrendObservation(
            title="Agent 商业化加速",
            description="（试运行）越来越多公司将 AI 嵌入真实工作流，工具型产品开始向生产环节渗透。",
        ),
        TrendObservation(
            title="大模型成本与开源博弈",
            description="（试运行）推理降价与开源模型迭代并行，中小团队更易获得可部署能力。",
        ),
        TrendObservation(
            title="监管与合规关注度上升",
            description="（试运行）各国对数据、版权与安全的规则更细，产品出海需前置合规设计。",
        ),
    ]
    tools = [
        ToolRecommendation(
            name="Cursor",
            use_case="研发提效与代码审查",
            reason="（试运行）与今日 AI 编程/Agent 相关报道呼应，适合快速验证工作流改造。",
        ),
        ToolRecommendation(
            name="LangSmith",
            use_case="LLM 应用观测与调试",
            reason="（试运行）Agent 上线后需要链路追踪，便于对照今日产品发布类新闻。",
        ),
        ToolRecommendation(
            name="Perplexity",
            use_case="行业情报速览",
            reason="（试运行）适合在大量新闻中快速交叉验证趋势与机会假设。",
        ),
    ]
    opportunity = OpportunityInsight(
        name="垂直行业 AI 工作流套件",
        description="（试运行）将通用大模型包装为某行业可交付的 SOP+工具链，降低落地摩擦。",
        why_watch="与今日企业数字化、Agent 落地新闻方向一致，适合小团队切入。",
    )
    return DailyBrief(
        overview="【试运行】未调用 LLM，以下为 RSS 启发式预览。",
        articles=internal,
        top_hot=top,
        trends=trends,
        tools=tools,
        opportunity=opportunity,
    )


def _system_prompt() -> str:
    categories_str = "、".join(CATEGORIES)
    return f"""你是一位资深 AI 行业分析师与情报顾问，不是新闻编辑。
你的任务是从新闻素材中提取洞察（Insight），帮助读者在 3 分钟内理解：发生了什么、为什么重要、趋势、可尝试工具、商业机会。

请输出严格 JSON（不要 markdown 代码块），结构如下：
{{
  "top_events": [
    {{
      "original_title": "RSS 原始标题",
      "title": "中文标题（英文需翻译）",
      "link": "必须使用输入中的原始 link",
      "source": "来源",
      "content_lang": "zh 或 en",
      "importance": 1-10 整数,
      "summary": "2-3 句话新闻摘要，客观高密度",
      "why_important": "1-2 句话：为什么这件事值得行业关注（洞察，勿复述标题）",
      "industry_impact": "1-2 句话：对行业意味着什么、可能影响谁（洞察）"
    }}
  ],
  "trends": [
    {{ "title": "趋势标题（8字内为佳）", "description": "50-100字说明，基于多条新闻归纳" }}
  ],
  "tool_recommendations": [
    {{
      "name": "工具名称",
      "use_case": "适用场景（一句话）",
      "reason": "推荐理由，必须引用或呼应今日新闻中的具体主题，禁止泛泛而谈"
    }}
  ],
  "opportunity": {{
    "name": "机会名称",
    "description": "机会描述（合计不超过100字）",
    "why_watch": "为什么值得关注（一句话）"
  }},
  "internal_articles": [
    {{
      "original_title": "...",
      "title": "...",
      "link": "...",
      "source": "...",
      "category": "必须是以下之一：{categories_str}",
      "content_lang": "zh 或 en",
      "summary": "一句话",
      "importance": 1-10
    }}
  ]
}}

硬性要求：
- top_events **恰好 {TOP_HOT_COUNT} 条**，按 importance 降序，全球/中文素材均需覆盖（不必固定比例，但避免单一语言）
- trends **恰好 {TREND_COUNT} 条**，description 每条 50-100 字
- tool_recommendations **恰好 {TOOL_RECOMMENDATION_COUNT} 个**，reason 与今日新闻强相关
- opportunity **{OPPORTUNITY_COUNT} 条**，name+description+why_watch 总信息量精炼，description 侧重创业/投资/产品/新需求之一
- internal_articles **{INTERNAL_ARTICLE_COUNT} 条左右**，仅用于内部分类归档，可含 category，勿在输出中堆砌分类列表式正文
- 全文洞察导向：少罗列、多解释「为什么」「意味着什么」
- 控制总输出篇幅：相当于中文 600-1000 字的信息量，避免冗长
- link 不得编造；arxiv 类 internal 不宜超过 3 条
- importance 需有区分度"""


def summarize_news(
    grouped: Dict[str, List[NewsItem]],
    *,
    dry_run: bool = False,
) -> DailyBrief:
    news_list = _prepare_news_payload(grouped)
    if not news_list:
        return DailyBrief(overview="今日暂无可用新闻数据。")

    pool = [_article_from_news_entry(n) for n in news_list]

    if dry_run:
        return _dry_run_brief(pool)

    client = _build_client()
    user_content = json.dumps(news_list, ensure_ascii=False, indent=2)
    cfg = _llm_config()
    print(
        f"[summarizer] Calling {cfg['model']} via {cfg['provider']} "
        f"({cfg['base_url'] or 'api.openai.com'}) for {len(news_list)} candidates..."
    )

    data = _call_openai(client, _system_prompt(), user_content, cfg["model"])

    top_hot = _parse_top_events(data)
    if len(top_hot) < TOP_HOT_COUNT:
        print(f"[summarizer] top_events={len(top_hot)}, padding from pool")
        existing_links = {a.link for a in top_hot}
        for art in _pick_top_from_pool(pool, TOP_HOT_COUNT):
            if art.link not in existing_links:
                top_hot.append(art)
                existing_links.add(art.link)
            if len(top_hot) >= TOP_HOT_COUNT:
                break
        top_hot = top_hot[:TOP_HOT_COUNT]

    articles = _parse_internal_articles(data)
    if not articles:
        articles = _pick_top_from_pool(pool, INTERNAL_ARTICLE_COUNT)

    trends = _parse_trends(data)
    tools = _parse_tools(data)
    opportunity = _parse_opportunity(data)

    print(
        f"[summarizer] Brief ready: top={len(top_hot)}, internal={len(articles)}, "
        f"trends={len(trends)}, tools={len(tools)}, opportunity={'yes' if opportunity else 'no'}"
    )

    overview = (data.get("daily_overview") or data.get("overview") or "").strip()
    if not overview and top_hot:
        overview = top_hot[0].summary[:200]

    return DailyBrief(
        overview=overview or "今日 AI 行业情报已整理完毕。",
        articles=articles,
        top_hot=top_hot,
        trends=trends,
        tools=tools,
        opportunity=opportunity,
    )


def regroup_by_category(articles: List[SummarizedArticle]) -> Dict[str, List[SummarizedArticle]]:
    """Group summarized articles by category (internal/debug only)."""
    from collections import defaultdict

    grouped: Dict[str, List[SummarizedArticle]] = defaultdict(list)
    for art in articles:
        cat = normalize_category(art.category)
        grouped[cat].append(art)

    result: Dict[str, List[SummarizedArticle]] = {}
    for cat in CATEGORIES:
        if cat in grouped:
            result[cat] = sorted(grouped[cat], key=lambda a: a.importance, reverse=True)
    return result
