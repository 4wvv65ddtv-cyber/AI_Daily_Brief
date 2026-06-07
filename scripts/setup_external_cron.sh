#!/usr/bin/env bash
# 一键配置准时云端定时：验证 GitHub Token + 创建 cron-job.org 任务
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

OWNER="4wvv65ddtv-cyber"
REPO="AI_Daily_Brief"
WORKFLOW="daily-brief.yml"
DISPATCH_URL="https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW}/dispatches"
CRON_API="https://api.cron-job.org/jobs"
JOB_TITLE="AI Daily Brief 8AM Beijing"

load_env_key() {
  local key="$1"
  if [ -n "${!key:-}" ]; then
    echo "${!key}"
    return
  fi
  if [ -f .env ]; then
    grep -E "^${key}=" .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"' | sed "s/^'//;s/'$//"
  fi
}

GITHUB_PAT="$(load_env_key GITHUB_PAT)"
CRON_JOB_API_KEY="$(load_env_key CRON_JOB_API_KEY)"

echo "=========================================="
echo "  AI Daily Brief — 准时云端定时（一键配置）"
echo "=========================================="
echo ""

# --- GitHub PAT ---
if [ -z "$GITHUB_PAT" ] && command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  echo "检测到 GitHub CLI 已登录，使用当前会话 token（不写入 .env）..."
  GITHUB_PAT="$(gh auth token)"
fi

if [ -z "$GITHUB_PAT" ]; then
  echo "【需要 GitHub Token】"
  echo "  方式 A（推荐）：在终端执行一次 gh auth login，然后重新运行本脚本"
  echo "    brew install gh   # 若未安装"
  echo "    gh auth login -h github.com -p https -w"
  echo ""
  echo "  方式 B：手动创建 Fine-grained PAT 写入 .env"
  echo "    https://github.com/settings/tokens?type=beta"
  echo "    仓库选 ${REPO}，权限 Actions: Read and write"
  echo "    echo 'GITHUB_PAT=github_pat_xxx' >> .env"
  echo ""
  exit 1
fi

echo "【1/3】验证 GitHub workflow 触发..."
HTTP_CODE=$(curl -sS -o /tmp/gh-dispatch-test.json -w "%{http_code}" -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${GITHUB_PAT}" \
  "${DISPATCH_URL}" \
  -d '{"ref":"main"}')

if [ "$HTTP_CODE" != "204" ]; then
  echo "  ❌ 触发失败 HTTP ${HTTP_CODE}"
  cat /tmp/gh-dispatch-test.json
  exit 1
fi
echo "  ✅ workflow_dispatch 触发成功（请到 GitHub Actions 查看）"

# --- cron-job.org ---
if [ -z "$CRON_JOB_API_KEY" ]; then
  echo ""
  echo "【2/3】需要 cron-job.org API Key（免费注册一次）"
  echo "  1. 打开 https://console.cron-job.org/signup 注册/登录"
  echo "  2. 左侧 Settings → API Key → 复制"
  echo "  3. 写入 .env：  CRON_JOB_API_KEY=你的key"
  echo "  4. 重新运行: bash scripts/setup_external_cron.sh"
  echo ""
  echo "  （GitHub 触发已验证通过；补上 API Key 后会自动创建每天 8:00 定时任务）"
  exit 0
fi

echo ""
echo "【2/3】创建/更新 cron-job.org 定时任务..."

PAYLOAD=$(python3 - <<PY
import json
payload = {
  "job": {
    "title": "${JOB_TITLE}",
    "url": "${DISPATCH_URL}",
    "enabled": True,
    "saveResponses": True,
    "requestMethod": 1,
    "extendedData": {
      "headers": {
        "Authorization": "Bearer ${GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json"
      },
      "body": json.dumps({"ref": "main"})
    },
    "schedule": {
      "timezone": "Asia/Shanghai",
      "expiresAt": 0,
      "hours": [8],
      "minutes": [0],
      "mdays": [-1],
      "months": [-1],
      "wdays": [-1]
    }
  }
}
print(json.dumps(payload))
PY
)

# 查是否已有同名任务
EXISTING=$(curl -sS -H "Authorization: Bearer ${CRON_JOB_API_KEY}" "${CRON_API}" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for j in d.get('jobs',[]):
    if j.get('title')=='${JOB_TITLE}':
        print(j['jobId'])
        break
" 2>/dev/null || true)

if [ -n "$EXISTING" ]; then
  HTTP_CODE=$(curl -sS -o /tmp/cronjob-res.json -w "%{http_code}" -X PATCH \
    -H "Authorization: Bearer ${CRON_JOB_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    "${CRON_API}/${EXISTING}")
  ACTION="更新"
else
  HTTP_CODE=$(curl -sS -o /tmp/cronjob-res.json -w "%{http_code}" -X PUT \
    -H "Authorization: Bearer ${CRON_JOB_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    "${CRON_API}")
  ACTION="创建"
fi

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
  JOB_ID=$(python3 -c "import json; print(json.load(open('/tmp/cronjob-res.json')).get('jobId','?'))")
  echo "  ✅ 已${ACTION} cron 任务 (jobId=${JOB_ID})，每天 08:00 Asia/Shanghai"
else
  echo "  ❌ cron-job.org ${ACTION}失败 HTTP ${HTTP_CODE}"
  cat /tmp/cronjob-res.json
  exit 1
fi

# 备用 8:15
BACKUP_TITLE="AI Daily Brief 815 Backup"
BACKUP_PAYLOAD=$(python3 - <<PY
import json
payload = {
  "job": {
    "title": "${BACKUP_TITLE}",
    "url": "${DISPATCH_URL}",
    "enabled": True,
    "saveResponses": False,
    "requestMethod": 1,
    "extendedData": {
      "headers": {
        "Authorization": "Bearer ${GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json"
      },
      "body": json.dumps({"ref": "main"})
    },
    "schedule": {
      "timezone": "Asia/Shanghai",
      "expiresAt": 0,
      "hours": [8],
      "minutes": [15],
      "mdays": [-1],
      "months": [-1],
      "wdays": [-1]
    }
  }
}
print(json.dumps(payload))
PY
)

EXISTING2=$(curl -sS -H "Authorization: Bearer ${CRON_JOB_API_KEY}" "${CRON_API}" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for j in d.get('jobs',[]):
    if j.get('title')=='${BACKUP_TITLE}':
        print(j['jobId'])
        break
" 2>/dev/null || true)

if [ -n "$EXISTING2" ]; then
  curl -sS -o /dev/null -X PATCH \
    -H "Authorization: Bearer ${CRON_JOB_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "$BACKUP_PAYLOAD" \
    "${CRON_API}/${EXISTING2}"
else
  curl -sS -o /dev/null -X PUT \
    -H "Authorization: Bearer ${CRON_JOB_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "$BACKUP_PAYLOAD" \
    "${CRON_API}"
fi
echo "  ✅ 已配置 08:15 备用任务（同一天 workflow 防重复，不会连发两条）"

echo ""
echo "【3/3】完成"
echo "  • 云端：cron-job.org 每天 8:00 触发 GitHub Actions → 飞书"
echo "  • 本机：crontab 8:00 备份（Mac 醒着时）"
echo "  • GitHub 内置 schedule 仅兜底，可忽略"
echo ""
echo "明天 8:00 后检查飞书；Actions 里应出现 event=workflow_dispatch 的绿色记录。"
