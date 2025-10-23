# Claude Team Usage Monitor

**macOS 메뉴바에서 Claude Code (Team Premium) 사용량을 실시간으로 모니터링**

[![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)](https://www.apple.com/macos)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## ✨ 특징

- 🎯 **Team Premium 전용** - Claude Code Team Premium 플랜에 최적화
- 🎚️ **Calibration 시스템** - Claude UI 기준으로 수동 보정 (±0.5% 정확도)
- 📊 **이중 추적** - 세션(5시간) + 주간(7일) 동시 모니터링
- ⚡ **실시간 계산** - Learned limit 기반 동적 퍼센트 계산
- 🔄 **Global Fallback Limit** - 세션 간 학습 데이터 공유로 초기 정확도 향상
- 🔔 **스마트 알림** - 80%, 90%, 95% 도달 시 macOS 알림
- 🎨 **간결한 UI** - SwiftBar 메뉴바에서 핵심 정보만 표시
- 💻 **개별 PC 지원** - 각 PC에서 독립적으로 작동
- 🛡️ **안정성 강화** (v2.1) - Daemon 중복 방지, 윈도우 검증, Limit 범위 검증

## 🚀 설치

```bash
git clone git@github.com:dslee02/claude-team-usage-monitor.git
cd claude-team-usage-monitor
./install.sh
```

설치 후 SwiftBar를 실행하면 메뉴바에서 바로 사용량을 확인할 수 있습니다.

## 📊 사용 예시

**메뉴바:**
```
🟢 35.2%
```

**드롭다운:**
```
📊 Session (resets in 2h 20m)
  Max: 35.2% (calibrated)
  Output: 27.0% (130,660 tokens)
  Input: 36.2% (12,110 tokens)
  Messages: 525

📈 Weekly (7 days)
  Max: 56.1% (calibrated)
  Output: 49.1% (956,062 tokens)
  Input: 7.4% (65,464 tokens)
  Messages: 4,140
```

## 💡 작동 원리

### 1. 자동 모니터링
- Claude Code 세션 파일(`~/.claude/projects`)을 실시간으로 파싱
- 토큰 사용량 자동 집계 (input, output, cache)

### 2. Calibration 시스템
- **Claude UI의 실제 값으로 수동 보정**
- 입력한 값을 기준으로 limit 역산
- Learned limit으로 실시간 퍼센트 계산

### 3. Override 메커니즘
- 세션/주간 각각 독립적으로 관리
- 세션 종료 시까지 고정 기준 유지
- 토큰 증가에 따라 동적으로 퍼센트 업데이트

### 4. Global Fallback Limit
- 모든 세션의 learned limit을 가중 평균으로 계산
- 새 세션 또는 데이터 부족 시 fallback limit 사용
- 각 세션은 독립적으로 학습을 계속하며 점진적으로 정확도 향상

## 🎯 Calibration 사용법

### 기본 사용
```bash
# Claude Code에서 /usage 명령 실행 후
# Session Output: 35% 확인

# 보정
claude-calibrate 35

# 세션 + 주간 동시 보정
claude-calibrate 35 56
```

### 결과
- **즉시 반영**: SwiftBar에 입력값 즉시 표시
- **실시간 계산**: 토큰 증가 시 자동으로 퍼센트 업데이트
- **세션별 관리**: 각 세션마다 독립적으로 유지

### 상태 확인
```bash
# Calibration 상태 확인
claude-calibrate --status

# 히스토리 조회
claude-calibrate --history
```

## 🔧 주요 명령어

```bash
# 현재 사용량 확인
cat ~/.claude_usage.json | jq '.session.percentages'

# Calibration 수행 (대화형)
claude-calibrate-prompt

# 세션 리셋 시간 변경 (자동으로 데몬 재시작 및 SwiftBar 갱신)
claude-set-session-resets 20  # 20시로 변경

# Daemon 수동 재시작 (필요 시)
killall claude-usage-monitor
~/.local/bin/claude-usage-monitor &
```

## 📁 구조

```
claude-monitor/
├── README.md                    # 메인 사용 가이드
├── CHANGELOG.md                 # 버전별 변경사항
├── src/
│   ├── monitor_daemon.py        # 메인 모니터링 데몬 (PID lock 포함)
│   └── calibration_learner.py   # Calibration 시스템 (윈도우 검증, limit 검증)
├── plugins/
│   └── ClaudeUsage.1m.sh        # SwiftBar 플러그인 (상태 표시 개선)
├── docs/                        # 개발자 문서
│   ├── SESSION_RESTORE.md       # 세션 복원 가이드
│   ├── SESSION_RESET_TIME.md    # 리셋 시간 설정
│   └── LOGIC_PRIORITY.md        # 로직 우선순위 설명
└── archive/                     # 레거시 문서 및 코드
```

## ⚙️ 설정

### 세션 윈도우 (5시간 고정)
기본값 (base_hour = 14):
- 09:00-14:00
- 14:00-19:00
- 19:00-00:00
- 00:00-04:00
- 04:00-09:00

변경 가능:
```bash
claude-set-session-resets 20  # 20시를 기준으로 변경
```

### 주간 윈도우 (7일 rolling)
- 현재 시간부터 정확히 7일 전까지

### 알림 임계값
- 80% (첫 경고)
- 90% (높은 사용량)
- 95% (거의 한계)

## 🎯 정확도

- **Calibration 전**: ±3-5% 오차 (config limit 기반)
- **Calibration 후**: ±0.5% 정확도 (learned limit 기반)
- **Claude UI 기준**: Session 35% 입력 → 35.2% 실시간 계산

### Calibration 작동 원리

1. **토큰 역산**: 실제 사용량으로 API limit 계산
   ```
   limit = current_tokens / (actual_percentage / 100) / window_minutes
   ```

2. **실시간 계산**: Learned limit으로 퍼센트 계산
   ```
   percentage = (current_tokens / (learned_limit × window_minutes)) × 100
   ```

3. **세션별 관리**: 각 세션마다 독립적인 override

4. **Global Fallback**: 데이터 부족 시 다른 세션의 learned limit 활용
   ```
   fallback_limit = weighted_average(모든 세션의 learned_limit)
   weight = min(sample_count / 10.0, 1.0)
   ```

## 💻 여러 PC에서 사용

**각 PC에서 독립적으로 작동합니다:**

- PC-A, PC-B, PC-C 각각에 설치 가능
- 각 PC마다 별도로 calibration 데이터 관리
- PC 간 데이터 동기화 불필요
- 설치 후 첫 세션에서 calibration 1회 수행 권장

**예시:**
```
MacBook Pro  → 설치 → claude-calibrate 35 → ±0.5% 정확도
Mac Mini     → 설치 → claude-calibrate 35 → ±0.5% 정확도
iMac         → 설치 → claude-calibrate 35 → ±0.5% 정확도
```

## 🆕 v2.1 개선사항 (2025-10-22)

### 1. Daemon 안정성 강화
- **PID 파일 기반 중복 실행 방지**
  - `~/.claude-monitor/daemon.pid` 파일로 프로세스 관리
  - 중복 실행 시 자동 감지 및 경고
  - 오래된 PID 파일 자동 정리
  - `--force` 옵션으로 강제 시작 가능

### 2. 윈도우 검증 시스템
- **세션 윈도우 변경 시 자동 만료**
  - 과거 윈도우의 override 자동 삭제
  - 현재 윈도우와 일치하는 데이터만 적용
  - 윈도우 불일치로 인한 오류 방지

### 3. Calibration 정확도 개선
- **실행 전 자동 데이터 업데이트**
  - `claude-calibrate` 실행 전 monitor 강제 업데이트
  - 최신 윈도우 데이터로 calibration 수행
  - 오래된 데이터 사용으로 인한 오류 방지

### 4. Learned Limit 검증
- **범위 검증 자동화**
  - 최소값: 100 TPM
  - 최대값: 20,000 TPM
  - 범위 벗어날 시 자동 조정 및 경고
  - Override 적용 시에도 검증 수행

### 5. SwiftBar UI 개선
- **Calibration 상태 상세 표시**
  ```
  📚 Calibration Status
  --Session: ⭐ Override (12.4%)
  --  Window: 14:00-19:00
  --  Learned limit: 1196 TPM
  --  Original: 15.8%
  --Weekly: ⭐ Override (11.2%)
  ```
  - 현재 윈도우 표시
  - Learned limit TPM 값 표시
  - 원본/Calibrated 퍼센트 비교
  - 세션/주간 상태 분리 표시

## 🔍 트러블슈팅

### 메뉴바에 "⚠️ No Data" 표시

```bash
# Daemon 확인
ps aux | grep claude-usage-monitor

# PID 파일 확인 (v2.1+)
cat ~/.claude-monitor/daemon.pid

# 수동 실행
python3 src/monitor_daemon.py --once

# 로그 확인
cat ~/.claude_usage.json | jq .
```

### Calibration이 적용 안 됨

```bash
# 1. Override 확인 (현재 윈도우)
cat ~/.claude-monitor/calibration_data.json | jq '.["14:00-19:00"].latest_override'

# 2. Learned limit 확인 (v2.1+)
cat ~/.claude_usage.json | jq '.calibration.session.learned_limit'

# 3. Daemon 재시작 (PID 체크 포함)
cat ~/.claude-monitor/daemon.pid  # 현재 PID 확인
killall claude-usage-monitor
~/.local/bin/claude-usage-monitor &

# 4. SwiftBar 새로고침
open "swiftbar://refreshallplugins"
```

### SwiftBar 플러그인이 안 보임

```bash
# 권한 확인
chmod +x ~/Library/Application\ Support/SwiftBar/ClaudeUsage.1m.sh

# 플러그인 재설치
cp plugins/ClaudeUsage.1m.sh ~/Library/Application\ Support/SwiftBar/

# SwiftBar 재시작
killall SwiftBar && open -a SwiftBar
```

## 🛠️ 기술 스택

- **Python 3.9+** - Daemon 및 calibration 시스템
- **Bash** - SwiftBar 플러그인 및 CLI 도구
- **jq** - JSON 처리
- **SwiftBar** - macOS 메뉴바 UI
- **launchd** - 백그라운드 서비스 (선택사항)

## 📝 요구사항

- macOS (10.15 이상)
- Python 3.9+
- **Claude Code (Team Premium 플랜)**
- SwiftBar

### ⚠️ 중요 사항

**이 모니터는 Team Premium 플랜을 기준으로 개발되었습니다.**

- ✅ **Team Premium**: 정확도 ±0.5% (calibration 후)
- ⚠️ **개인 구독 (Pro, Max 등)**: 정확하지 않을 수 있음
  - 개인 구독 플랜은 limit 구조가 다름
  - Calibration 시스템으로 어느정도 대응 가능하나 테스트 안됨

**권장**: Team Premium 플랜 사용자만 설치하시기 바랍니다.

## 📚 개발자 문서

프로젝트 개발 및 디버깅을 위한 상세 문서는 `docs/` 폴더에 있습니다:

- [docs/SESSION_RESTORE.md](docs/SESSION_RESTORE.md) - 세션 복원 및 상태 파악 가이드
- [docs/LOGIC_PRIORITY.md](docs/LOGIC_PRIORITY.md) - Calibration 로직 및 우선순위
- [docs/SESSION_RESET_TIME.md](docs/SESSION_RESET_TIME.md) - 세션 리셋 시간 설정 방법

## 🤝 기여

이슈와 PR은 언제나 환영합니다!

## 📄 라이선스

MIT License

## 🙏 감사

- [SwiftBar](https://github.com/swiftbar/SwiftBar) - macOS 메뉴바 프레임워크
- [Claude Code](https://claude.ai/code) - Anthropic의 AI 코딩 도구

---

**Made for Team Premium users** 🚀
