# AI 行业情报与机会发现助手

自动抓取 RSS → 去重分类（内部归档）→ LLM 提炼洞察 → 飞书四模块情报卡片推送。

实现手册：[docs/IMPLEMENTATION_HANDBOOK.md](docs/IMPLEMENTATION_HANDBOOK.md)

## 项目结构

```
AI_Daily_Brief/
├── ai_news_bot/           # 主包
│   ├── main.py            # CLI 入口（cron 可执行）
│   ├── paths.py           # 项目路径常量
│   ├── config.py          # 配置与 RSS 源
│   ├── crawler.py         # RSS 采集
│   ├── classifier.py      # 去重 + 主题分类
│   ├── summarizer.py      # OpenAI 总结与评分
│   └── feishu_card.py     # 飞书交互卡片
├── docs/                  # 实现手册
├── scripts/               # bootstrap / Phase 0 验收
├── logs/                  # cron 日志目录
├── output/                # 可选 JSON 输出
├── requirements.txt
├── pyproject.toml         # 可编辑安装 pip install -e .
├── .env.example
└── Makefile
```

## Phase 0 — 工程脚手架（一键初始化）

```bash
cd AI_Daily_Brief
chmod +x scripts/bootstrap.sh
make bootstrap
# 或: bash scripts/bootstrap.sh
```

验收（与手册 Phase 0 一致）：

```bash
make verify-phase0
# 等价: python scripts/verify_phase0.py
```

手动初始化：

```bash
cd AI_Daily_Brief
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
cp .env.example .env
mkdir -p logs output
python -c "import ai_news_bot; print(ai_news_bot.__version__)"
```

### 分阶段运行

```bash
make crawl-only          # Phase 1+2：仅采集与分类
make dry-run             # 全流程试运行（不调 OpenAI / 不推送）
make run                 # 正式运行（写日志 + 自动保存 output/brief-日期.json）
make verify-all          # Phase 1–6 自动化验收（需网络）
```

### 常用命令

```bash
python -m ai_news_bot.main --dry-run --preview-card output/card.json
python -m ai_news_bot.main --no-push
python -m ai_news_bot.main --log-file logs/brief.log
```

部署详见 [docs/DEPLOY.md](docs/DEPLOY.md)。

## 环境变量

| 变量 | 说明 |
|------|------|
| `LLM_PROVIDER` | 预设：`deepseek` / `moonshot` / `zhipu` / `groq` / `ollama` / `openai` |
| `OPENAI_API_KEY` | 对应平台的 API Key（变量名保留，兼容所有厂商） |
| `OPENAI_MODEL` | 模型名；不填则用该预设默认值 |
| `OPENAI_BASE_URL` | 兼容 API 地址（预设会自动填写） |
| `FEISHU_WEBHOOK_URL` | 飞书小群 Webhook（`FEISHU_PUSH_MODE=webhook`） |

**不想用 OpenAI 付费？** 见 [docs/MODEL_PROVIDERS.md](docs/MODEL_PROVIDERS.md)（推荐 DeepSeek 或本地 Ollama）。

## 飞书推送（个人私聊）

默认推送到**你自己的飞书私聊**（企业自建应用），不是群聊。  
配置步骤见 **[docs/FEISHU_PERSONAL.md](docs/FEISHU_PERSONAL.md)**。

简要：在 [open.feishu.cn](https://open.feishu.cn/app) 创建应用 → 开机器人权限 → `.env` 填 `FEISHU_APP_ID` / `SECRET` / `FEISHU_RECEIVE_ID` → 在飞书里先给机器人发一条消息 → `make run`。

若只想用群 Webhook，设 `FEISHU_PUSH_MODE=webhook` 并填 `FEISHU_WEBHOOK_URL`。  

## 定时推送

| 方式 | 说明 |
|------|------|
| **云端（推荐）** | [docs/CLOUD_SCHEDULE.md](docs/CLOUD_SCHEDULE.md) — GitHub Actions，**无需 Mac 开机/登录**，工作日 8:00 北京时间 |
| 本机 | `scripts/install_launchd.sh` — Mac 需 8:00 前唤醒；8 点后开机靠登录补跑 |

本机 crontab 示例见 [`crontab.example`](crontab.example)。

## RSS 数据源

- Google News（AI 关键词）
- Hacker News（AI/LLM 过滤）
- arXiv cs.AI
- TechCrunch Artificial Intelligence

## 飞书卡片（用户可见，约 3 分钟读完）

1. **🔥 今日最重要 TOP5** — 摘要 + 为什么重要 + 意味着什么 + 链接  
2. **📈 今日趋势观察** — 3 条归纳趋势  
3. **🛠 今日 AI 工具推荐** — 3 个与当日新闻相关的工具  
4. **💰 今日机会观察** — 1 条创业/投资/产品机会  

分类新闻列表仅保存在 `output/brief-*.json` 的 `articles` 字段，不在飞书展示。
