#!/usr/bin/env bash
# <xbar.title>Claude Usage Monitor</xbar.title>
# <xbar.version>v3.0 - Web Extension Only</xbar.version>
# <xbar.author>Claude Monitor</xbar.author>
# <xbar.desc>Monitor Claude usage from Chrome Extension</xbar.desc>
# <xbar.dependencies>jq</xbar.dependencies>

# Web Extension 데이터 파일 (간단 버전)
USAGE_FILE="/tmp/claude-web-usage.json"

# 파일 확인
if [[ ! -f "$USAGE_FILE" ]]; then
    echo "⚠️ No Data"
    echo "---"
    echo "Chrome Extension not synced yet"
    echo "---"
    echo "📖 Instructions:"
    echo "--1. Open Chrome Extension"
    echo "--2. Click 'Scrape Now'"
    echo "--3. Wait 1-3 seconds"
    echo "---"
    echo "🔄 Manual sync | bash='$HOME/.local/bin/claude-sync-from-extension' terminal=true refresh=true"
    exit 0
fi

# JSON 파싱
SESSION=$(jq -r '.session.percentage // 0' "$USAGE_FILE" 2>/dev/null)
WEEKLY=$(jq -r '.weekly.percentage // 0' "$USAGE_FILE" 2>/dev/null)
LAST_UPDATED=$(jq -r '.timestamp // ""' "$USAGE_FILE" 2>/dev/null)

# 데이터 검증
if [ -z "$SESSION" ] || [ "$SESSION" == "0" ]; then
    echo "⚠️ Invalid Data"
    echo "---"
    echo "Click to resync | bash='$HOME/.local/bin/claude-sync-from-extension' terminal=true refresh=true"
    exit 0
fi

# 색상 결정 (Session 기준)
if (( $(echo "$SESSION < 50" | bc -l) )); then
    ICON="🟢"
    COLOR="green"
elif (( $(echo "$SESSION < 80" | bc -l) )); then
    ICON="🟡"
    COLOR="yellow"
else
    ICON="🔴"
    COLOR="red"
fi

# 메뉴바 표시
echo "$ICON ${SESSION}%"

# 드롭다운 메뉴
echo "---"

# Session 정보
echo "📊 Session Usage"
printf -- "--Current: %s%% | color=%s\n" "$SESSION" "$COLOR"
echo "--Source: Chrome Extension"

echo "---"

# Weekly 정보
echo "📈 Weekly Usage"
printf -- "--Current: %s%%\n" "$WEEKLY"
echo "--Source: Chrome Extension"

echo "---"

# Last Update
if [ -n "$LAST_UPDATED" ]; then
    # ISO timestamp를 Mac 로컬 시간으로 변환
    # 먼저 초 단위로 변환 (UTC 기준)
    UTC_SECONDS=$(date -j -u -f "%Y-%m-%dT%H:%M:%SZ" "$LAST_UPDATED" "+%s" 2>/dev/null)
    if [ -n "$UTC_SECONDS" ]; then
        # Unix timestamp를 로컬 시간으로 표시
        READABLE_TIME=$(date -r "$UTC_SECONDS" "+%m/%d %H:%M")
    else
        READABLE_TIME="Unknown"
    fi
    echo "🕐 Last Updated: $READABLE_TIME"
    echo "---"
fi


# Instructions
echo "📖 How to Update"
echo "--1. Chrome Extension → 'Scrape Now'"
echo "--2. Wait 1-3 seconds (auto-sync)"
echo "--3. SwiftBar updates automatically"

echo "---"

# Data source indicator
echo "📡 Data Source"
echo "--Chrome Extension (Web Scraping)"
echo "--File: /tmp/claude-web-usage.json"
echo "--Auto-sync: Enabled ✅"
