# Claude Monitor 세션 복원 가이드

**최종 업데이트**: 2025-10-17 KST
**목적**: 개발 세션 중단 시 현재 상태를 빠르게 이해하고 작업 재개

---

## 📋 현재 프로젝트 상태

### 구현 완료된 기능
- ✅ **Override 메커니즘 (세션 + 주간)** - 즉시 반영 + 실시간 토큰 계산
- ✅ **토큰 역산으로 Limit 학습** - Output limit 기준
- ✅ **세션별 시간 윈도우 관리** - Config 기반 5시간 윈도우
- ✅ **주간 사용량 Calibration** - 세션과 동일한 메커니즘
- ✅ **세션 리셋 시간 설정** - CLI & SwiftBar 버튼 (자동 재시작/갱신)
- ✅ **SwiftBar Max 항목 표시** - 세션/주간 모두 calibrated 값 표시
- ✅ **SwiftBar 자동 갱신** - Calibration + Reset Time UI
- ✅ **Global Fallback Limit** - 세션 간 학습 데이터 공유로 초기 정확도 향상

### 최근 개선사항 (2025-10-16 ~ 2025-10-17)
1. **주간 사용량 Override** (2025-10-16) - 세션과 동일하게 learned_limit 기반 실시간 계산
2. **SwiftBar Max 항목** (2025-10-16) - 세션/주간 드롭다운에 Max 라인 추가
3. **독립적인 윈도우 관리** (2025-10-16) - 세션(5시간), 주간(7일) 각각 독립 override
4. **Global Fallback Limit** (2025-10-17) - 다른 세션의 learned limit을 가중 평균하여 fallback
5. **자동 재시작/갱신** (2025-10-17) - 세션 리셋 시간 변경 시 자동 데몬 재시작 및 SwiftBar 갱신
6. **Legacy 모듈 제거** (2025-10-17) - limit_learner.py 제거, calibration_learner.py만 사용

---

## 🗂️ 프로젝트 구조

```
/Users/dasollee/claude-monitor/
├── src/
│   ├── monitor_daemon.py          # 메인 모니터링 데몬 (legacy 제거됨)
│   └── calibration_learner.py     # Calibration 시스템 (global fallback 포함)
├── plugins/
│   └── ClaudeUsage.1m.sh          # SwiftBar 플러그인
├── config.json                    # 설정 파일
├── README.md                      # 메인 문서
├── docs/
│   ├── SESSION_RESTORE.md         # (현재 파일)
│   ├── LOGIC_PRIORITY.md          # Override + Fallback 로직 설명
│   └── SESSION_RESET_TIME.md      # 리셋 시간 설정 가이드 (자동화)
└── archive/                       # 레거시 문서 및 코드
    ├── limit_learner.py           # 레거시 모듈 (미사용)
    ├── OVERRIDE_DESIGN.md
    ├── PERCENTAGE_CALC.md
    └── USAGE.md

/Users/dasollee/.local/bin/
├── claude-usage-monitor           # 모니터 실행 스크립트
├── claude-calibrate               # Calibration 래퍼 (SwiftBar 갱신)
├── claude-calibrate-prompt        # 인터랙티브 프롬프트
├── claude-set-session-resets      # 세션 리셋 시간 설정
├── claude-set-session-resets-prompt  # 리셋 시간 인터랙티브
└── calibration_learner.py         # Calibration 스크립트 (복사본)

/Users/dasollee/.claude-monitor/
└── calibration_data.json          # Calibration 학습 데이터

/Users/dasollee/.claude_usage.json # 모니터 출력 (SwiftBar가 읽음)

~/Library/Application Support/SwiftBar/
└── ClaudeUsage.1m.sh              # SwiftBar 플러그인 (실제 위치)
```

---

## 🔑 핵심 컴포넌트

### 1. monitor_daemon.py
**역할**: Claude Code 로그를 모니터링하고 사용량 계산

**핵심 로직** (Line 553-604):
```python
# Calibration 적용 (세션)
if CALIBRATION_ENABLED:
    window_key = get_session_window_key(session_start)
    monitor_value = session_percentages['max_percentage'] / 100.0
    calibration = get_calibrated_value(monitor_value, window_key)

    session_calibration_info = {...}
    if calibration['status'] in ['override', 'calibrated', 'learning']:
        session_display_percentage = calibration_info['calibrated_percentage']

# Calibration 적용 (주간)
if CALIBRATION_ENABLED:
    weekly_window_key = get_weekly_window_key()
    weekly_monitor_value = weekly_percentages['max_percentage'] / 100.0
    weekly_calibration = get_calibrated_value(weekly_monitor_value, weekly_window_key)

    weekly_calibration_info = {...}
    if weekly_calibration['status'] in ['override', 'calibrated', 'learning']:
        weekly_display_percentage = weekly_calibration_info['calibrated_percentage']
```

**실행 방법**:
```bash
# 1회 실행
python3 src/monitor_daemon.py --once

# 데몬 모드 (60초마다 자동 실행)
~/.local/bin/claude-usage-monitor
```

---

### 2. calibration_learner.py
**역할**: Calibration 데이터 학습 및 Override 관리

**주요 함수**:

#### `get_calibrated_value(monitor_value, window_key)`
**우선순위**:
1. **Override** (최우선) - 세션/주간 종료 시까지 고정 기준
2. **Calibrated** - 샘플 5개 이상 학습 완료
3. **Learning** - 샘플 1~4개 학습 중
4. **Learning with Fallback** (신규) - 샘플 < 3개, global fallback limit 사용
5. **No Data** - 샘플 없음, 원본값 사용

```python
# 1. Override 확인 (만료 여부 체크)
if 'latest_override' in data[window_key]:
    if now < expires_at:
        # Learned limit으로 실시간 계산
        if window_key == "weekly":
            output_total = usage_data['weekly']['usage']['output_tokens']
            window_minutes = 7 * 24 * 60  # 7일
        else:
            output_total = usage_data['session']['usage']['output_tokens']
            window_minutes = 300  # 5시간

        calibrated_pct = (output_total / (learned_limit * window_minutes)) * 100
        return {'status': 'override', 'calibrated_value': calibrated_pct / 100}

# 2. 샘플 < 3개: Global fallback limit 시도
if sample_count < 3:
    fallback_limit = get_global_fallback_limit()
    if fallback_limit and window_key != "weekly":
        # Fallback limit으로 실시간 계산
        output_total = usage_data['session']['usage']['output_tokens']
        calibrated_pct = (output_total / (fallback_limit * 300)) * 100
        return {'status': 'learning_with_fallback', 'calibrated_value': calibrated_pct / 100, 'confidence': 0.5}

# 3. 모델 기반 보정
if model and sample_count >= 3:
    if has_limit_learning:
        # Limit 기반 계산
        return {'status': 'learning' or 'calibrated', 'calibrated_value': model_value}
    else:
        # Limit learning 없음: Global fallback 시도
        fallback_limit = get_global_fallback_limit()
        if fallback_limit and window_key != "weekly":
            return {'status': 'fallback_limit', 'calibrated_value': ..., 'confidence': 0.5}

# 4. 데이터 없음
return {'status': 'no_data', 'calibrated_value': monitor_value}
```

#### `set_calibration_override(window_key, calibrated_pct, learned_limit, expires_at)`
**목적**: 사용자 입력값을 즉시 반영

```python
data[window_key]['latest_override'] = {
    'timestamp': '2025-10-16T16:40:00+09:00',
    'calibrated_percentage': 35.0,
    'expires_at': '2025-10-16T19:00:00+09:00',  # 세션 끝 or 주간 +7일
    'learned_limit': 1269  # Output TPM
}
```

#### `reverse_calculate_limit(actual_percentage, current_tokens, window_minutes)`
**목적**: 실제 퍼센트로 API Limit 역산

**공식**:
```
limit_tpm = current_tokens / (actual_percentage / 100) / window_minutes

예시 (세션):
- 현재 토큰: 131,259 (output)
- 실제 %: 35.0%
- 윈도우: 300분 (5시간)
→ limit = 131,259 / 0.35 / 300 = 1,250 TPM

예시 (주간):
- 현재 토큰: 956,661 (output)
- 실제 %: 56.0%
- 윈도우: 10,080분 (7일)
→ limit = 956,661 / 0.56 / 10,080 = 169 TPM
```

#### `get_window_end_time(window_key)`
**목적**: 세션/주간 종료 시간 계산 (Override 만료 시점)

```python
if window_key == "weekly":
    return now + timedelta(days=7)  # 7일 후
else:
    # 세션 윈도우 종료 시간 (예: 19:00)
    return window_end
```

**실행 방법**:
```bash
# 세션만 calibrate
claude-calibrate 35

# 세션 + 주간 calibrate
claude-calibrate 35 56

# 상태 확인
claude-calibrate --status

# 히스토리 조회
claude-calibrate --history
```

---

### 3. claude-calibrate (래퍼 스크립트)
**위치**: `/Users/dasollee/.local/bin/claude-calibrate`

**역할**: calibration_learner.py 실행 + SwiftBar 갱신

**핵심 로직**:
```bash
# 1. Calibration 실행
python3 ~/.local/bin/calibration_learner.py "$@"
EXIT_CODE=$?

# 2. 성공 시 모니터 갱신 + SwiftBar 새로고침
if [ $EXIT_CODE -eq 0 ] && [ -n "$1" ] && [[ ! "$1" =~ ^-- ]]; then
    ~/.local/bin/claude-usage-monitor --once > /dev/null 2>&1
    open "swiftbar://refreshallplugins" 2>/dev/null
fi
```

---

### 4. ClaudeUsage.1m.sh (SwiftBar 플러그인)
**위치**: `~/Library/Application Support/SwiftBar/ClaudeUsage.1m.sh`

**역할**: 1분마다 `~/.claude_usage.json` 읽어서 메뉴바 표시

**표시 로직** (Line 48-91):
```bash
# 세션 Calibration 값 사용
CALIBRATION_ENABLED=$(jq -r '.calibration.enabled // false' "$USAGE_FILE")
if [[ "$CALIBRATION_ENABLED" == "true" ]]; then
    CALIBRATED_PCT=$(jq -r '.calibration.session.calibrated_percentage // null' "$USAGE_FILE")
    if [[ "$CALIBRATED_PCT" != "null" ]]; then
        SESSION_PCT="$CALIBRATED_PCT"  # ← Override/Calibrated 값
    fi
fi

# 주간 Calibration 값 사용
if [[ "$CALIBRATION_ENABLED" == "true" ]]; then
    WEEKLY_CALIBRATED_PCT=$(jq -r '.calibration.weekly.calibrated_percentage // null' "$USAGE_FILE")
    if [[ "$WEEKLY_CALIBRATED_PCT" != "null" ]]; then
        WEEKLY_PCT="$WEEKLY_CALIBRATED_PCT"  # ← Override/Calibrated 값
    fi
fi
```

**드롭다운 출력** (Line 120-134):
```bash
# 세션 사용량
echo "📊 Session (resets in $SESSION_TIME_UNTIL)"
printf -- "--Max: %s%%\n" "$SESSION_PCT"              # ← Calibrated 값
printf -- "--Output: %s%% (%'d tokens)\n" "$SESSION_OUTPUT_PCT" "$SESSION_OUTPUT"
printf -- "--Input:  %s%% (%'d tokens)\n" "$SESSION_INPUT_PCT" "$SESSION_INPUT"

# 주간 사용량
echo "📈 Weekly (7 days)"
printf -- "--Max: %s%%\n" "$WEEKLY_PCT"               # ← Calibrated 값
printf -- "--Output: %s%% (%'d tokens)\n" "$WEEKLY_OUTPUT_PCT" "$WEEKLY_OUTPUT"
printf -- "--Input:  %s%% (%'d tokens)\n" "$WEEKLY_INPUT_PCT" "$WEEKLY_INPUT"
```

---

## 🔄 데이터 플로우

### A. 정상 모니터링 플로우
```
[Claude Code 로그]
~/.cache/claude/logs/claude-desktop.log
        ↓
[monitor_daemon.py]
- 최근 5시간/7일 토큰 합산
- 퍼센트 계산: tokens / (limit * window_minutes) * 100
        ↓
[calibration_learner.py]
- get_calibrated_value() 호출 (세션 + 주간)
- Override > Model > Raw 순서로 값 선택
        ↓
[~/.claude_usage.json]
{
  "calibration": {
    "session": {"status": "override", "calibrated_percentage": 35.4},
    "weekly": {"status": "override", "calibrated_percentage": 56.2}
  }
}
        ↓
[SwiftBar Plugin]
- 1분마다 JSON 읽기
- 메뉴바에 🟢 35.4% 표시
- 드롭다운에 Max 항목 표시
```

### B. Calibration 플로우
```
[사용자]
claude-calibrate 35 56
        ↓
[calibration_learner.py]
1. 세션: 현재 모니터 값 읽기
2. 세션: 토큰 역산 → Limit 학습
3. 세션: Override 설정 (35%, 만료: 19:00)
4. 주간: 현재 모니터 값 읽기
5. 주간: 토큰 역산 → Limit 학습
6. 주간: Override 설정 (56%, 만료: +7일)
        ↓
[~/.claude-monitor/calibration_data.json]
{
  "14:00-19:00": {
    "latest_override": {
      "calibrated_percentage": 35.0,
      "learned_limit": 1250,
      "expires_at": "2025-10-16T19:00:00+09:00"
    }
  },
  "weekly": {
    "latest_override": {
      "calibrated_percentage": 56.0,
      "learned_limit": 169,
      "expires_at": "2025-10-23T16:40:00+09:00"
    }
  }
}
        ↓
[claude-calibrate 스크립트]
- monitor_daemon.py --once 실행
- SwiftBar 새로고침
        ↓
[SwiftBar]
🟢 35.4% 즉시 표시
드롭다운: Max 35.4%, Max 56.2%
```

---

## 🎯 주요 명령어

### 모니터링
```bash
# 현재 사용량 확인 (1회)
python3 src/monitor_daemon.py --once | jq '.session.percentages'

# JSON 전체 확인
cat ~/.claude_usage.json | jq .

# Calibration 상태
cat ~/.claude_usage.json | jq '.calibration'

# Daemon 상태 확인
ps aux | grep claude-usage-monitor
```

### Calibration
```bash
# 세션만 (Claude /usage에서 Session Output 확인)
claude-calibrate 35

# 세션 + 주간
claude-calibrate 35 56

# 상태 확인
claude-calibrate --status

# 히스토리 조회
claude-calibrate --history

# 특정 윈도우 히스토리
claude-calibrate --history 14:00-19:00
claude-calibrate --history weekly
```

### 세션 리셋 시간 설정
```bash
# 현재 리셋 시간 확인
claude-set-session-resets

# 리셋 시간 변경 (예: 20시) - 자동으로 데몬 재시작 및 SwiftBar 갱신
claude-set-session-resets 20

# 수동 재시작 (필요 시만)
killall claude-usage-monitor
~/.local/bin/claude-usage-monitor &

# 수동 새로고침 (필요 시만)
open "swiftbar://refreshallplugins"
```

**참고**: `claude-set-session-resets` 명령어는 자동으로 데몬을 재시작하고 SwiftBar를 갱신합니다 (2025-10-17 업데이트).

### 데이터 관리
```bash
# Override 확인
cat ~/.claude-monitor/calibration_data.json | jq '.["14:00-19:00"].latest_override'
cat ~/.claude-monitor/calibration_data.json | jq '.weekly.latest_override'

# 전체 윈도우 확인
cat ~/.claude-monitor/calibration_data.json | jq 'keys'
```

---

## 🔧 문제 해결

### 1. SwiftBar에 Max 항목이 안 보임
```bash
# 플러그인 파일 확인
bash ~/Library/Application\ Support/SwiftBar/ClaudeUsage.1m.sh | head -20

# SwiftBar 재시작
killall SwiftBar && open -a SwiftBar
```

### 2. Calibration이 적용 안 됨
```bash
# 1. Calibration 활성화 확인
cat ~/.claude_usage.json | jq '.calibration.enabled'
# → true

# 2. Override 만료 확인
cat ~/.claude-monitor/calibration_data.json | jq '.["14:00-19:00"].latest_override.expires_at'

# 3. 세션/주간 calibration 정보 확인
cat ~/.claude_usage.json | jq '.calibration.session'
cat ~/.claude_usage.json | jq '.calibration.weekly'

# 4. Daemon 재시작
killall claude-usage-monitor
~/.local/bin/claude-usage-monitor &
```

### 3. 주간 사용량이 이상함
```bash
# 현재 주간 토큰 확인
cat ~/.claude_usage.json | jq '.weekly.usage.output_tokens'

# 주간 override 확인
cat ~/.claude-monitor/calibration_data.json | jq '.weekly.latest_override'

# 수동으로 재계산
cat ~/.claude_usage.json | jq '{
  output_tokens: .weekly.usage.output_tokens,
  learned_limit: 169,
  window_minutes: (7 * 24 * 60),
  calculated_pct: (.weekly.usage.output_tokens / (169 * 10080) * 100)
}'
```

### 4. Daemon이 여러 개 실행됨
```bash
# 모든 daemon 확인
ps aux | grep claude-usage-monitor

# 모두 종료
killall -9 claude-usage-monitor

# 단일 daemon만 실행
~/.local/bin/claude-usage-monitor &
```

---

## 📊 현재 학습 데이터 예시

### 세션 윈도우: 14:00-19:00
```json
{
  "14:00-19:00": {
    "latest_override": {
      "timestamp": "2025-10-16T16:40:00+09:00",
      "calibrated_percentage": 35.0,
      "expires_at": "2025-10-16T19:00:00+09:00",
      "learned_limit": 1250
    },
    "history": [...]
  }
}
```

### 주간 윈도우
```json
{
  "weekly": {
    "latest_override": {
      "timestamp": "2025-10-16T16:40:00+09:00",
      "calibrated_percentage": 56.0,
      "expires_at": "2025-10-23T16:40:00+09:00",
      "learned_limit": 169
    },
    "history": [...]
  }
}
```

---

## 🎓 이해해야 할 핵심 개념

### 1. Percentage 계산 방식

**세션 (Output 기준)**:
```
percentage = (output_tokens / (learned_limit × 300분)) × 100
learned_limit = output_tokens / (actual_percentage / 100) / 300
```

**주간 (Output 기준)**:
```
percentage = (output_tokens / (learned_limit × 10,080분)) × 100
learned_limit = output_tokens / (actual_percentage / 100) / 10,080
```

### 2. Override vs Model

**Override**:
- 사용자가 직접 입력한 값 (Claude /usage UI 참고)
- 세션/주간 종료 시까지 learned_limit 유지
- 100% 신뢰도
- 즉시 반영
- 실시간 토큰 계산

**Model**:
- 여러 샘플로 학습한 보정 모델
- 샘플 1개부터 적용
- 샘플 5개 이상이면 "calibrated" 상태
- Override가 없을 때 사용

### 3. 세션/주간 윈도우

**세션 (고정 5시간 블록)**:
- 09:00-14:00
- 14:00-19:00
- 19:00-00:00
- 00:00-04:00
- 04:00-09:00

**주간 (7일 rolling)**:
- 현재 시간부터 정확히 7일 전
- Override 만료: 입력 시점 + 7일

---

## 🚀 빠른 시작 (세션 복원)

### 1. 현재 상태 파악
```bash
# 1. 모니터 값 확인
cat ~/.claude_usage.json | jq '{
  session: .calibration.session.calibrated_percentage,
  weekly: .calibration.weekly.calibrated_percentage
}'

# 2. Calibration 상태 확인
claude-calibrate --status

# 3. 세션 리셋 시간 확인
claude-set-session-resets
```

### 2. Claude /usage UI와 비교
1. Claude Code 실행
2. `/usage` 명령어 입력
3. **"Session Output" 값 확인** (예: 35%)
4. **"Weekly Output" 값 확인** (예: 56%)
5. **"Resets at" 시간 확인** (예: 19:00 KST)

### 3. 리셋 시간 불일치 시 조정
```bash
# Claude /usage UI: "Resets at 20:00"
# 현재 설정: 19:00
claude-set-session-resets 20

# Daemon 재시작 (필수)
killall claude-usage-monitor
~/.local/bin/claude-usage-monitor &
```

### 4. 퍼센트 불일치 시 재조정
```bash
# Claude /usage UI 값으로 즉시 보정
claude-calibrate 35 56

# 결과 확인
# ✅ SwiftBar 메뉴바: 35.4%
# ✅ 드롭다운 Session Max: 35.4%
# ✅ 드롭다운 Weekly Max: 56.2%
```

### 5. 다음 세션 준비
- **세션 리셋** (19:00): Override 자동 만료, 새 세션 시작
- **주간 리셋**: Override 7일 후 만료
- 필요 시 Claude /usage UI 확인 후 재조정

---

## 📝 알려진 이슈

### 1. 첫 세션 정확도 낮음
**원인**: Config limit과 실제 limit 불일치
**해결 (자동)**: Global fallback limit 시스템으로 다른 세션의 학습 데이터 활용 (2025-10-17)
**해결 (수동)**: 첫 사용 시 Claude /usage UI 값으로 calibration 권장 (추가 정확도 향상)

### 2. 세션 전환 시 정확도
**원인**: 새 세션에 학습 데이터 부족
**해결 (자동)**: Global fallback limit으로 초기 정확도 확보 (2025-10-17)
**해결 (수동)**: 각 세션 시작 시 재조정 권장 (선택사항)

### 3. 주간 사용량 증가 속도
**원인**: 7일 rolling 윈도우라 오래된 데이터 빠져나감
**정상**: 토큰 사용보다 퍼센트가 느리게 증가할 수 있음

---

## 🔗 관련 문서

- `../README.md` - 프로젝트 전체 개요 및 설치 가이드
- `LOGIC_PRIORITY.md` - Override 로직 및 우선순위 상세
- `SESSION_RESET_TIME.md` - 세션 리셋 시간 설정 가이드

---

**생성일**: 2025-10-16 11:00 KST
**최종 업데이트**: 2025-10-17 KST
**마지막 테스트**:
- `claude-calibrate 35 56` 성공 ✅
- Override 실시간 계산 동작 확인 ✅
- SwiftBar Max 항목 표시 확인 ✅
- Global fallback limit 동작 확인 ✅ (2025-10-17)
- 세션 리셋 시간 자동 재시작 확인 ✅ (2025-10-17)
- Legacy 모듈 제거 완료 ✅ (2025-10-17)
