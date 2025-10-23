# Claude Team Usage Monitor v3.0

**완전 자동화된 Chrome Extension 기반 사용량 모니터**

Mac StatusBar (SwiftBar)에서 Claude Team 사용량을 실시간으로 모니터링합니다.

![Version](https://img.shields.io/badge/version-3.0-blue)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)
![Chrome](https://img.shields.io/badge/chrome-extension-green)

## ✨ 주요 기능

- 🔄 **완전 자동화**: Chrome Extension 클릭 한 번으로 자동 동기화
- 📊 **실시간 표시**: SwiftBar에 Session/Weekly 사용량 표시
- 🟢 **색상 코딩**: 사용량에 따른 자동 색상 변경 (녹색/노란색/빨간색)
- ⚡ **빠른 동기화**: 1-3초 이내 자동 업데이트
- 🎯 **간단한 구조**: Monitor daemon 제거, Extension 전용

## 📋 시스템 구성

### Chrome Extension
- 자동 스크래핑 (5분 간격)
- Badge에 실시간 % 표시
- 클릭 한 번으로 수동 스크래핑

### Extension Watcher
- fswatch 기반 파일 감지
- 1초 이내 자동 동기화
- 백그라운드 실행

### SwiftBar Plugin
- 간결한 표시 (100줄)
- 로컬 시간 표시
- 자동 새로고침

## 🚀 빠른 시작

### 1. Chrome Extension 설치

```bash
# Extension 폴더 열기
open ~/claude-monitor/chrome-extension/
```

1. Chrome 열기
2. `chrome://extensions/` 접속
3. **개발자 모드** 켜기
4. **압축해제된 확장 프로그램을 로드합니다** 클릭
5. `~/claude-monitor/chrome-extension` 폴더 선택

### 2. Extension Watcher 시작

```bash
claude-start-extension-watcher
```

### 3. SwiftBar 확인

SwiftBar가 이미 설치되어 있다면 자동으로 표시됩니다!

## 💡 사용 방법

### 자동 동기화 (권장)

1. Chrome Extension "Scrape Now" 클릭
2. 끝! 1-3초 후 SwiftBar 자동 업데이트 ✨

### 수동 입력 (백업)

Extension이 작동하지 않을 경우:

```bash
claude-manual-update 22 25  # session% weekly%
```

## 📊 SwiftBar 표시

```
🟢 22%                    ← Session 사용량
├─ 📊 Session Usage
│  ├─ Current: 22%
│  └─ Source: Chrome Extension
├─ 📈 Weekly Usage
│  ├─ Current: 25%
│  └─ Source: Chrome Extension
└─ 🕐 Last Updated: 10/23 16:14
```

### 색상 의미

- 🟢 **녹색** (0-49%): 안전
- 🟡 **노란색** (50-79%): 주의
- 🔴 **빨간색** (80-100%): 위험

## 🔧 관리 명령어

### Watcher 관리

```bash
# 상태 확인
ps aux | grep claude-extension-watcher

# 재시작
killall claude-extension-watcher
claude-start-extension-watcher

# 로그 확인
tail -f /tmp/claude-extension-watcher.log
```

### LaunchAgent (자동 시작)

```bash
# 상태 확인
launchctl list | grep claude.extension

# 로드
launchctl load ~/Library/LaunchAgents/com.claude.extension.watcher.plist

# 언로드
launchctl unload ~/Library/LaunchAgents/com.claude.extension.watcher.plist
```

## 📁 파일 구조

```
~/claude-monitor/
├── chrome-extension/          # Chrome Extension
│   ├── manifest.json
│   ├── background.js         # Service worker (DataURL 다운로드)
│   ├── content.js            # 페이지 스크래핑
│   ├── popup.html/js         # UI
│   └── README.md
├── README.md                  # 이 파일
├── CHANGELOG.md               # 변경 이력
├── WEB_EXTENSION_ONLY.md     # Web Extension 전용 가이드
└── CHROME_EXTENSION_AUTO_SYNC.md  # 자동 동기화 가이드

~/.local/bin/
├── claude-extension-watcher       # 파일 감시자
├── claude-start-extension-watcher # Watcher 시작
├── claude-sync-from-extension     # 동기화 스크립트
├── claude-manual-update           # 수동 입력
└── claude-find-extension-id       # Extension ID 찾기

~/Library/Application Support/SwiftBar/
└── ClaudeUsage.1m.sh             # SwiftBar 플러그인

/tmp/
└── claude-web-usage.json         # 현재 데이터
```

## 🐛 문제 해결

### Extension이 작동하지 않음

1. `chrome://extensions/` 에서 Extension 새로고침
2. 개발자 도구 Console 확인
3. `claude-manual-update` 명령어로 수동 입력

### SwiftBar 업데이트 안 됨

```bash
# SwiftBar 재시작
killall SwiftBar && open -a SwiftBar

# 데이터 파일 확인
cat /tmp/claude-web-usage.json
```

### Watcher가 작동하지 않음

```bash
# Watcher 재시작
killall claude-extension-watcher
claude-start-extension-watcher

# 로그 확인
tail -20 /tmp/claude-extension-watcher.log
```

## 📝 변경 이력

### v3.0 (2025-10-23) - Web Extension Only

- ✅ Monitor daemon 완전 제거
- ✅ Chrome Extension 전용 (DataURL 방식)
- ✅ fswatch 기반 자동 동기화 (1-3초)
- ✅ SwiftBar 플러그인 간소화 (277줄 → 100줄)
- ✅ 로컬 시간 표시
- ✅ Actions 버튼 정리

### v2.1 (2025-10-22)

- Monitor daemon + Calibration 시스템
- 학습 기반 한도 예측

### v1.0 (2025-10-16)

- 초기 버전
- Monitor daemon 기반

## 🎯 기술 스택

- **Chrome Extension**: Manifest V3, Service Worker
- **Watcher**: fswatch (macOS)
- **SwiftBar**: Bash script
- **자동 시작**: LaunchAgent (macOS)

## 📖 추가 문서

- [WEB_EXTENSION_ONLY.md](./WEB_EXTENSION_ONLY.md) - Web Extension 전용 상세 가이드
- [CHROME_EXTENSION_AUTO_SYNC.md](./CHROME_EXTENSION_AUTO_SYNC.md) - 자동 동기화 설명
- [chrome-extension/README.md](./chrome-extension/README.md) - Extension 개발 가이드
- [CHANGELOG.md](./CHANGELOG.md) - 전체 변경 이력

## 🤝 기여

이슈 및 PR은 환영합니다!

## 📄 라이센스

MIT License

---

**Made with ❤️ for Claude Team Users**
