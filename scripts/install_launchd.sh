#!/usr/bin/env bash
# Install macOS LaunchAgents: 08:00 schedule + login catch-up after sleep.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AGENTS="$HOME/Library/LaunchAgents"
BIN_DIR="${HOME}/.local/bin"
LAUNCHER="${BIN_DIR}/ai-daily-brief-run"
chmod +x "$ROOT/scripts/run_daily.sh"

mkdir -p "$BIN_DIR"
cat > "$LAUNCHER" <<EOF
#!/bin/bash
export TZ=Asia/Shanghai
exec "${ROOT}/scripts/run_daily.sh" "\$@"
EOF
chmod +x "$LAUNCHER"

# 生成 plist（使用 launcher 路径）
gen_plist() {
  local label="$1" mode="$2" run_at_load="$3" outlog="$4" errlog="$5"
  cat > "$AGENTS/${label}.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${LAUNCHER}</string>
    <string>${mode}</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>TZ</key>
    <string>Asia/Shanghai</string>
  </dict>
  <key>RunAtLoad</key>
  <${run_at_load}/>
  <key>StandardOutPath</key>
  <string>${outlog}</string>
  <key>StandardErrorPath</key>
  <string>${errlog}</string>
</dict>
</plist>
EOF
}

mkdir -p "$ROOT/logs"
gen_plist "com.ai.daily-brief" "scheduled" "false" \
  "$ROOT/logs/launchd.out.log" "$ROOT/logs/launchd.err.log"

# 8:00 每天
/usr/libexec/PlistBuddy -c "Add :StartCalendarInterval dict" "$AGENTS/com.ai.daily-brief.plist" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :StartCalendarInterval:Hour integer 8" "$AGENTS/com.ai.daily-brief.plist"
/usr/libexec/PlistBuddy -c "Add :StartCalendarInterval:Minute integer 0" "$AGENTS/com.ai.daily-brief.plist"

gen_plist "com.ai.daily-brief.login" "login" "true" \
  "$ROOT/logs/launchd-login.out.log" "$ROOT/logs/launchd-login.err.log"

launchctl bootout "gui/$(id -u)/com.ai.daily-brief" 2>/dev/null || true
launchctl bootout "gui/$(id -u)/com.ai.daily-brief.login" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$AGENTS/com.ai.daily-brief.plist"
launchctl bootstrap "gui/$(id -u)" "$AGENTS/com.ai.daily-brief.login.plist"

echo "LaunchAgents installed (launcher: ${LAUNCHER})"
launchctl print "gui/$(id -u)/com.ai.daily-brief" 2>/dev/null | head -5 || launchctl list | grep daily-brief
echo ""
echo "  • 每天 08:00（Mac 醒着时）"
echo "  • 登录补跑：8 点后开机且今天还没发过 → 自动补发"
echo ""
echo "⚠️  项目在桌面时，请到：系统设置 → 隐私与安全性 → 完全磁盘访问权限"
echo "    添加 ${LAUNCHER}（或 /bin/bash），否则 launchd 会报 Operation not permitted"
echo "    更推荐：bash scripts/install_crontab.sh（用户 crontab，通常更稳）"
