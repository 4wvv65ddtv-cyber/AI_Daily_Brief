#!/usr/bin/env bash
# Run AI Daily Brief on schedule or catch up after login (Mac sleep-safe).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export TZ=Asia/Shanghai
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

MODE="${1:-scheduled}"  # scheduled | login
HOUR="$(date +%H)"
DAY="$(date +%Y%m%d)"
STAMP="logs/sent-${DAY}.stamp"
LOG="logs/cron.log"

mkdir -p logs

# Already sent today
if [ -f "$STAMP" ]; then
  echo "$(date -Iseconds) skip: already sent ($STAMP)" >> "$LOG"
  exit 0
fi

# Login catch-up: only after 08:00 local
if [ "$MODE" = "login" ] && [ "$HOUR" -lt 8 ]; then
  echo "$(date -Iseconds) skip login: before 08:00" >> "$LOG"
  exit 0
fi

echo "$(date -Iseconds) start ($MODE)" >> "$LOG"
./venv/bin/python -m ai_news_bot.main --log-file logs/brief.log >> "$LOG" 2>&1
echo "$(date -Iseconds) exit=$?" >> "$LOG"
