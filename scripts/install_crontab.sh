#!/usr/bin/env bash
# Install weekday 08:00 Beijing cron for AI Daily Brief.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CRON_FILE="${ROOT}/.crontab.installed"

cat > "$CRON_FILE" <<EOF
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
TZ=Asia/Shanghai

# AI Daily Brief — weekdays 08:00 Asia/Shanghai → Feishu push
0 8 * * 1-5 cd ${ROOT} && ./venv/bin/python -m ai_news_bot.main --log-file logs/brief.log >> logs/cron.log 2>&1
EOF

crontab "$CRON_FILE"
rm -f "$CRON_FILE"
echo "Installed crontab:"
crontab -l
