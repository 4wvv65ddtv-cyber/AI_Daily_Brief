# AI 行业每日早报系统 — 实现手册

> **文档用途**：作为后续 AI Coding 的行动手册。按阶段、按模块拆解需求、接口、验收标准与实现步骤。  
> **项目路径**：`AI_Daily_Brief/`  
> **当前状态**：v1.0 基础链路已实现（见文末「实现进度」），本文档同时指导增量优化与二次开发。

---

## 目录

1. [产品目标与范围](#1-产品目标与范围)
2. [需求—模块映射表](#2-需求模块映射表)
3. [系统架构](#3-系统架构)
4. [目录与文件职责](#4-目录与文件职责)
5. [数据模型与流转](#5-数据模型与流转)
6. [分阶段实现计划](#6-分阶段实现计划)
7. [模块实现细则](#7-模块实现细则)
8. [主流程编排（main.py）](#8-主流程编排mainpy)
9. [配置与环境变量](#9-配置与环境变量)
10. [外部依赖与 API 约定](#10-外部依赖与-api-约定)
11. [测试与验收清单](#11-测试与验收清单)
12. [部署与定时任务](#12-部署与定时任务)
13. [已知问题与扩展 backlog](#13-已知问题与扩展-backlog)
14. [AI Coding 会话指引](#14-ai-coding-会话指引)
15. [实现进度跟踪](#15-实现进度跟踪)

---

## 1. 产品目标与范围

### 1.1 一句话描述

每日自动抓取 AI 行业 RSS 新闻 → 去重与分类 → OpenAI 生成结构化简报 → 飞书交互卡片推送 → 支持 cron 无人值守运行。

### 1.2 核心产出（对用户可见）

| 产出物 | 说明 |
|--------|------|
| 今日 AI 热点 TOP5 | 带 1–10 重要性评分，按分数降序 |
| 分类新闻列表 | 5 大主题 +「其他」，可折叠展示 |
| AI 总结日报 | 自然语言总览 + 每条 1–2 句摘要（共 5–8 条精选） |
| 飞书卡片 | 非纯文本；标题、日期、链接可点击 |

### 1.3 非目标（v1 不做）

- 网页爬虫（非 RSS）
- 用户后台 / Web UI
- 数据库存储与历史检索（可作为 v2）
- 多语言简报（默认中文输出，源可为英文）

### 1.4 成功标准

- [ ] `python -m ai_news_bot.main --dry-run` 在无密钥时可跑通采集与分类
- [ ] 配置 `.env` 后 `main` 可完成 OpenAI 总结
- [ ] 飞书群收到符合规范的交互卡片
- [ ] cron 每日执行无交互、日志可追踪

---

## 2. 需求—模块映射表

| # | 原始需求 | 负责模块 | 关键函数/产物 |
|---|----------|----------|----------------|
| R1 | RSS 采集（Google News / HN / arXiv / TechCrunch） | `crawler.py` | `crawl_all_feeds()` → `List[NewsItem]` |
| R2 | 标题 + 链接 + 来源 | `crawler.py` | `NewsItem` 数据类 |
| R3 | 去重 | `classifier.py` | `deduplicate_items()` |
| R4 | 主题分类（5 类） | `classifier.py` + `summarizer.py` | 规则预分类 + LLM 修正 |
| R5 | OpenAI 总结（gpt-4o-mini） | `summarizer.py` | `summarize_news()` → `DailyBrief` |
| R6 | 5–8 条总结、1–2 句/条、评分、排序 | `summarizer.py` | `SummarizedArticle.importance` |
| R7 | 输出 TOP5 + 分类列表 + 日报 | `main.py` + `feishu_card.py` | 控制台 + 卡片结构 |
| R8 | 飞书 Webhook 卡片 | `feishu_card.py` | `build_feishu_card()` / `send_feishu_card()` |
| R9 | cron 可执行 | `main.py` | CLI、`--dry-run`、`--no-push` |
| R10 | 代码结构 6 文件 + config | 全包 | 见 §4 |

---

## 3. 系统架构

### 3.1 流水线总览

```mermaid
flowchart LR
    subgraph input [输入]
        RSS[RSS Feeds x4]
        ENV[.env 配置]
    end

    subgraph pipeline [处理流水线]
        C[crawler.py\n采集]
        CL[classifier.py\n去重+分类]
        S[summarizer.py\nOpenAI总结]
        F[feishu_card.py\n卡片构建/推送]
    end

    subgraph output [输出]
        CON[控制台报告]
        JSON[可选 JSON 文件]
        FS[飞书 Webhook]
    end

    RSS --> C
    ENV --> C
    ENV --> S
    ENV --> F
    C -->|NewsItem[]| CL
    CL -->|grouped dict| S
    S -->|DailyBrief| F
    S --> CON
    F --> FS
    S --> JSON
```

### 3.2 模块依赖关系

```
config.py          （无内部依赖，被全模块引用）
    ↑
crawler.py         → config
classifier.py      → config, crawler.NewsItem
summarizer.py      → config, crawler.NewsItem
feishu_card.py     → config, summarizer.DailyBrief
main.py            → classifier, crawler, summarizer, feishu_card
```

### 3.3 设计原则（AI Coding 时遵守）

1. **单向数据流**：`NewsItem` → 分组字典 → `DailyBrief` → 飞书 JSON，不反向污染原始条目。
2. **配置集中**：RSS URL、分类关键词、阈值仅改 `config.py`。
3. **可降级运行**：`--dry-run` 跳过 OpenAI 与飞书；HN 源失败走 fallback。
4. **失败可观测**：每步 `print("[模块] ...")` 日志，cron 重定向到文件。

---

## 4. 目录与文件职责

```
AI_Daily_Brief/
├── ai_news_bot/
│   ├── __init__.py          # 包版本号
│   ├── config.py            # ★ 所有常量、RSS、分类词表、环境变量
│   ├── crawler.py           # ★ RSS 抓取、NewsItem、去重键
│   ├── classifier.py        # ★ 去重、规则分类、分组
│   ├── summarizer.py        # ★ OpenAI、DailyBrief、TOP5 逻辑
│   ├── feishu_card.py       # ★ 卡片 JSON、Webhook POST
│   └── main.py              # ★ CLI 入口、流程编排
├── docs/
│   └── IMPLEMENTATION_HANDBOOK.md   # 本文档
├── requirements.txt
├── pyproject.toml           # pip install -e .
├── Makefile                 # bootstrap / verify-phase0
├── scripts/
│   ├── bootstrap.sh         # 一键初始化
│   └── verify_phase0.py     # Phase 0 验收
├── .env.example
├── .gitignore
├── README.md
├── logs/                    # cron 日志（.gitkeep）
└── output/                  # JSON 输出（.gitkeep）
```

---

## 5. 数据模型与流转

### 5.1 `NewsItem`（采集层）

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | str | RSS 标题 |
| `link` | str | 原文 URL |
| `source` | str | 来源名称（如 `TechCrunch AI`） |
| `summary` | str | RSS 摘要/描述，HTML 已剥离，≤500 字 |
| `dedup_key` | str | MD5(normalized_title + canonical_link) |

**生成位置**：`crawler.py` → `NewsItem.__post_init__` 自动计算 `dedup_key`。

### 5.2 分类分组（处理层）

```python
Dict[str, List[NewsItem]]
# key: CATEGORIES 中的中文类名
# value: 该类下的新闻列表（已去重）
```

### 5.3 `SummarizedArticle`（总结层）

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | str | 展示标题（可精简） |
| `original_title` | str | 原始 RSS 标题 |
| `link` | str | 原文链接 |
| `source` | str | 来源 |
| `category` | str | 最终分类（LLM 输出） |
| `summary` | str | 1–2 句中文摘要 |
| `importance` | int | 1–10，10 最重要 |

### 5.4 `DailyBrief`（输出层）

| 字段 | 类型 | 说明 |
|------|------|------|
| `overview` | str | 200–400 字日报总览 |
| `articles` | List[SummarizedArticle] | 5–8 条精选（已按 importance 排序） |
| `top_hot` | List[SummarizedArticle] | TOP5（`articles` 前 5 条） |

### 5.5 飞书卡片 payload（推送层）

```json
{
  "msg_type": "interactive",
  "card": {
    "config": { "wide_screen_mode": true },
    "header": { "title": "📊 今日AI早报", "template": "blue" },
    "elements": [ "... div / hr / collapsible_panel ..." ]
  }
}
```

---

## 6. 分阶段实现计划

> **给 AI Coding 的使用方式**：每个 Phase 可单独开一个会话，完成该 Phase 全部勾选后再进入下一阶段。

### Phase 0 — 工程脚手架（预估 15 min）✅ 已完成

| 步骤 | 任务 | 产出 | 状态 |
|------|------|------|------|
| 0.1 | 创建 `ai_news_bot/` 包与 `requirements.txt`、`pyproject.toml` | `pip install -e .` | ✅ |
| 0.2 | 编写 `.env.example`、`README.md`、`.gitignore` | 密钥说明 + 忽略规则 | ✅ |
| 0.3 | `main.py` 加载 `dotenv`、argparse（`--dry-run` 等） | CLI 入口 | ✅ |
| 0.4 | `paths.py`、`logs/`、`output/`、`scripts/bootstrap.sh` | 路径常量 + 目录 + 一键初始化 | ✅ |
| 0.5 | `scripts/verify_phase0.py`、`Makefile` | 自动化验收 | ✅ |

**验收**：

```bash
make bootstrap          # 一键初始化 + 验收
make verify-phase0      # 仅验收
python -c "import ai_news_bot; print(ai_news_bot.__version__)"
```

---

### Phase 1 — 数据采集（`crawler.py` + `config.py`）✅ 已完成

| 步骤 | 任务 | 细节 | 状态 |
|------|------|------|------|
| 1.1 | 定义 `RSSSource`、`RSS_FEEDS` | 4 个源 URL | ✅ |
| 1.2 | `_fetch_feed` + 重试 | `requests` + `feedparser`，`CRAWL_REQUEST_RETRIES` | ✅ |
| 1.3 | `NewsItem` + `dedup_key` + `published` | Google News URL 解包 | ✅ |
| 1.4 | `crawl_with_report()` 并行采集 | `ThreadPoolExecutor`，`CRAWL_MAX_WORKERS` | ✅ |
| 1.5 | HN fallback | `HACKER_NEWS_FALLBACK_URLS` + AI 关键词过滤 | ✅ |

**验收**：

```bash
python -c "from ai_news_bot.crawler import crawl_with_report; r=crawl_with_report(); print(r.total, r.per_source)"
make crawl-only
# 期望 total > 20
```

**AI Prompt 模板**：

> 在 `crawler.py` 实现 RSS 采集，数据源见 `config.RSS_FEEDS`，返回 `NewsItem` 列表，含 dedup_key 与摘要清洗。

---

### Phase 2 — 去重与分类（`classifier.py`）✅ 已完成

| 步骤 | 任务 | 细节 | 状态 |
|------|------|------|------|
| 2.1 | `deduplicate_items` | 按 `dedup_key` 保留首次 | ✅ |
| 2.2 | `CATEGORY_KEYWORDS` 打分 | `classify_item` 返回 (类别, 分数) | ✅ |
| 2.3 | `classify_all` | 按 `CATEGORIES` 顺序输出 dict | ✅ |
| 2.4 | `classification_stats` | 日志/验收用统计 | ✅ |

**分类枚举（必须与 LLM prompt 一致）**：

1. `大模型（LLM）`
2. `公司动态` — OpenAI / Google / Meta / Anthropic 等
3. `AI产品发布`
4. `AI论文 / 技术突破`
5. `AI投资 / 融资`
6. `其他`

**验收**：

```bash
python -m ai_news_bot.main --dry-run
# 日志应显示 After dedup: N items in M categories
```

---

### Phase 3 — AI 总结（`summarizer.py`）✅ 已完成

| 步骤 | 任务 | 细节 | 状态 |
|------|------|------|------|
| 3.1 | `_build_client()` | `OPENAI_API_KEY` / `OPENAI_BASE_URL` | ✅ |
| 3.2 | `_prepare_news_payload` | 每类最多 8 条 | ✅ |
| 3.3 | System prompt + JSON mode | `daily_overview` + `articles[]` | ✅ |
| 3.4 | `_call_openai` 重试 | `OPENAI_MAX_RETRIES` | ✅ |
| 3.5 | `normalize_category` | `config.normalize_category` | ✅ |
| 3.6 | `top_hot` / `regroup_by_category` | TOP5 + 飞书折叠 | ✅ |
| 3.7 | `dry_run` 启发式评分 | `_heuristic_importance`（非固定 5 分） | ✅ |

**OpenAI 请求参数（固定）**：

| 参数 | 值 |
|------|-----|
| model | `gpt-4o-mini`（`OPENAI_MODEL`） |
| temperature | 0.4 |
| response_format | `{ "type": "json_object" }` |

**JSON 响应 schema（LLM 必须遵守）**：

```json
{
  "daily_overview": "string",
  "articles": [
    {
      "original_title": "string",
      "title": "string",
      "link": "string",
      "source": "string",
      "category": "大模型（LLM）|公司动态|...",
      "summary": "string",
      "importance": 7
    }
  ]
}
```

**条数约束**：`BRIEF_ITEM_COUNT_MIN=5`，`BRIEF_ITEM_COUNT_MAX=8`。

**验收**：配置 `OPENAI_API_KEY` 后运行 `main`，控制台 TOP5 分数应有差异（非全 5）。

---

### Phase 4 — 飞书卡片（`feishu_card.py`）✅ 已完成

| 步骤 | 任务 | 卡片区块 | 状态 |
|------|------|----------|------|
| 4.1 | `build_feishu_card` | header：📊 今日AI早报 | ✅ |
| 4.2 | `format_date_str` | Asia/Shanghai | ✅ |
| 4.3 | TOP5 区 | lark_md 链接 + 评分 | ✅ |
| 4.4 | 日报总览 | overview ≤2000 字 | ✅ |
| 4.5 | 分类折叠 | collapsible_panel | ✅ |
| 4.6 | 每条新闻 | 链接 + 摘要 + 来源 | ✅ |
| 4.7 | `send_feishu_card` + `validate_card` + `save_card_json` | Webhook + 本地预览 | ✅ |

**卡片元素顺序（固定）**：

1. 日期 `div`
2. `hr`
3. TOP5 标题 + 内容
4. `hr`
5. AI总结日报 标题 + 内容
6. `hr`
7. 各分类 `collapsible_panel`（按 `CATEGORIES` 顺序）

**验收**：向测试群发卡片，链接可点击、折叠可展开。

---

### Phase 5 — 主流程与 CLI（`main.py`）✅ 已完成

| 步骤 | 任务 | 说明 | 状态 |
|------|------|------|------|
| 5.1 | 串联 1→2→3→4 | `crawl_with_report` → `classify_all` → `summarize` → Feishu | ✅ |
| 5.2 | `_print_console_report` | 控制台预览 | ✅ |
| 5.3 | `--dry-run` / `--no-push` / `--crawl-only` | 分阶段运行 | ✅ |
| 5.4 | `--preview-card` / `--save-json` | 本地产物 | ✅ |
| 5.5 | `--log-file` + `logging_config` | cron 友好日志 | ✅ |
| 5.6 | 退出码 | 无新闻=1，飞书失败=2，成功=0 | ✅ |

**验收**：完整链路 `python -m ai_news_bot.main` 一次成功。

---

### Phase 6 — 部署与运维 ✅ 已完成

| 步骤 | 任务 | 状态 |
|------|------|------|
| 6.1 | `logs/`、`crontab.example`、cron 重定向 | ✅ |
| 6.2 | `scripts/bootstrap.sh`、`docs/DEPLOY.md` | ✅ |
| 6.3 | `.gitignore` 忽略 `.env` | ✅ |
| 6.4 | `scripts/verify_phases.py`、`make verify-all` | ✅ |
| 6.5 | 失败告警 | ⬜ v2 backlog |

---

## 7. 模块实现细则

### 7.1 `config.py`

**职责**：单一配置源，禁止在其他文件硬编码 RSS URL。

**必须包含的配置项**：

| 常量 | 用途 |
|------|------|
| `RSS_FEEDS` | 4 个 `RSSSource` |
| `HACKER_NEWS_FALLBACK_URLS` | HN 备用 |
| `CATEGORIES` | 展示顺序 |
| `CATEGORY_KEYWORDS` | 规则分类词表 |
| `OPENAI_*` / `FEISHU_WEBHOOK_URL` | 从 `os.getenv` 读取 |
| `MAX_ITEMS_PER_FEED` / `MAX_TOTAL_ITEMS` | 采集上限 |
| `BRIEF_ITEM_COUNT_*` / `TOP_HOT_COUNT` | 总结条数 |

**扩展指引**：新增 RSS 源 = 在 `RSS_FEEDS` 追加一项 + 更新 README。

---

### 7.2 `crawler.py`

**核心函数**：

| 函数 | 输入 | 输出 |
|------|------|------|
| `_fetch_feed` | url, source_name | `List[NewsItem]` |
| `_fetch_hacker_news` | — | 带 fallback 的 HN 列表 |
| `crawl_all_feeds` | — | 合并所有源 |

**错误处理**：

- 单源失败：打印 `[crawler] Failed...`，返回 `[]`，不中断其他源。
- 禁止因单源失败导致进程崩溃。

**去重键逻辑（勿随意修改）**：

```
dedup_key = md5(normalize(title) + "|" + canonical_link)
```

Google News 链接需从 `?url=` 参数提取真实 URL。

---

### 7.3 `classifier.py`

**核心函数**：

| 函数 | 说明 |
|------|------|
| `deduplicate_items` | 全局去重 |
| `classify_item` | 单条规则分类 |
| `classify_all` | 去重 + 分组 |
| `flatten_grouped` | 工具函数，展平分组 |

**与 summarizer 的分工**：

- **规则分类**：粗筛、减少 LLM 输入噪声、飞书折叠预分组。
- **LLM 分类**：在 JSON 输出中可覆盖 `category_hint`。

---

### 7.4 `summarizer.py`

**核心函数**：

| 函数 | 说明 |
|------|------|
| `summarize_news(grouped, dry_run=False)` | 主入口 |
| `regroup_by_category(articles)` | 按最终 category 分组 |

**Prompt 要点（修改时同步本文档 §6 Phase 3）**：

- 角色：资深 AI 行业分析师
- 语言：中文输出
- 客观、高信息密度
- importance 必须有区分度
- 严格 JSON，无 markdown 包裹

**Token 控制建议（v2）**：

- 候选过多时先按规则分数取 Top N 再送 LLM
- 或对 `snippet` 做截断（当前 300 字）

---

### 7.5 `feishu_card.py`

**核心函数**：

| 函数 | 说明 |
|------|------|
| `build_feishu_card(brief, date_str=None)` | 纯构建，便于单元测试 |
| `send_feishu_card(brief, webhook_url=None, dry_run=False)` | 构建 + POST |

**Markdown 链接注意**：

- 标题中的 `|` 需转义为 `\|`，避免破坏 `lark_md`。

**Webhook 成功判断**：

```python
resp.status_code == 200 and body.get("code", body.get("StatusCode")) == 0
```

---

## 8. 主流程编排（main.py）

### 8.1 伪代码（实现时必须保持一致）

```
load_dotenv()
parse_args()

raw = crawl_all_feeds()
if empty: exit(1)

grouped = classify_all(raw)
brief = summarize_news(grouped, dry_run=args.dry_run)

_print_console_report(brief)

if args.save_json:
    write JSON

if args.dry_run or args.no_push:
    send_feishu_card(brief, dry_run=True)  # 仅打印 JSON 片段
else:
    ok = send_feishu_card(brief)
    if not ok: exit(2)

exit(0)
```

### 8.2 CLI 参数表

| 参数 | 行为 |
|------|------|
| （无） | 完整流水线 + 推送 |
| `--dry-run` | 采集+分类+模拟总结+打印卡片 JSON |
| `--no-push` | 真实 OpenAI，不推送飞书 |
| `--save-json PATH` | 额外保存结果 |

---

## 9. 配置与环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `OPENAI_API_KEY` | 正式运行是 | — | OpenAI 密钥 |
| `OPENAI_MODEL` | 否 | `gpt-4o-mini` | 总结模型 |
| `OPENAI_BASE_URL` | 否 | 官方 | 代理/兼容端点 |
| `FEISHU_WEBHOOK_URL` | 推送时是 | — | 群机器人 Webhook |
| `MAX_ITEMS_PER_FEED` | 否 | `15` | 每源条数上限 |
| `MAX_TOTAL_ITEMS` | 否 | `60` | 总条数上限 |
| `REQUEST_TIMEOUT` | 否 | `30` | HTTP 超时秒 |

---

## 10. 外部依赖与 API 约定

### 10.1 Python 依赖（`requirements.txt`）

```
feedparser>=6.0.11
requests>=2.31.0
openai>=1.40.0
python-dotenv>=1.0.1
```

### 10.2 RSS 源 URL（`config.py` 现状）

| 源 | URL |
|----|-----|
| Google News | `news.google.com/rss/search?q=artificial+intelligence+OR+AI+OR+LLM...` |
| Hacker News | `hnrss.org/newest?q=AI+OR+LLM+...` + fallback |
| arXiv AI | `export.arxiv.org/rss/cs.AI` |
| TechCrunch AI | `techcrunch.com/category/artificial-intelligence/feed/` |

### 10.3 飞书 Webhook

- 文档：[自定义机器人](https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot)
- 消息类型：`interactive`
- 限制：注意单卡片体积与频率，避免触发限流

### 10.4 OpenAI Chat Completions

- Endpoint：SDK 默认 `chat.completions.create`
- 必须使用 `response_format: json_object` 保证可解析

---

## 11. 测试与验收清单

### 11.1 单元级（可按模块手动测）

| 模块 | 测试命令/方法 | 期望 |
|------|----------------|------|
| crawler | `crawl_all_feeds()` | ≥1 源有数据，字段非空 |
| classifier | 构造重复 `NewsItem` | 去重后数量减少 |
| classifier | 标题含 `OpenAI` | 分类为 `公司动态` |
| summarizer | mock OpenAI 响应 | 解析 JSON 正确 |
| feishu | `build_feishu_card` | JSON 含 header + collapsible_panel |

### 11.2 集成测试

```bash
# T1 无密钥冒烟
python -m ai_news_bot.main --dry-run

# T2 仅总结
python -m ai_news_bot.main --no-push --save-json output/test.json

# T3 端到端（需 .env）
python -m ai_news_bot.main
```

### 11.3 飞书卡片人工检查项

- [ ] 标题显示「📊 今日AI早报」
- [ ] 日期为当日北京时间
- [ ] TOP5 含分数且可点击
- [ ] 分类可折叠/展开
- [ ] 链接在飞书客户端内可打开

---

## 12. 部署与定时任务

### 12.1 推荐 crontab

```cron
0 8 * * 1-5 cd /Users/yanxin/Desktop/AI_Daily_Brief && ./venv/bin/python -m ai_news_bot.main >> logs/brief.log 2>&1
```

### 12.2 首次部署检查单

1. [ ] `python3 -m venv venv && pip install -r requirements.txt`
2. [ ] `cp .env.example .env` 并填写密钥
3. [ ] `mkdir -p logs output`
4. [ ] 手动跑一次 T3 确认飞书收到
5. [ ] 写入 crontab 并次日检查 `logs/brief.log`

---

## 13. 已知问题与扩展 backlog

### 13.1 已知问题

| 问题 | 影响 | 建议修复 |
|------|------|----------|
| hnrss.org 间歇 502/SSL | HN 条数少 | 已实现 fallback；可加 Redis 缓存昨日条目 |
| Google News 链接为跳转 URL | 阅读体验 | 已部分 canonical；v2 可请求真实 URL |
| arXiv 条目偏多 | 分类偏「论文」 | LLM prompt 强调产业新闻优先级 |
| dry-run 重要性均为 5 | 预览不真实 | 可用简单启发式打分 |

### 13.2 v2 扩展 backlog（按需拆 Phase）

| 优先级 | 功能 | 建议模块 |
|--------|------|----------|
| P1 | SQLite 历史去重（跨日） | 新建 `storage.py` |
| P1 | 失败重试 + 告警 | `main.py` / `notifier.py` |
| P2 | 中文源 RSS（36氪、机器之心） | `config.py` + `crawler.py` |
| P2 | 并行抓取 `asyncio`/`ThreadPool` | `crawler.py` |
| P3 | 飞书签名鉴权（非 webhook） | `feishu_card.py` |
| P3 | Web 仪表盘 | 独立前端项目 |

---

## 14. AI Coding 会话指引

### 14.1 推荐会话拆分

| 会话 # | 目标 | 仅改文件 |
|--------|------|----------|
| S1 | 修 crawler / 新增源 | `config.py`, `crawler.py` |
| S2 | 优化分类准确率 | `classifier.py`, `config.py` |
| S3 | 优化 prompt / 模型 | `summarizer.py` |
| S4 | 飞书 UI 调整 | `feishu_card.py` |
| S5 | CLI / 日志 / 存储 | `main.py`, 新模块 |

### 14.2 给 AI 的上下文粘贴模板

```markdown
请根据 @docs/IMPLEMENTATION_HANDBOOK.md 的 Phase X 实现/修改功能。
约束：
- 不改动未列出的文件
- 保持现有数据类字段名
- 运行 python -m ai_news_bot.main --dry-run 验证
```

### 14.3 代码审查要点

1. 新增配置项是否加入 `.env.example` 与本文档 §9  
2. 分类名是否与 `CATEGORIES` 和 LLM prompt 完全一致  
3. 异常是否只影响单源/单步  
4. 飞书 JSON 是否符合[卡片结构](https://open.feishu.cn/document/uAjLw4CM/ukzMukzMukzM/feishu-cards/feishu-card-cardkit/component-overview)

---

## 15. 实现进度跟踪

> 在每次 AI Coding 完成后更新下表。

| Phase | 描述 | 状态 | 备注 |
|-------|------|------|------|
| 0 | 工程脚手架 | ✅ 完成 | bootstrap / verify_phase0 |
| 1 | RSS 采集 | ✅ 完成 | 并行 + 重试 + crawl_with_report |
| 2 | 去重分类 | ✅ 完成 | classification_stats |
| 3 | OpenAI 总结 | ✅ 完成 | 重试 + normalize + 启发式 dry-run |
| 4 | 飞书卡片 | ✅ 完成 | validate + save_card_json |
| 5 | main CLI | ✅ 完成 | crawl-only / preview-card / logging |
| 6 | 部署运维 | ✅ 完成 | DEPLOY.md / crontab.example / verify_phases |
| v2 | 存储/告警/中文源 | ⬜ 未开始 | 见 §13.2 |

---

## 附录 A：原始需求原文对照

1. **数据采集**：RSS（Google News / Hacker News / arXiv AI / TechCrunch AI）→ `crawler.py`  
2. **数据处理**：去重 + 5 类主题 → `classifier.py`  
3. **AI 总结**：gpt-4o-mini，5–8 条、1–2 句、1–10 分、排序 → `summarizer.py`  
4. **输出结构**：TOP5 + 分类列表 + 自然语言日报 → `DailyBrief` + `main` 预览  
5. **飞书推送**：Webhook 交互卡片 → `feishu_card.py`  
6. **定时运行**：cron 执行 `main.py`  
7. **代码结构**：6 模块 + `config.py`  

---

## 附录 B：输出示例结构（逻辑示意）

```
📊 今日AI早报
📅 2026年06月03日 Wednesday

🔥 今日AI热点 TOP5
  1. [标题](url) — 8/10
     > 摘要两句...
  ...

📝 AI总结日报
  （200-400 字总览）

📂 大模型（LLM）（3条）  [折叠]
📂 公司动态（2条）      [折叠]
...
```

---

*文档版本：v1.0 | 最后更新：2026-06-03*
