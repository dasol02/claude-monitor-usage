# 세션 리셋 시간 설정 가이드

## 📋 개요

Claude의 세션 리셋 시간은 가끔 변경될 수 있습니다:
- **오늘**: 19:00에 리셋
- **어제**: 20:00에 리셋

이 기능을 사용하면 리셋 시간을 간단하게 업데이트할 수 있습니다.

---

## 🎯 사용 방법

### 방법 1: SwiftBar 메뉴에서 설정

1. SwiftBar 메뉴바 아이콘 클릭
2. 드롭다운에서 **"⏰ Session Reset Time"** 섹션 찾기
3. **"Set reset time"** 클릭
4. 터미널에서 리셋 시간 입력 (예: `20`)
5. 자동으로 적용됨

```
⏰ Session Reset Time
  Current: 19:00
  Set reset time  ← 클릭
```

### 방법 2: CLI에서 직접 설정

```bash
# 현재 설정 확인
claude-set-session-resets

# 리셋 시간 변경 (예: 20시)
claude-set-session-resets 20
```

---

## 🔄 동작 원리

### 입력: 리셋 시간
```bash
claude-set-session-resets 20  # 20:00에 리셋
```

### 자동 계산: Base Hour
- **리셋 시간**: 20:00
- **Base hour 계산**: `(20 - 5) = 15`
- **결과**: 세션은 15시부터 시작

### 생성되는 세션 윈도우
```
15:00-20:00  ← 첫 세션 (20시에 리셋)
20:00-01:00
01:00-06:00
06:00-11:00
11:00-16:00
```

---

## 📊 예시

### 예시 1: 현재 (19시 리셋)
```bash
$ claude-set-session-resets 19

Current reset time: 19:00 (base: 14)

New session windows:
  - 14:00-19:00 ← First session resets at 19:00
  - 19:00-00:00
  - 00:00-05:00
  - 05:00-10:00
  - 10:00-15:00
```

### 예시 2: 어제 (20시 리셋)
```bash
$ claude-set-session-resets 20

Current reset time: 19:00 (base: 14)

Changing reset time to: 20:00
   → Calculated base hour: 15

New session windows:
  - 15:00-20:00 ← First session resets at 20:00
  - 20:00-01:00
  - 01:00-06:00
  - 06:00-11:00
  - 11:00-16:00
```

### 예시 3: 새벽 리셋
```bash
$ claude-set-session-resets 8

New session windows:
  - 03:00-08:00 ← First session resets at 08:00
  - 08:00-13:00
  - 13:00-18:00
  - 18:00-23:00
  - 23:00-04:00
```

---

## ✅ 변경 후 자동 처리

**2025-10-17 업데이트**: 리셋 시간 변경 시 자동으로 다음 작업을 수행합니다:

### 자동으로 처리되는 작업

1. **모니터 데몬 재시작**
   - 기존 프로세스 종료
   - 새 설정으로 데몬 재시작
   - 0.5초 대기 후 안정화

2. **SwiftBar 새로고침**
   - 플러그인 자동 갱신
   - 새 세션 윈도우 표시

3. **완료 메시지 출력**
   ```
   🔄 Restarting monitor daemon...
   ✅ Monitor daemon restarted
   🔄 Refreshing SwiftBar...
   ✅ SwiftBar refreshed
   💡 Tip: If needed, recalibrate with: claude-calibrate <actual_%>
   ```

### 수동 작업 (선택사항)

#### 재조정 (권장)
```bash
# 기존 calibration 데이터 확인
claude-calibrate --status

# Claude usage UI에서 현재 % 확인 후
claude-calibrate <actual_%>
```

**참고**:
- 기존 calibration 데이터는 이전 윈도우 키 사용 (예: `14:00-19:00`)
- 새 윈도우 키 (예: `15:00-20:00`)에는 데이터 없음
- **Global fallback limit**으로 다른 세션 데이터 활용 (자동)
- 새 세션에서 재조정하면 정확도 추가 향상 (선택)

---

## 🔍 실제 리셋 시간 확인 방법

### Claude Code에서 확인
```bash
# Claude Code에서
/usage
```

출력 예시:
```
Session Output: 10%
Resets in 2h 30m (at 19:00 KST)  ← 여기서 확인
```

### 또는 SwiftBar에서 확인
메뉴바 → 드롭다운에서:
```
📊 Session (resets in 2h 30m)  ← 현재 리셋까지 남은 시간
```

---

## 📝 Config 파일 직접 수정 (고급)

**파일**: `~/.claude-monitor/config.json`

```json
{
  "reset_schedule": {
    "type": "rolling_5h",
    "description": "마지막 사용 시점부터 5시간 후 리셋",
    "session_base_hour": 14,  ← 이 값 변경 (14 = 19시 리셋)
    "note": "세션 시작 기준 시간"
  }
}
```

**Base hour 계산**:
```
session_base_hour = (reset_hour - 5 + 24) % 24

예시:
- 19시 리셋 → (19 - 5) = 14
- 20시 리셋 → (20 - 5) = 15
- 08시 리셋 → (8 - 5) = 3
- 03시 리셋 → (3 - 5 + 24) = 22
```

---

## 🛠️ 문제 해결

### 문제 1: 변경했는데 SwiftBar에 반영 안됨
```bash
# 자동 갱신이 실패한 경우 수동으로 SwiftBar 강제 새로고침
open swiftbar://refreshallplugins

# 또는 SwiftBar 재시작
killall SwiftBar
open -a SwiftBar
```

**참고**: `claude-set-session-resets` 명령어는 자동으로 SwiftBar를 새로고침합니다 (2025-10-17 업데이트).

### 문제 2: 모니터가 이전 윈도우 사용
```bash
# 자동 재시작이 실패한 경우 수동으로 데몬 재시작
killall claude-usage-monitor
~/.local/bin/claude-usage-monitor &

# 확인
python3 src/monitor_daemon.py --once | jq '.calibration.info.window_key'
# → "15:00-20:00" (새 윈도우)
```

**참고**: `claude-set-session-resets` 명령어는 자동으로 데몬을 재시작합니다 (2025-10-17 업데이트).

### 문제 3: Calibration 데이터 꼬임
```bash
# 특정 윈도우 리셋 (이전 윈도우)
python3 cleanup_window_data.py --window 14:00-19:00 --reset

# 새 윈도우에서 재조정
claude-calibrate 10  # (Claude usage UI 값)
```

---

## 📖 관련 명령어

```bash
# 현재 설정 보기
claude-set-session-resets

# 리셋 시간 변경
claude-set-session-resets <hour>

# Calibration 상태 확인
claude-calibrate --status

# 모니터 확인
python3 src/monitor_daemon.py --once | jq '.calibration.info.window_key'

# Config 확인
cat ~/.claude-monitor/config.json | jq '.reset_schedule'
```

---

## 🎓 FAQ

### Q: 언제 변경해야 하나요?
**A**: Claude usage UI의 리셋 시간과 모니터의 리셋 시간이 다를 때
- Claude: "Resets at 20:00"
- 모니터: "Resets at 19:00"
→ `claude-set-session-resets 20` 실행

### Q: 자주 변경되나요?
**A**: 가끔 변경됩니다. 보통 하루에 한 번 정도 확인하면 됩니다.

### Q: 변경하면 데이터 손실되나요?
**A**: 아니요. 기존 데이터는 유지됩니다.
- 이전 윈도우 (14:00-19:00) 데이터: 보존
- 새 윈도우 (15:00-20:00) 데이터: 새로 생성

### Q: 모든 윈도우가 5시간인가요?
**A**: 네. 모든 세션은 정확히 5시간입니다.
- 이전 구현: 00:00-04:00 (4시간) - 불규칙
- 현재 구현: 모든 윈도우 5시간 - 일관성 ✅

### Q: Base hour vs Reset hour?
**A**:
- **Reset hour**: 사용자가 입력하는 값 (직관적)
  - 예: 19 → "19시에 리셋"
- **Base hour**: 내부적으로 계산되는 값 (자동)
  - 예: 14 → "14시에 세션 시작" (19시 리셋)

---

**구현 완료일**: 2025-10-16
**최종 업데이트**: 2025-10-17 (자동 재시작/갱신 추가)

**관련 파일**:
- `/Users/dasollee/.local/bin/claude-set-session-resets` (CLI - 자동 재시작 포함)
- `/Users/dasollee/.local/bin/claude-set-session-resets-prompt` (인터랙티브)
- `plugins/ClaudeUsage.1m.sh` (SwiftBar 버튼)
- `config.json` (session_base_hour 설정)

**변경 사항 (2025-10-17)**:
- ✅ 자동 데몬 재시작 추가 (`killall` + `claude-usage-monitor &`)
- ✅ 자동 SwiftBar 갱신 추가 (`open "swiftbar://refreshallplugins"`)
- ✅ 완료 메시지 출력 개선
- ✅ Global fallback limit으로 새 세션 자동 대응
