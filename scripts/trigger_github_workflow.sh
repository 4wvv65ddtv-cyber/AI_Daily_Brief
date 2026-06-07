#!/usr/bin/env bash
# 准时触发 GitHub Actions（比内置 schedule 可靠）。需 GITHUB_PAT 环境变量。
# 用法：GITHUB_PAT=ghp_xxx ./scripts/trigger_github_workflow.sh
set -euo pipefail

OWNER="4wvv65ddtv-cyber"
REPO="AI_Daily_Brief"
WORKFLOW="daily-brief.yml"
REF="${1:-main}"

PAT="${GITHUB_PAT:-${GH_TOKEN:-}}"
if [ -z "$PAT" ]; then
  echo "错误：请设置 GITHUB_PAT（GitHub → Settings → Developer settings → Fine-grained token，权限 Actions: Read and write）" >&2
  exit 1
fi

HTTP_CODE=$(curl -sS -o /tmp/gh-dispatch.json -w "%{http_code}" -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${PAT}" \
  "https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW}/dispatches" \
  -d "{\"ref\":\"${REF}\"}")

if [ "$HTTP_CODE" = "204" ]; then
  echo "已触发 workflow_dispatch（${REF}）"
else
  echo "触发失败 HTTP ${HTTP_CODE}:" >&2
  cat /tmp/gh-dispatch.json >&2
  exit 1
fi
