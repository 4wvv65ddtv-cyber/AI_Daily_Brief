#!/usr/bin/env bash
# Open GitHub Desktop + browser pages for push & Actions secrets.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="https://github.com/4wvv65ddtv-cyber/AI_Daily_Brief"

echo "项目目录: $ROOT"
echo ""
echo "【GitHub Desktop】请在该窗口点击: Push origin（或 Publish branch）"
open -a "GitHub Desktop" "$ROOT" 2>/dev/null || echo "请手动打开 GitHub Desktop → File → Add Local Repository → 选择上述目录"

sleep 1
echo "【浏览器】打开 Secrets 配置页（请添加 OPENAI_API_KEY、FEISHU_WEBHOOK_URL）"
open "${REPO}/settings/secrets/actions/new" 2>/dev/null || true

echo ""
echo "Secrets 添加完成后，打开 Actions 手动试跑:"
open "${REPO}/actions/workflows/daily-brief.yml" 2>/dev/null || true
