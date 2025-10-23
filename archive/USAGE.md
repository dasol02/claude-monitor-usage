# Claude Monitor - 사용 가이드

## 🎯 Calibration System

### 개요
모니터가 읽는 사용량과 실제 `claude usage`의 차이를 학습하여 더 정확한 알림을 제공합니다.

### 특징
- ✅ **세션 윈도우별 독립 학습** (15:00-20:00, 20:00-01:00 등)
- ✅ **주간 사용량도 학습 가능**
- ✅ **10개 샘플부터 보정 적용**
- ✅ **SwiftBar 메뉴에 상태 표시**

---

## 📱 사용 방법

### 1. SwiftBar에서 Calibrate 실행

1. **SwiftBar 메뉴 열기** (상단바 아이콘 클릭)
2. **🎯 Calibration** 섹션 확인
3. **"Calibrate now..."** 클릭
4. 터미널이 열리면:

```
============================================================
📊 Calibration Check for 15:00-20:00
============================================================
Monitor Session: 48.6%
Monitor Weekly:  34.6%

Please check actual usage from 'claude usage' command
and enter the percentages below.

Example:
  Session Output: 54.2%  → enter: 54.2
  Weekly Output:  35%    → enter: 35

Press Enter on Session to skip.

Actual Session Output %: ▊
```

5. **`claude usage` 실행**하고 실제 % 확인
6. **Session Output %** 입력 (예: `58`)
7. **Weekly Output %** 입력 (예: `35`) - 선택사항, Enter로 스킵 가능
8. 완료!

---

### 2. 명령줄에서 직접 실행

```bash
# Calibration 실행
claude-calibrate

# 현재 상태 확인
cd ~/.local/bin && python3 calibration_learner.py --status

# 히스토리 확인 (JSON)
cd ~/.local/bin && python3 calibration_learner.py --history
```

---

## 📊 학습 단계

| 샘플 수 | Status | 설명 |
|---------|--------|------|
| 0-2 | `insufficient_data` | 데이터 부족 - baseline 사용 |
| 3-9 | `insufficient_data` | 통계 계산 시작하지만 미적용 |
| 10-49 | `learning` | 보정값 적용 시작 |
| 50+ | `learned` | Confidence 0.7+ 시 완전 학습 |

---

## 🔧 코드 수정 후 반영

```bash
# 이제 이 명령어 하나만!
claude-reload
```

- install/uninstall 필요 없음
- 5초 안에 반영됨
- 모니터 데몬 재시작 + SwiftBar 갱신

---

## 📈 SwiftBar 표시

### Calibration 섹션 예시:

```
🎯 Calibration (15:00-20:00)
  --Status: Learning (conf: 0.61)
  --Monitor: 48.6% → Actual: 58.9%
  --Offset: +10.3%
  --Calibrate now...
```

### 상태별 의미:

- **Needs more data**: 3개 미만 샘플
- **Learning (conf: X.XX)**: 학습 중
- **✅ Active (conf: X.XX)**: 완전 학습됨, 알림에 적용

---

## 💡 팁

1. **자주 입력할수록 정확해집니다**
   - 매일 1-2번씩 입력 추천
   - 특히 사용량이 많을 때 입력하면 효과적

2. **세션 윈도우별 독립 학습**
   - 15:00-20:00과 20:00-01:00은 별도로 학습
   - 각 시간대마다 10개씩 입력 필요

3. **주간 학습도 권장**
   - 주간 사용량도 함께 입력하면 더 정확
   - 선택사항이므로 스킵해도 무방

4. **SwiftBar 갱신**
   - 1분마다 자동 갱신
   - 수동 갱신: "Refresh now" 클릭

---

## 🗂️ 파일 위치

### 설정 파일
```
~/.claude-monitor/
├── config.json              # 전체 설정
├── calibration_data.json    # 학습 데이터
├── session_history.json     # 세션 히스토리
└── notification_state.json  # 알림 상태
```

### 실행 파일
```
~/.local/bin/
├── claude-usage-monitor     # 메인 모니터
├── claude-calibrate         # Calibration 스크립트
├── calibration_learner.py   # 학습 로직
└── claude-reload            # 빠른 재시작
```

### SwiftBar 플러그인
```
~/Library/Application Support/SwiftBar/
└── ClaudeUsage.1m.sh        # SwiftBar 플러그인
```

---

## ❓ 문제 해결

### Calibration이 SwiftBar에 표시 안 됨
```bash
claude-reload
```

### 보정값이 적용 안 됨
- 10개 이상 샘플 필요
- 현재 상태 확인: `cd ~/.local/bin && python3 calibration_learner.py --status`

### 모니터가 멈춤
```bash
launchctl list | grep claude
launchctl kickstart -k gui/$UID/com.claude.usage-monitor
```

---

## 📞 지원

이슈 발생 시:
1. 로그 확인: `tail -50 ~/.claude-monitor/calibration-daemon.error.log`
2. 상태 확인: `cd ~/.local/bin && python3 calibration_learner.py --status`
3. 재시작: `claude-reload`

---

**Happy Coding! 🚀**
