#!/usr/bin/env bash
# Open all pages needed for the last 2 manual steps.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="https://github.com/4wvv65ddtv-cyber/AI_Daily_Brief"

open -a "GitHub Desktop" "$ROOT" 2>/dev/null || true
open "$REPO" 2>/dev/null || true
open "${REPO}/settings/secrets/actions" 2>/dev/null || true
open "${REPO}/actions/workflows/daily-brief.yml" 2>/dev/null || true
open -e "${ROOT}/.env" 2>/dev/null || true
open "${ROOT}/docs/还需你完成2步.md" 2>/dev/null || true

echo "已打开：GitHub Desktop、仓库页、Secrets 页、Actions、.env、说明文档"
echo "请按 docs/还需你完成2步.md 完成 Push + 2 个 Secret。"
