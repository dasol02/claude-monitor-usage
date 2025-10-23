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
# 캘리브레이션이 활성화되어 있으면 calibrated 값 사용, 아니면 원본 사용
CALIBRATION_ENABLED=$(jq -r '.calibration.enabled // false' "$USAGE_FILE")
SESSION_ORIGINAL_MAX=$(jq -r '.session.percentages.max_percentage // 0' "$USAGE_FILE")
SESSION_ORIGINAL_INPUT=$(jq -r '.session.percentages.input_percentage // 0' "$USAGE_FILE")
SESSION_ORIGINAL_OUTPUT=$(jq -r '.session.percentages.output_percentage // 0' "$USAGE_FILE")

if [[ "$CALIBRATION_ENABLED" == "true" ]]; then
    CALIBRATED_PCT=$(jq -r '.calibration.info.calibrated_percentage // null' "$USAGE_FILE")
    if [[ "$CALIBRATED_PCT" != "null" ]] && [[ "$SESSION_ORIGINAL_MAX" != "0" ]]; then
        # Calibration 비율 계산
        CALIB_RATIO=$(echo "scale=6; $CALIBRATED_PCT / $SESSION_ORIGINAL_MAX" | bc)
        SESSION_PCT="$CALIBRATED_PCT"
        SESSION_INPUT_PCT=$(printf "%.1f" $(echo "$SESSION_ORIGINAL_INPUT * $CALIB_RATIO" | bc))
        SESSION_OUTPUT_PCT=$(printf "%.1f" $(echo "$SESSION_ORIGINAL_OUTPUT * $CALIB_RATIO" | bc))
    else
        SESSION_PCT="$SESSION_ORIGINAL_MAX"
        SESSION_INPUT_PCT="$SESSION_ORIGINAL_INPUT"
        SESSION_OUTPUT_PCT="$SESSION_ORIGINAL_OUTPUT"
    fi
else
    SESSION_PCT="$SESSION_ORIGINAL_MAX"
    SESSION_INPUT_PCT="$SESSION_ORIGINAL_INPUT"
    SESSION_OUTPUT_PCT="$SESSION_ORIGINAL_OUTPUT"
fi
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
# 캘리브레이션이 활성화되어 있으면 calibrated 값 사용, 아니면 원본 사용
WEEKLY_ORIGINAL_MAX=$(jq -r '.weekly.percentages.max_percentage // 0' "$USAGE_FILE")
WEEKLY_ORIGINAL_INPUT=$(jq -r '.weekly.percentages.input_percentage // 0' "$USAGE_FILE")
WEEKLY_ORIGINAL_OUTPUT=$(jq -r '.weekly.percentages.output_percentage // 0' "$USAGE_FILE")

if [[ "$CALIBRATION_ENABLED" == "true" ]]; then
    WEEKLY_CALIBRATED_PCT=$(jq -r '.calibration.weekly.calibrated_percentage // null' "$USAGE_FILE")
    if [[ "$WEEKLY_CALIBRATED_PCT" != "null" ]] && [[ "$WEEKLY_ORIGINAL_MAX" != "0" ]]; then
        # Calibration 비율 계산
        WEEKLY_CALIB_RATIO=$(echo "scale=6; $WEEKLY_CALIBRATED_PCT / $WEEKLY_ORIGINAL_MAX" | bc)
        WEEKLY_PCT="$WEEKLY_CALIBRATED_PCT"
        WEEKLY_INPUT_PCT=$(printf "%.1f" $(echo "$WEEKLY_ORIGINAL_INPUT * $WEEKLY_CALIB_RATIO" | bc))
        WEEKLY_OUTPUT_PCT=$(printf "%.1f" $(echo "$WEEKLY_ORIGINAL_OUTPUT * $WEEKLY_CALIB_RATIO" | bc))
    else
        WEEKLY_PCT="$WEEKLY_ORIGINAL_MAX"
        WEEKLY_INPUT_PCT="$WEEKLY_ORIGINAL_INPUT"
        WEEKLY_OUTPUT_PCT="$WEEKLY_ORIGINAL_OUTPUT"
    fi
else
    WEEKLY_PCT="$WEEKLY_ORIGINAL_MAX"
    WEEKLY_INPUT_PCT="$WEEKLY_ORIGINAL_INPUT"
    WEEKLY_OUTPUT_PCT="$WEEKLY_ORIGINAL_OUTPUT"
fi
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
printf -- "--Max: %s%%\n" "$SESSION_PCT"
printf -- "--Output: %s%% (%'d tokens) | color=%s\n" "$SESSION_OUTPUT_PCT" "$SESSION_OUTPUT" "$COLOR"
printf -- "--Input:  %s%% (%'d tokens)\n" "$SESSION_INPUT_PCT" "$SESSION_INPUT"
printf -- "--Messages: %'d\n" "$SESSION_MESSAGES"

echo "---"

# 주간 사용량
echo "📈 Weekly (7 days)"
printf -- "--Max: %s%%\n" "$WEEKLY_PCT"
printf -- "--Output: %s%% (%'d tokens)\n" "$WEEKLY_OUTPUT_PCT" "$WEEKLY_OUTPUT"
printf -- "--Input:  %s%% (%'d tokens)\n" "$WEEKLY_INPUT_PCT" "$WEEKLY_INPUT"
printf -- "--Messages: %'d\n" "$WEEKLY_MESSAGES"

echo "---"

echo "🔄 Actions"
echo "--Refresh now | refresh=true"
echo "--Calibrate usage | bash='$HOME/.local/bin/claude-calibrate-prompt' terminal=true refresh=true"
echo "--View config | bash='cat' param1='$CONFIG_FILE' terminal=true"
echo "--Open usage JSON | bash='open' param1='$USAGE_FILE'"
echo "---"
echo "📚 Calibration Status"
CALIB_STATUS=$(jq -r '.calibration.session.status // "no_data"' "$USAGE_FILE")
CALIB_ORIGINAL=$(jq -r '.calibration.session.original_percentage // 0' "$USAGE_FILE")
CALIB_ADJUSTED=$(jq -r '.calibration.session.calibrated_percentage // 0' "$USAGE_FILE")
CALIB_WINDOW=$(jq -r '.calibration.session.window_key // "unknown"' "$USAGE_FILE")
CALIB_LIMIT=$(jq -r '.calibration.session.learned_limit // 0' "$USAGE_FILE")

if [[ "$CALIB_STATUS" == "override" ]]; then
    echo "--Session: ⭐ Override (${CALIB_ADJUSTED}%)"
    echo "--  Window: ${CALIB_WINDOW}"
    if [[ "$CALIB_LIMIT" != "0" ]] && [[ "$CALIB_LIMIT" != "null" ]]; then
        echo "--  Learned limit: ${CALIB_LIMIT} TPM"
    fi
    echo "--  Original: ${CALIB_ORIGINAL}%"
elif [[ "$CALIB_STATUS" == "calibrated" ]]; then
    echo "--Session: ✅ Calibrated (${CALIB_ADJUSTED}%)"
    echo "--  Window: ${CALIB_WINDOW}"
elif [[ "$CALIB_STATUS" == "learning" ]]; then
    echo "--Session: 📚 Learning (${CALIB_ADJUSTED}%)"
    echo "--  Window: ${CALIB_WINDOW}"
else
    echo "--Session: ⚠️ No calibration"
fi

# Weekly calibration status
WEEKLY_STATUS=$(jq -r '.calibration.weekly.status // "no_data"' "$USAGE_FILE")
WEEKLY_ADJUSTED=$(jq -r '.calibration.weekly.calibrated_percentage // 0' "$USAGE_FILE")
if [[ "$WEEKLY_STATUS" == "override" ]]; then
    echo "--Weekly: ⭐ Override (${WEEKLY_ADJUSTED}%)"
elif [[ "$WEEKLY_STATUS" != "no_data" ]]; then
    echo "--Weekly: ${WEEKLY_ADJUSTED}%"
fi
echo "---"
echo "⏰ Session Reset Time"
if [[ -f "$CONFIG_FILE" ]]; then
    BASE_HOUR=$(jq -r '.reset_schedule.session_base_hour // 14' "$CONFIG_FILE")
    RESET_HOUR=$((($BASE_HOUR + 5) % 24))
    printf -- "--Current: %02d:00\n" $RESET_HOUR
    echo "--Set reset time | bash='$HOME/.local/bin/claude-set-session-resets-prompt' terminal=true refresh=true"
else
    echo "--Config not found"
fi

echo "---"
echo "🚪 Activity Tracking"

# Load activity data
ACTIVITY_FILE="$HOME/.claude-monitor/activity_data.json"

if [[ -f "$ACTIVITY_FILE" ]] && [[ -s "$ACTIVITY_FILE" ]]; then
    # Check if today's data
    TODAY=$(date +"%Y-%m-%d")
    STORED_DATE=$(jq -r '.today // ""' "$ACTIVITY_FILE" 2>/dev/null)

    if [[ "$STORED_DATE" == "$TODAY" ]]; then
        BREAK_COUNT=$(jq -r '.break_count // 0' "$ACTIVITY_FILE")
        TOTAL_MINUTES=$(jq -r '.total_minutes // 0' "$ACTIVITY_FILE")
        CURRENT_STATUS=$(jq -r '.current_status // "in"' "$ACTIVITY_FILE")
        CURRENT_OUT_TIME=$(jq -r '.current_out_time // null' "$ACTIVITY_FILE")

        # Show status
        if [[ "$CURRENT_STATUS" == "out" ]]; then
            if [[ "$CURRENT_OUT_TIME" != "null" ]]; then
                # Calculate how long out
                OUT_DURATION=$(python3 -c "
from datetime import datetime
try:
    dt_out = datetime.fromisoformat('$CURRENT_OUT_TIME'.replace('Z', '+00:00'))
    now = datetime.now(dt_out.tzinfo)
    duration_seconds = (now - dt_out).total_seconds()
    duration_minutes = round(duration_seconds / 60)
    print(duration_minutes)
except:
    print(0)
" 2>/dev/null || echo 0)
                echo "--Status: 🚪 OUT (${OUT_DURATION} min ago)"
            else
                echo "--Status: 🚪 OUT"
            fi
        else
            echo "--Status: ✅ IN"
        fi

        # Show summary
        if [[ $TOTAL_MINUTES -ge 60 ]]; then
            HOURS=$((TOTAL_MINUTES / 60))
            MINS=$((TOTAL_MINUTES % 60))
            echo "--Today: $BREAK_COUNT breaks (${HOURS}h ${MINS}m)"
        else
            echo "--Today: $BREAK_COUNT breaks (${TOTAL_MINUTES}m)"
        fi

        # Action buttons
        if [[ "$CURRENT_STATUS" == "out" ]]; then
            echo "--✅ Record In | bash='$HOME/.local/bin/activity-in' terminal=false refresh=true"
            echo "--⏱️ Quick In (5min) | bash='$HOME/.local/bin/activity-quick' terminal=false refresh=true"
        else
            echo "--🚪 Record Out | bash='$HOME/.local/bin/activity-out' terminal=false refresh=true"
            echo "--⏱️ Quick +5min | bash='$HOME/.local/bin/activity-quick' terminal=false refresh=true"
        fi
        echo "--📊 View history | bash='$HOME/.local/bin/activity-status' terminal=true"
    else
        # Old data or new day
        echo "--No data today"
        echo "--🚪 Record Out | bash='$HOME/.local/bin/activity-out' terminal=false refresh=true"
        echo "--⏱️ Quick +5min | bash='$HOME/.local/bin/activity-quick' terminal=false refresh=true"
        echo "--📊 View history | bash='$HOME/.local/bin/activity-status' terminal=true"
    fi
else
    # No data file
    echo "--No activity tracked yet"
    echo "--🚪 Record Out | bash='$HOME/.local/bin/activity-out' terminal=false refresh=true"
    echo "--⏱️ Quick +5min | bash='$HOME/.local/bin/activity-quick' terminal=false refresh=true"
    echo "--📊 View history | bash='$HOME/.local/bin/activity-status' terminal=true"
fi
