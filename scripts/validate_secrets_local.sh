#!/usr/bin/env bash
# 本地检查 .env 是否可跑通（不打印密钥）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export GITHUB_ACTIONS=true
export PYTHONIOENCODING=utf-8
export FEISHU_PUSH_MODE=webhook
set -a
# shellcheck disable=SC1091
source .env
set +a
./venv/bin/python -m ai_news_bot.main --crawl-only
echo "crawl-only OK"
./venv/bin/python -m ai_news_bot.main
echo "full run OK — check Feishu group"
