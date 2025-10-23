# SwiftBar 자동 동기화 가이드

Chrome Extension의 스크래핑 데이터를 SwiftBar에 자동으로 반영하는 방법입니다.

## 📊 작동 원리

```
Chrome Extension (5분마다)
    ↓
~/Downloads/.claude-monitor/auto-usage.json 생성
    ↓
LaunchAgent (1분마다 확인)
    ↓
파일 발견 → claude-calibrate 실행
    ↓
Monitor 업데이트 + SwiftBar 새로고침
    ↓
SwiftBar에 최신 사용량 표시 ✨
```

## 🚀 설치 방법

### 자동 설치 (권장)

```bash
cd /Users/dasollee/claude-monitor
./install_swiftbar_sync.sh
```

### 수동 설치

1. **스크립트 확인**
```bash
ls -l ~/.local/bin/claude-auto-update-usage
```

2. **다운로드 폴더 생성**
```bash
mkdir -p ~/Downloads/.claude-monitor
```

3. **LaunchAgent 생성**
```bash
cp ~/claude-monitor/LaunchAgent/com.claude.monitor.auto-sync.plist \
   ~/Library/LaunchAgents/
```

4. **LaunchAgent 로드**
```bash
launchctl load ~/Library/LaunchAgents/com.claude.monitor.auto-sync.plist
```

## ✅ 설치 확인

### 1. LaunchAgent 실행 확인
```bash
launchctl list | grep claude.monitor
```

출력:
```
-	0	com.claude.monitor.auto-sync
```

### 2. 로그 확인
```bash
tail -f /tmp/claude-auto-sync.log
```

### 3. 수동 테스트

Chrome Extension에서 "Scrape Now" 클릭 후:
```bash
# 파일 생성 확인
ls -l ~/Downloads/.claude-monitor/auto-usage.json

# 1분 대기 후 파일 삭제 확인 (처리됨)
ls -l ~/Downloads/.claude-monitor/auto-usage.json
# → No such file or directory (정상)

# SwiftBar 확인
# → 업데이트된 값 표시되어야 함
```

## 🔧 관리 명령어

### 중단
```bash
launchctl unload ~/Library/LaunchAgents/com.claude.monitor.auto-sync.plist
```

### 재시작
```bash
launchctl load ~/Library/LaunchAgents/com.claude.monitor.auto-sync.plist
```

### 로그 보기
```bash
# 일반 로그
tail -f /tmp/claude-auto-sync.log

# 에러 로그
tail -f /tmp/claude-auto-sync-error.log
```

### 상태 확인
```bash
launchctl list | grep claude
```

## 📝 설정 변경

### 확인 주기 변경 (1분 → 30초)

`~/Library/LaunchAgents/com.claude.monitor.auto-sync.plist` 수정:
```xml
<key>StartInterval</key>
<integer>30</integer>  <!-- 60 → 30으로 변경 -->
```

변경 후:
```bash
launchctl unload ~/Library/LaunchAgents/com.claude.monitor.auto-sync.plist
launchctl load ~/Library/LaunchAgents/com.claude.monitor.auto-sync.plist
```

## 🐛 문제 해결

### LaunchAgent가 실행 안 됨
```bash
# 권한 확인
ls -l ~/.local/bin/claude-auto-update-usage
# → -rwxr-xr-x (실행 권한 있어야 함)

# 수동 실행 테스트
~/.local/bin/claude-auto-update-usage
```

### 파일이 처리 안 됨
```bash
# jq 설치 확인
which jq
brew install jq

# 파일 내용 확인
cat ~/Downloads/.claude-monitor/auto-usage.json

# 수동 테스트
SESSION=17
WEEKLY=17
claude-calibrate $SESSION $WEEKLY
```

### SwiftBar에 반영 안 됨
```bash
# SwiftBar 수동 새로고침
open "swiftbar://refreshallplugins"

# Monitor daemon 확인
ps aux | grep claude-usage-monitor

# Monitor 재시작
killall claude-usage-monitor
~/.local/bin/claude-usage-monitor &
```

## 📊 완전 자동화 확인

이제 다음이 모두 자동으로 작동해야 합니다:

1. ✅ **Chrome Extension**: 5분마다 자동 스크래핑
2. ✅ **Badge 업데이트**: Chrome 툴바에 실시간 표시
3. ✅ **파일 생성**: ~/Downloads/.claude-monitor/auto-usage.json
4. ✅ **LaunchAgent**: 1분마다 파일 확인
5. ✅ **Auto Calibrate**: 파일 발견 시 자동 실행
6. ✅ **SwiftBar 업데이트**: 자동 새로고침

## 🎯 최종 테스트

1. Chrome Extension "Scrape Now" 클릭
2. 1분 대기
3. SwiftBar 확인 → 값 변경됨 ✅
4. Chrome Badge 확인 → 값 표시됨 ✅

완전 자동화 완성! 🎉

## 📌 추가 정보

- **지연 시간**: Extension 스크래핑 후 최대 1분 (LaunchAgent 주기)
- **리소스 사용**: 매우 낮음 (1분마다 파일 체크만)
- **안정성**: 파일 기반이라 안정적
- **로그**: /tmp/claude-auto-sync.log에 기록

## 🔄 업데이트

스크립트 업데이트 시:
```bash
# LaunchAgent 재로드
launchctl unload ~/Library/LaunchAgents/com.claude.monitor.auto-sync.plist
launchctl load ~/Library/LaunchAgents/com.claude.monitor.auto-sync.plist
```
