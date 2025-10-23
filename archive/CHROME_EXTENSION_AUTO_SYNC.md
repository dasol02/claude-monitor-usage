# Chrome Extension 자동 동기화 완벽 가이드

## 🎯 개요

Chrome Extension이 스크래핑한 사용량 데이터를 **자동으로** SwiftBar에 반영합니다.

## 🚀 작동 원리

```
Chrome Extension "Scrape Now" 클릭
    ↓
~/Downloads/claude-auto-usage.json 생성
    ↓
fswatch가 파일 생성 감지 (즉시)
    ↓
자동으로 claude-sync-from-extension 실행
    ↓
SwiftBar 자동 업데이트 ✨
```

**지연 시간**: 1초 이내 (거의 즉시)

## 📦 설치 완료 상태

✅ Chrome Extension 설치됨
✅ SwiftBar 플러그인 간소화됨 (277줄 → 107줄)
✅ 자동 동기화 Watcher 실행 중
✅ 로그인 시 자동 시작 설정됨

## 🎮 사용 방법

### 자동 동기화 (권장)

1. **Chrome Extension** → "Scrape Now" 클릭
2. **끝!** 1초 이내 SwiftBar 자동 업데이트

### 수동 동기화 (옵션)

```bash
claude-sync-from-extension
```

또는 SwiftBar 메뉴:
```
🔄 Actions → Sync from Chrome Extension
```

## 🔧 관리 명령어

### Watcher 상태 확인

```bash
ps aux | grep claude-extension-watcher
```

### Watcher 재시작

```bash
killall claude-extension-watcher
claude-start-extension-watcher
```

### 로그 확인

```bash
tail -f /tmp/claude-extension-watcher.log
```

## 🏃 자동 시작

LaunchAgent가 설정되어 **Mac 로그인 시 자동 시작**됩니다:

```bash
# 상태 확인
launchctl list | grep claude.extension

# 수동 시작
launchctl load ~/Library/LaunchAgents/com.claude.extension.watcher.plist

# 중단
launchctl unload ~/Library/LaunchAgents/com.claude.extension.watcher.plist
```

## 📊 SwiftBar 표시

### 메뉴바

```
🟢 2.0%  (0-49%: 녹색)
🟡 65%   (50-79%: 노란색)
🔴 85%   (80-100%: 빨간색)
```

### 드롭다운 메뉴

```
📊 Session Usage
--Current: 2.0%
--Status: ⭐ Web Calibrated
--Resets in: 4h 49m

📈 Weekly Usage
--Current: 2.0%
--Status: ⭐ Web Calibrated

🔄 Actions
--Refresh now
--Sync from Chrome Extension
--Manual calibrate
--View data

📡 Data Source: Chrome Extension
```

## 🎯 완전 자동화 체크리스트

- ✅ Chrome Extension: 5분마다 자동 스크래핑
- ✅ Chrome Badge: 실시간 % 표시 + 색상 코드
- ✅ 파일 감지: fswatch로 1초 이내 감지
- ✅ 자동 Calibrate: claude-calibrate 자동 실행
- ✅ SwiftBar 업데이트: 자동 새로고침
- ✅ 로그인 시 자동 시작: LaunchAgent 설정됨

## 🐛 문제 해결

### Watcher가 실행 안 됨

```bash
# 수동 시작
claude-start-extension-watcher

# 프로세스 확인
ps aux | grep claude-extension-watcher
```

### 동기화가 안 됨

```bash
# 로그 확인
tail -20 /tmp/claude-extension-watcher.log

# 수동 테스트
echo '{"session": 5, "weekly": 5}' > ~/Downloads/claude-auto-usage.json
# 1초 대기 후 SwiftBar 확인
```

### SwiftBar 업데이트 안 됨

```bash
# SwiftBar 수동 새로고침
open "swiftbar://refreshallplugins"

# 플러그인 직접 실행
"/Users/dasollee/Library/Application Support/SwiftBar/ClaudeUsage.1m.sh"
```

## 📁 파일 위치

```
Chrome Extension:
  ~/claude-monitor/chrome-extension/

Scripts:
  ~/.local/bin/claude-extension-watcher
  ~/.local/bin/claude-start-extension-watcher
  ~/.local/bin/claude-sync-from-extension

SwiftBar Plugin:
  ~/Library/Application Support/SwiftBar/ClaudeUsage.1m.sh

LaunchAgent:
  ~/Library/LaunchAgents/com.claude.extension.watcher.plist

Logs:
  /tmp/claude-extension-watcher.log
  /tmp/claude-extension-watcher-error.log
```

## 🎉 최종 결과

**완전 자동화 완성!**

1. Chrome Extension "Scrape Now" 클릭
2. 1초 이내 SwiftBar 자동 업데이트
3. 수동 입력 필요 없음!
4. Mac 재시작 후에도 자동 작동!

더 이상 수동 calibration 필요 없습니다! 🚀
