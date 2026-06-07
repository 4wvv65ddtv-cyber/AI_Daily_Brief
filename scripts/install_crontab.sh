#!/usr/bin/env bash
# Install daily 08:00 Beijing crontab (logged-in user; more reliable than launchd on Desktop).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CRON_FILE="${ROOT}/.crontab.installed"
RUN="${ROOT}/scripts/run_daily.sh"

chmod +x "$RUN"

cat > "$CRON_FILE" <<EOF
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
TZ=Asia/Shanghai

# AI Daily Brief — 每天 08:00 北京时间（含周末）
0 8 * * * ${RUN} scheduled >> ${ROOT}/logs/cron.log 2>&1
# 08:15 备用（Mac 8:00 唤醒略晚时）
15 8 * * * ${RUN} scheduled >> ${ROOT}/logs/cron.log 2>&1
EOF

crontab "$CRON_FILE"
rm -f "$CRON_FILE"
echo "Installed crontab:"
crontab -l
