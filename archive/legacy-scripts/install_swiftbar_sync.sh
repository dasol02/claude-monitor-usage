#!/bin/bash
# SwiftBar 자동 동기화 설치 스크립트

echo "=================================================="
echo "Claude Monitor - SwiftBar Auto-Sync 설치"
echo "=================================================="
echo ""

# 1. 자동 업데이트 스크립트 확인
if [ -f ~/.local/bin/claude-auto-update-usage ]; then
    echo "✅ Auto-update script already installed"
else
    echo "❌ Auto-update script not found"
    echo "   Run: chmod +x ~/.local/bin/claude-auto-update-usage"
    exit 1
fi

# 2. 다운로드 폴더 생성
mkdir -p ~/Downloads/.claude-monitor
echo "✅ Download folder created: ~/Downloads/.claude-monitor"

# 3. LaunchAgent 생성
PLIST_PATH=~/Library/LaunchAgents/com.claude.monitor.auto-sync.plist

cat > "$PLIST_PATH" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.claude.monitor.auto-sync</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/dasollee/.local/bin/claude-auto-update-usage</string>
    </array>

    <key>StartInterval</key>
    <integer>60</integer>

    <key>StandardOutPath</key>
    <string>/tmp/claude-auto-sync.log</string>

    <key>StandardErrorPath</key>
    <string>/tmp/claude-auto-sync-error.log</string>

    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF

echo "✅ LaunchAgent created: $PLIST_PATH"

# 4. LaunchAgent 로드
if launchctl list | grep -q "com.claude.monitor.auto-sync"; then
    echo "⏸️  Unloading existing LaunchAgent..."
    launchctl unload "$PLIST_PATH" 2>/dev/null
fi

echo "🚀 Loading LaunchAgent..."
launchctl load "$PLIST_PATH"

# 5. 확인
sleep 2
if launchctl list | grep -q "com.claude.monitor.auto-sync"; then
    echo "✅ LaunchAgent loaded successfully!"
else
    echo "❌ Failed to load LaunchAgent"
    exit 1
fi

echo ""
echo "=================================================="
echo "✨ 설치 완료!"
echo "=================================================="
echo ""
echo "📋 작동 방식:"
echo "   1. Chrome Extension이 usage 데이터 스크래핑 (5분마다)"
echo "   2. ~/Downloads/.claude-monitor/auto-usage.json에 저장"
echo "   3. LaunchAgent가 1분마다 파일 확인"
echo "   4. 파일 발견 시 자동으로 claude-calibrate 실행"
echo "   5. SwiftBar 자동 새로고침 → 업데이트된 값 표시"
echo ""
echo "🔍 로그 확인:"
echo "   tail -f /tmp/claude-auto-sync.log"
echo ""
echo "🛑 중단하려면:"
echo "   launchctl unload ~/Library/LaunchAgents/com.claude.monitor.auto-sync.plist"
echo ""
echo "🔄 다시 시작:"
echo "   launchctl load ~/Library/LaunchAgents/com.claude.monitor.auto-sync.plist"
echo ""
