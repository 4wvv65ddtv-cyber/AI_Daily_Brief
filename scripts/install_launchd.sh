#!/usr/bin/env bash
# Install macOS LaunchAgents: 08:00 schedule + login catch-up after sleep.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AGENTS="$HOME/Library/LaunchAgents"
chmod +x "$ROOT/scripts/run_daily.sh"

cp "$ROOT/scripts/com.ai.daily-brief.plist" "$AGENTS/"
cp "$ROOT/scripts/com.ai.daily-brief.login.plist" "$AGENTS/"

launchctl bootout "gui/$(id -u)/com.ai.daily-brief" 2>/dev/null || true
launchctl bootout "gui/$(id -u)/com.ai.daily-brief.login" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$AGENTS/com.ai.daily-brief.plist"
launchctl bootstrap "gui/$(id -u)" "$AGENTS/com.ai.daily-brief.login.plist"

echo "LaunchAgents installed:"
launchctl print "gui/$(id -u)/com.ai.daily-brief" 2>/dev/null | head -5 || launchctl list | grep daily-brief
echo ""
echo "  • 每天 08:00（Mac 醒着时自动发）"
echo "  • 登录补跑：8 点后开机且今天还没发过 → 自动补发"
