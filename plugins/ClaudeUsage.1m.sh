#!/usr/bin/env bash
# <xbar.title>Claude Usage Monitor</xbar.title>
# <xbar.version>v2.0</xbar.version>
# <xbar.author>Claude Monitor</xbar.author>
# <xbar.author.github>your-github</xbar.author.github>
# <xbar.desc>Monitor Claude Code token usage with session and weekly limits</xbar.desc>
# <xbar.dependencies>python3,jq</xbar.dependencies>
# <xbar.abouturl>https://github.com/your-org/claude-monitor</xbar.abouturl>

# Refresh: 1 minute (1m)

USAGE_FILE="$HOME/.claude_usage.json"
CONFIG_FILE="$HOME/.claude-monitor/config.json"
MONITOR_SCRIPT="$HOME/.local/bin/claude-usage-monitor"
CONFIG_SCRIPT="$HOME/.local/bin/claude-config"

# JSON 파일 확인
if [[ ! -f "$USAGE_FILE" ]]; then
    echo "⚠️ No Data"
    echo "---"
    echo "Setup required | bash='$CONFIG_SCRIPT' terminal=true"
    echo "Install monitor | bash='echo Run install.sh first' terminal=false"
    exit 0
fi

# JSON 파싱
STATUS=$(jq -r '.status // "unknown"' "$USAGE_FILE" 2>/dev/null)

if [[ "$STATUS" != "active" ]]; then
    echo "💤 Idle"
    echo "---"
    echo "No active Claude session"
    echo "---"
    echo "⚙️ Settings"
    echo "--View config | bash='cat' param1='$CONFIG_FILE' terminal=true"
    echo "--Open usage JSON | bash='open' param1='$USAGE_FILE'"
    exit 0
fi

# 플랜 정보
PLAN_NAME=$(jq -r '.plan.name // "Unknown"' "$USAGE_FILE")

# Timezone 정보
TZ_ABBR=$(jq -r '.timezone_abbr // "UTC"' "$USAGE_FILE")

# 세션 데이터
SESSION_PCT=$(jq -r '.session.percentages.max_percentage // 0' "$USAGE_FILE")
SESSION_INPUT_PCT=$(jq -r '.session.percentages.input_percentage // 0' "$USAGE_FILE")
SESSION_OUTPUT_PCT=$(jq -r '.session.percentages.output_percentage // 0' "$USAGE_FILE")
SESSION_RESET=$(jq -r '.session.reset.time // "--:--"' "$USAGE_FILE")
SESSION_TIME_UNTIL=$(jq -r '.session.reset.time_until_reset.human_readable // "N/A"' "$USAGE_FILE")
SESSION_BAR=$(jq -r '.session.display.progress_bar // "[--% -----]"' "$USAGE_FILE")

SESSION_INPUT=$(jq -r '.session.usage.input_tokens // 0' "$USAGE_FILE")
SESSION_OUTPUT=$(jq -r '.session.usage.output_tokens // 0' "$USAGE_FILE")
SESSION_CACHE=$(jq -r '.session.usage.cache_creation_tokens // 0' "$USAGE_FILE")
SESSION_TOTAL=$(jq -r '.session.usage.total_counted_tokens // 0' "$USAGE_FILE")
SESSION_MESSAGES=$(jq -r '.session.usage.messages_count // 0' "$USAGE_FILE")

SESSION_INPUT_LIMIT=$(jq -r '.session.limits.input_tokens_per_minute // 0' "$USAGE_FILE")
SESSION_OUTPUT_LIMIT=$(jq -r '.session.limits.output_tokens_per_minute // 0' "$USAGE_FILE")
SESSION_WINDOW=$(jq -r '.session.limits.window_hours // 5' "$USAGE_FILE")

# 주간 데이터
WEEKLY_PCT=$(jq -r '.weekly.percentages.max_percentage // 0' "$USAGE_FILE")
WEEKLY_INPUT_PCT=$(jq -r '.weekly.percentages.input_percentage // 0' "$USAGE_FILE")
WEEKLY_OUTPUT_PCT=$(jq -r '.weekly.percentages.output_percentage // 0' "$USAGE_FILE")
WEEKLY_BAR=$(jq -r '.weekly.display.progress_bar // "[--% -----]"' "$USAGE_FILE")

WEEKLY_INPUT=$(jq -r '.weekly.usage.input_tokens // 0' "$USAGE_FILE")
WEEKLY_OUTPUT=$(jq -r '.weekly.usage.output_tokens // 0' "$USAGE_FILE")
WEEKLY_CACHE=$(jq -r '.weekly.usage.cache_creation_tokens // 0' "$USAGE_FILE")
WEEKLY_TOTAL=$(jq -r '.weekly.usage.total_counted_tokens // 0' "$USAGE_FILE")
WEEKLY_MESSAGES=$(jq -r '.weekly.usage.messages_count // 0' "$USAGE_FILE")

WEEKLY_INPUT_LIMIT=$(jq -r '.weekly.limits.input_tokens_per_minute // 0' "$USAGE_FILE")
WEEKLY_OUTPUT_LIMIT=$(jq -r '.weekly.limits.output_tokens_per_minute // 0' "$USAGE_FILE")

# 색상 결정 (세션 퍼센트 기준)
if (( $(echo "$SESSION_PCT < 50" | bc -l) )); then
    COLOR="green"
    ICON="🟢"
elif (( $(echo "$SESSION_PCT < 80" | bc -l) )); then
    COLOR="yellow"
    ICON="🟡"
else
    COLOR="red"
    ICON="🔴"
fi

# 메뉴바 출력 (세션 퍼센트 표시)
echo "$ICON ${SESSION_PCT}%"

# 드롭다운 메뉴
echo "---"

# 세션 사용량
echo "📊 Session (resets in $SESSION_TIME_UNTIL)"
printf -- "--Output: %s%% (%'d tokens) | color=%s\n" "$SESSION_OUTPUT_PCT" "$SESSION_OUTPUT" "$COLOR"
printf -- "--Input:  %s%% (%'d tokens)\n" "$SESSION_INPUT_PCT" "$SESSION_INPUT"
printf -- "--Messages: %'d\n" "$SESSION_MESSAGES"

echo "---"

# 주간 사용량
echo "📈 Weekly (7 days)"
printf -- "--Output: %s%% (%'d tokens)\n" "$WEEKLY_OUTPUT_PCT" "$WEEKLY_OUTPUT"
printf -- "--Input:  %s%% (%'d tokens)\n" "$WEEKLY_INPUT_PCT" "$WEEKLY_INPUT"
printf -- "--Messages: %'d\n" "$WEEKLY_MESSAGES"

echo "---"

echo "🔄 Actions"
echo "--Refresh now | refresh=true"
echo "--View config | bash='cat' param1='$CONFIG_FILE' terminal=true"
echo "--Open usage JSON | bash='open' param1='$USAGE_FILE'"
