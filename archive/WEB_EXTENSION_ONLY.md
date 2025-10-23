# Web Extension 전용 모드

## 🎯 개요

SwiftBar가 **Chrome Extension 전용**으로 작동합니다.
Monitor daemon이 완전히 제거되어 간단하고 빠릅니다.

## 📊 개선 내역

### Before (v2.x)
- Monitor daemon (Python) 백그라운드 실행
- 복잡한 calibration 로직
- 277줄의 SwiftBar 스크립트
- Multiple 의존성 (Python, config.json, 등)

### After (v3.0 - Web Extension Only)
- **Monitor daemon 없음** ✅
- **Chrome Extension만 사용** ✅
- **100줄의 간단한 스크립트** (64% 감소!)
- **단일 JSON 파일** (/tmp/claude-web-usage.json)

## 🚀 작동 방식

```
Chrome Extension "Scrape Now"
    ↓
~/Downloads/claude-auto-usage.json 생성
    ↓
fswatch 자동 감지 (1초 이내)
    ↓
claude-sync-from-extension 실행
    ↓
/tmp/claude-web-usage.json 생성
    ↓
SwiftBar 자동 새로고침 ✨
```

## 📁 파일 구조

### 사용하는 파일
```
/tmp/claude-web-usage.json          # SwiftBar 데이터 (간단 JSON)
~/.local/bin/claude-sync-from-extension  # 동기화 스크립트
~/.local/bin/claude-extension-watcher    # 파일 감시자
~/Library/Application Support/SwiftBar/ClaudeUsage.1m.sh  # SwiftBar 플러그인 (100줄)
~/Library/LaunchAgents/com.claude.extension.watcher.plist # 자동 시작
```

### 제거된 파일 (더 이상 사용 안 함)
```
~/.claude_usage.json                 # Monitor daemon 데이터
~/.claude-monitor/config.json        # Monitor 설정
~/.local/bin/claude-usage-monitor    # Monitor daemon
~/.local/bin/calibration_learner.py  # Calibration 로직
~/Library/LaunchAgents/com.claude.usage-monitor.plist     # 제거됨
~/Library/LaunchAgents/com.claude.monitor.auto-sync.plist # 제거됨
```

## 💡 사용 방법

### 자동 동기화 (권장)
1. Chrome Extension → "Scrape Now" 클릭
2. **끝!** 1-3초 이내 자동 업데이트

### 수동 동기화 (옵션)
```bash
claude-sync-from-extension
```

또는 SwiftBar 메뉴:
```
🔄 Actions → Sync from Chrome Extension
```

## 📊 SwiftBar 표시

### 메뉴바
```
🟢 3%   (0-49%: 녹색)
🟡 65%  (50-79%: 노란색)
🔴 85%  (80-100%: 빨간색)
```

### 드롭다운 메뉴
```
📊 Session Usage
--Current: 3% | color=green
--Source: Chrome Extension

📈 Weekly Usage
--Current: 3%
--Source: Chrome Extension

🕐 Last Updated: 10/23 06:33

🔄 Actions
--Sync from Chrome Extension
--Refresh now
--View data
--Clear data

📖 How to Update
--1. Chrome Extension → 'Scrape Now'
--2. Wait 1-3 seconds (auto-sync)
--3. SwiftBar updates automatically

📡 Data Source
--Chrome Extension (Web Scraping)
--File: /tmp/claude-web-usage.json
--Auto-sync: Enabled ✅
```

## 🔧 관리

### Watcher 상태 확인
```bash
ps aux | grep claude-extension-watcher
```

### Watcher 재시작
```bash
killall claude-extension-watcher
claude-start-extension-watcher
```

### LaunchAgent 상태
```bash
# 확인
launchctl list | grep claude

# 출력:
# -  0  com.claude.extension.watcher  ✅ (Web Extension watcher만)
```

### 데이터 파일 확인
```bash
# Web Extension 데이터
cat /tmp/claude-web-usage.json

# 출력 예시:
{
  "timestamp": "2025-10-23T06:33:00Z",
  "source": "chrome_extension",
  "session": {
    "percentage": 3,
    "last_updated": "2025-10-23T06:33:00Z"
  },
  "weekly": {
    "percentage": 3,
    "last_updated": "2025-10-23T06:33:00Z"
  }
}
```

## 🎯 장점

### 1. 간단함
- 복잡한 Python daemon 없음
- 단일 JSON 파일
- 100줄의 간결한 스크립트

### 2. 빠름
- 1-3초 이내 업데이트
- 백그라운드 프로세스 최소화
- 리소스 사용 거의 없음

### 3. 신뢰성
- Chrome Extension이 직접 스크래핑
- 학습/calibration 오류 없음
- 단순한 구조 = 적은 오류

### 4. 유지보수
- 코드 64% 감소
- 의존성 최소화
- 디버깅 용이

## 🐛 문제 해결

### SwiftBar에 "No Data" 표시
```bash
# 1. Watcher 확인
ps aux | grep claude-extension-watcher

# 2. 수동 동기화
claude-sync-from-extension

# 3. 데이터 파일 확인
cat /tmp/claude-web-usage.json
```

### 자동 동기화 안 됨
```bash
# Watcher 로그 확인
tail -20 /tmp/claude-extension-watcher.log

# Watcher 재시작
killall claude-extension-watcher
claude-start-extension-watcher
```

### Chrome Extension 작동 안 함
```
1. chrome://extensions/ 접속
2. "Claude Usage Monitor" 찾기
3. 🔄 새로고침 버튼 클릭
4. "Scrape Now" 다시 시도
```

## ✅ 최종 체크리스트

- ✅ Monitor daemon 제거됨
- ✅ SwiftBar 100줄로 간소화됨
- ✅ Web Extension watcher만 실행 중
- ✅ 자동 동기화 작동 (1-3초)
- ✅ /tmp/claude-web-usage.json 사용
- ✅ LaunchAgent 자동 시작 설정됨

## 🎉 결론

**완전히 간소화되었습니다!**

- Monitor daemon 없음
- Python 의존성 제거
- 단순한 구조
- 빠른 업데이트
- 쉬운 유지보수

Chrome Extension만으로 모든 것이 작동합니다! 🚀
