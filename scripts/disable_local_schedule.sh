#!/usr/bin/env bash
# Stop local cron/LaunchAgent after enabling cloud schedule (avoid duplicate Feishu messages).
set -euo pipefail
launchctl bootout "gui/$(id -u)/com.ai.daily-brief" 2>/dev/null || true
launchctl bootout "gui/$(id -u)/com.ai.daily-brief.login" 2>/dev/null || true
crontab -r 2>/dev/null || true
echo "Local schedule disabled. Use GitHub Actions or server cron — see docs/CLOUD_SCHEDULE.md"
