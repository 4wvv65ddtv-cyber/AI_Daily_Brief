#!/usr/bin/env bash
# Phase 0: one-shot project setup
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> AI Daily Brief — bootstrap"
echo "    Project root: $ROOT"

if [[ ! -d venv ]]; then
  echo "==> Creating virtualenv..."
  python3 -m venv venv
fi

# shellcheck source=/dev/null
source venv/bin/activate

echo "==> Installing dependencies..."
python -m pip install -q --upgrade "pip>=23.0" setuptools wheel
pip install -q -r requirements.txt
pip install -q -e . || {
  echo "    (editable install skipped — use: python -m ai_news_bot.main from project root)"
}

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "==> Created .env from .env.example — please edit API keys"
else
  echo "==> .env already exists, skipped copy"
fi

mkdir -p logs output

echo "==> Running Phase 0 verification..."
python scripts/verify_phase0.py

echo ""
echo "Bootstrap complete. Next steps:"
echo "  1. Edit .env with OPENAI_API_KEY and FEISHU_WEBHOOK_URL"
echo "  2. python -m ai_news_bot.main --dry-run"
