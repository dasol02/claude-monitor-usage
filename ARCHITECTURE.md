# Claude Usage Monitor - 아키텍처 및 로직 설명

## 📋 목차
1. [전체 아키텍처](#전체-아키텍처)
2. [Chrome Extension 로직](#chrome-extension-로직)
3. [SwiftBar 연동 (macOS)](#swiftbar-연동-macos)
4. [데이터 흐름](#데이터-흐름)
5. [주요 함수 설명](#주요-함수-설명)

---

## 전체 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    사용자                                 │
│  1. Extension 아이콘 클릭                                │
│  2. Popup에서 사용량 확인                                │
│  3. (옵션) SwiftBar 메뉴바에서 확인                      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│           Chrome Extension (3개 파일)                    │
│  ┌────────────────────────────────────────────┐         │
│  │ 1. background.js (Service Worker)          │         │
│  │    - 5~60분마다 자동 스크래핑               │         │
│  │    - chrome.alarms API 사용                │         │
│  │    - 백그라운드에서 항상 실행               │         │
│  └────────────────────────────────────────────┘         │
│                     │                                    │
│                     ▼ (탭 열기)                          │
│  ┌────────────────────────────────────────────┐         │
│  │ 2. content.js (Content Script)             │         │
│  │    - https://claude.ai/settings/usage 접근 │         │
│  │    - 페이지에서 데이터 추출                 │         │
│  │    - Session/Weekly % + Reset Time         │         │
│  └────────────────────────────────────────────┘         │
│                     │                                    │
│                     ▼ (데이터 반환)                      │
│  ┌────────────────────────────────────────────┐         │
│  │ 3. popup.html/js (Popup UI)                │         │
│  │    - chrome.storage에서 데이터 읽기         │         │
│  │    - 사용자에게 표시                        │         │
│  │    - 간격 설정 UI                           │         │
│  └────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ (파일 다운로드)
┌─────────────────────────────────────────────────────────┐
│           ~/Downloads/claude-auto-usage.json             │
│  {                                                        │
│    "session": 48,                                        │
│    "weekly": 31,                                         │
│    "sessionResetTime": "1시간 50분 후",                  │
│    "weeklyResetTime": "(화) 오전 10:59에",               │
│    "timestamp": "2025-10-27T09:00:00Z"                  │
│  }                                                        │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ (fswatch 감지)
┌─────────────────────────────────────────────────────────┐
│        ~/.local/bin/claude-extension-watcher            │
│  - fswatch로 Downloads 폴더 모니터링                     │
│  - claude-auto-usage.json 생성되면 즉시 감지             │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ (동기화 실행)
┌─────────────────────────────────────────────────────────┐
│        ~/.local/bin/claude-sync-from-extension          │
│  - JSON 파싱 (session, weekly, reset times)             │
│  - /tmp/claude-web-usage.json 생성                       │
│  - SwiftBar 새로고침 트리거                              │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ (파일 읽기)
┌─────────────────────────────────────────────────────────┐
│        SwiftBar Plugin (ClaudeUsage.1m.sh)              │
│  - 1분마다 실행                                          │
│  - /tmp/claude-web-usage.json 읽기                       │
│  - macOS 메뉴바에 표시                                   │
└─────────────────────────────────────────────────────────┘
```

---

## Chrome Extension 로직

### 1. Service Worker (background.js)

**역할**: 백그라운드에서 자동 스크래핑 스케줄링

```javascript
// 초기화 (Extension 설치 시)
chrome.runtime.onInstalled.addListener(async () => {
  // 1. 저장된 간격 설정 로드 (기본값: 5분)
  const interval = await chrome.storage.local.get('scrapeInterval')

  // 2. chrome.alarms 설정
  chrome.alarms.create('scrapeUsage', {
    periodInMinutes: interval  // 5, 10, 15, 30, 60분 중 선택
  })
})

// 알람 이벤트 (자동 스크래핑)
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'scrapeUsage') {
    scrapeUsageData()  // 스크래핑 실행
  }
})
```

**주요 함수**:

```javascript
async function scrapeUsageData() {
  // 1. claude.ai/settings/usage 탭 열기 (백그라운드)
  const tab = await chrome.tabs.create({
    url: 'https://claude.ai/settings/usage',
    active: false
  })

  // 2. 페이지 로딩 대기 (최대 10초)
  await waitForTabLoad(tab.id)

  // 3. content.js에 메시지 전송 (데이터 추출 요청)
  const response = await chrome.tabs.sendMessage(tab.id, {
    action: 'extractUsage'
  })

  // 4. 탭 닫기
  await chrome.tabs.remove(tab.id)

  // 5. 데이터 저장
  await saveUsageData(response.data)

  // 6. 파일 다운로드 (SwiftBar 연동용)
  await sendToMonitor(response.data)
}

async function saveUsageData(data) {
  // chrome.storage.local에 저장
  await chrome.storage.local.set({
    lastScrape: new Date().toISOString(),
    lastUsage: data,
    status: 'success'
  })

  // Badge 업데이트 (Extension 아이콘에 % 표시)
  await updateBadge(data)
}

async function sendToMonitor(data) {
  // DataURL 방식으로 JSON 파일 다운로드
  const jsonStr = JSON.stringify(data)
  const utf8Bytes = new TextEncoder().encode(jsonStr)
  const base64 = btoa(String.fromCharCode(...utf8Bytes))
  const dataUrl = 'data:application/json;base64,' + base64

  // 다운로드 실행
  await chrome.downloads.download({
    url: dataUrl,
    filename: 'claude-auto-usage.json',
    conflictAction: 'overwrite',
    saveAs: false
  })
}
```

**다운로드 이력 자동 삭제**:

```javascript
chrome.downloads.onChanged.addListener((delta) => {
  if (delta.state && delta.state.current === 'complete') {
    // 다운로드 완료 시 이력에서 제거
    chrome.downloads.erase({ id: delta.id })
  }
})
```

---

### 2. Content Script (content.js)

**역할**: Claude.ai 사용량 페이지에서 데이터 추출

```javascript
// background.js에서 메시지 수신
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'extractUsage') {
    const usageData = extractUsageFromPage()
    sendResponse({
      success: true,
      data: usageData
    })
  }
})

function extractUsageFromPage() {
  // 페이지 전체 텍스트 가져오기
  const pageText = document.body.innerText
  const lines = pageText.split('\n')

  const result = {
    session: null,
    weekly: null,
    sessionResetTime: null,
    weeklyResetTime: null,
    timestamp: new Date().toISOString()
  }

  // 줄별로 검색
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()

    // "Current session" 찾기
    if (line === 'Current session') {
      // 다음 5줄에서 "XX% 사용됨" 패턴 찾기
      for (let j = i + 1; j < i + 6; j++) {
        // Reset time: "3시간 50분 후 재설정"
        const resetMatch = lines[j].match(/(.+)\s*재설정/)
        if (resetMatch) {
          result.sessionResetTime = resetMatch[1].trim()
        }

        // Usage: "48% 사용됨"
        const usageMatch = lines[j].match(/(\d+)%\s*사용/)
        if (usageMatch) {
          result.session = parseInt(usageMatch[1])
        }
      }
    }

    // "All models" 찾기 (Weekly)
    if (line === 'All models') {
      // 동일한 패턴으로 weekly 데이터 추출
      // ...
    }
  }

  return result
}
```

**예상 페이지 구조**:
```
Current session
3시간 50분 후 재설정
48% 사용됨

All models
(화) 오전 10:59에 재설정
31% 사용됨
```

---

### 3. Popup UI (popup.html/js)

**역할**: 사용자 인터페이스

```javascript
// Popup 열릴 때 실행
document.addEventListener('DOMContentLoaded', () => {
  loadStatus()    // 저장된 데이터 로드
  loadInterval()  // 저장된 간격 설정 로드

  // "Scrape Now" 버튼 이벤트
  document.getElementById('scrapeBtn').addEventListener('click', async () => {
    // background.js에 메시지 전송
    await chrome.runtime.sendMessage({ action: 'scrapeNow' })
  })

  // 간격 설정 변경
  document.getElementById('intervalSelect').addEventListener('change', async (e) => {
    const interval = parseInt(e.target.value)

    // 설정 저장
    await chrome.storage.local.set({ scrapeInterval: interval })

    // background.js에 알람 업데이트 요청
    await chrome.runtime.sendMessage({
      action: 'updateInterval',
      interval: interval
    })
  })
})

async function loadStatus() {
  // chrome.storage에서 데이터 읽기
  const response = await chrome.runtime.sendMessage({ action: 'getStatus' })

  // UI 업데이트
  document.getElementById('sessionValue').textContent = response.lastUsage.session + '%'
  document.getElementById('weeklyValue').textContent = response.lastUsage.weekly + '%'
  document.getElementById('sessionResetTime').textContent = response.lastUsage.sessionResetTime
  document.getElementById('weeklyResetTime').textContent = response.lastUsage.weeklyResetTime

  // Last Update 시간 계산
  const date = new Date(response.lastScrape)
  const diff = Math.floor((new Date() - date) / 1000 / 60)
  document.getElementById('lastUpdate').textContent = diff + 'm ago'
}
```

---

## SwiftBar 연동 (macOS)

### 1. File Watcher (claude-extension-watcher)

**역할**: Downloads 폴더 감시

```bash
#!/bin/bash

WATCH_FILE="$HOME/Downloads/claude-auto-usage.json"
SYNC_SCRIPT="$HOME/.local/bin/claude-sync-from-extension"

# fswatch로 Downloads 폴더 모니터링
fswatch -0 \
  -e ".*" \
  -i "claude-auto-usage\\.json$" \
  "$HOME/Downloads" | \
while read -d "" event; do
  if [ -f "$WATCH_FILE" ]; then
    echo "[$(date)] File detected, syncing..."
    "$SYNC_SCRIPT"
  fi
done
```

**작동 방식**:
1. `fswatch`로 `~/Downloads` 폴더 감시
2. `claude-auto-usage.json` 파일 생성 감지
3. 즉시 `claude-sync-from-extension` 실행

---

### 2. Sync Script (claude-sync-from-extension)

**역할**: Extension 데이터 → SwiftBar 형식 변환

```bash
#!/bin/bash

SOURCE_FILE="$HOME/Downloads/claude-auto-usage.json"
DEST_FILE="/tmp/claude-web-usage.json"

# JSON 파싱
SESSION=$(jq -r '.session' "$SOURCE_FILE")
WEEKLY=$(jq -r '.weekly' "$SOURCE_FILE")
SESSION_RESET=$(jq -r '.sessionResetTime // ""' "$SOURCE_FILE")
WEEKLY_RESET=$(jq -r '.weeklyResetTime // ""' "$SOURCE_FILE")

# SwiftBar 형식으로 변환
cat > "$DEST_FILE" << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "source": "chrome_extension",
  "session": {
    "percentage": ${SESSION},
    "reset_time": "${SESSION_RESET}",
    "last_updated": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  },
  "weekly": {
    "percentage": ${WEEKLY},
    "reset_time": "${WEEKLY_RESET}",
    "last_updated": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  }
}
EOF

# 원본 파일 삭제
rm "$SOURCE_FILE"

# SwiftBar 새로고침
open "swiftbar://refreshallplugins"
```

---

### 3. SwiftBar Plugin (ClaudeUsage.1m.sh)

**역할**: 메뉴바에 표시

```bash
#!/usr/bin/env bash

USAGE_FILE="/tmp/claude-web-usage.json"

# 파일 확인
if [[ ! -f "$USAGE_FILE" ]]; then
    echo "⚠️ No Data"
    exit 0
fi

# JSON 파싱
SESSION=$(jq -r '.session.percentage' "$USAGE_FILE")
WEEKLY=$(jq -r '.weekly.percentage' "$USAGE_FILE")
SESSION_RESET=$(jq -r '.session.reset_time' "$USAGE_FILE")
WEEKLY_RESET=$(jq -r '.weekly.reset_time' "$USAGE_FILE")

# 색상 결정
if (( $(echo "$SESSION < 50" | bc -l) )); then
    ICON="🟢"
    COLOR="green"
elif (( $(echo "$SESSION < 80" | bc -l) )); then
    ICON="🟡"
    COLOR="yellow"
else
    ICON="🔴"
    COLOR="red"
fi

# 메뉴바 표시 (이 줄이 메뉴바에 보임)
echo "$ICON ${SESSION}%"

# 구분선
echo "---"

# 드롭다운 메뉴
echo "📊 Session Usage (${SESSION_RESET})"
printf -- "--Current: %s%% | color=%s\n" "$SESSION" "$COLOR"

echo "---"

echo "📈 Weekly Usage (${WEEKLY_RESET})"
printf -- "--Current: %s%%\n" "$WEEKLY"
```

**SwiftBar 형식**:
```
첫 줄: 메뉴바에 표시되는 텍스트
---: 구분선
--로 시작: 드롭다운 메뉴 항목
```

---

## 데이터 흐름

### 전체 타임라인 (5분 간격 설정 시)

```
T=0분
├─ Extension: chrome.alarms 트리거
├─ background.js: scrapeUsageData() 실행
│   ├─ 1. 탭 열기: https://claude.ai/settings/usage
│   ├─ 2. 페이지 로딩 대기 (2초)
│   ├─ 3. content.js 호출: extractUsage
│   ├─ 4. 데이터 반환: {session: 48, weekly: 31, ...}
│   ├─ 5. 탭 닫기
│   ├─ 6. chrome.storage.local 저장
│   ├─ 7. Badge 업데이트 (48%)
│   └─ 8. 파일 다운로드: ~/Downloads/claude-auto-usage.json
│
├─ Watcher: fswatch 감지 (1초 이내)
├─ Sync Script: claude-sync-from-extension 실행
│   ├─ 1. JSON 파싱
│   ├─ 2. /tmp/claude-web-usage.json 생성
│   ├─ 3. 원본 파일 삭제
│   └─ 4. SwiftBar 새로고침
│
└─ SwiftBar: 메뉴바 업데이트 (즉시)
    └─ 🟢 48% 표시

T=1분
└─ SwiftBar: 자동 새로고침 (1분마다)
    └─ /tmp/claude-web-usage.json 다시 읽기

T=5분
└─ Extension: chrome.alarms 다시 트리거
    └─ (위 과정 반복)
```

---

## 주요 함수 설명

### Chrome Extension

#### 1. `scrapeUsageData()`
- **위치**: background.js
- **역할**: 전체 스크래핑 프로세스 관리
- **호출 시점**:
  - chrome.alarms (자동, 5~60분마다)
  - 사용자가 "Scrape Now" 클릭 (수동)

#### 2. `extractUsageFromPage()`
- **위치**: content.js
- **역할**: 페이지에서 사용량 데이터 추출
- **반환값**:
  ```javascript
  {
    session: 48,
    weekly: 31,
    sessionResetTime: "1시간 50분 후",
    weeklyResetTime: "(화) 오전 10:59에",
    timestamp: "2025-10-27T09:00:00Z"
  }
  ```

#### 3. `updateBadge(data)`
- **위치**: background.js
- **역할**: Extension 아이콘에 % 표시
- **색상 로직**:
  - 🟢 녹색: 0-49%
  - 🟡 노란색: 50-79%
  - 🔴 빨간색: 80-100%

#### 4. `updateAlarm(interval)`
- **위치**: background.js
- **역할**: 스크래핑 간격 동적 변경
- **파라미터**: 0, 5, 10, 15, 30, 60 (분)
- **동작**:
  - 0이면: 알람 제거 (Manual only)
  - 그 외: 새 간격으로 알람 재설정

---

### SwiftBar Scripts

#### 1. `claude-extension-watcher`
- **역할**: fswatch로 파일 감시
- **감시 대상**: `~/Downloads/claude-auto-usage.json`
- **감지 시**: `claude-sync-from-extension` 실행

#### 2. `claude-sync-from-extension`
- **역할**: Extension JSON → SwiftBar JSON 변환
- **입력**: `~/Downloads/claude-auto-usage.json`
- **출력**: `/tmp/claude-web-usage.json`
- **추가 동작**:
  - 원본 파일 삭제
  - SwiftBar 새로고침 트리거

#### 3. `ClaudeUsage.1m.sh`
- **역할**: SwiftBar 플러그인
- **실행 주기**: 1분마다
- **데이터 소스**: `/tmp/claude-web-usage.json`
- **출력**: macOS 메뉴바

---

## 설정 및 상태 관리

### chrome.storage.local 저장 데이터

```javascript
{
  // 스크래핑 간격 설정 (분)
  scrapeInterval: 5,  // 5, 10, 15, 30, 60, 0(manual)

  // 마지막 스크래핑 시간
  lastScrape: "2025-10-27T09:00:00Z",

  // 마지막 사용량 데이터
  lastUsage: {
    session: 48,
    weekly: 31,
    sessionResetTime: "1시간 50분 후",
    weeklyResetTime: "(화) 오전 10:59에"
  },

  // 상태
  status: "success"  // 'initialized', 'success', 'error'
}
```

---

## 트러블슈팅

### Extension이 작동하지 않을 때

1. **Service Worker 재시작**
   - `chrome://extensions/` → Extension → "Service Worker" → "검사" → Console 확인

2. **Alarm 확인**
   - Console에서: `chrome.alarms.getAll(console.log)`
   - 출력: `[{name: "scrapeUsage", periodInMinutes: 5}]`

3. **Storage 확인**
   - Console에서: `chrome.storage.local.get(console.log)`

### SwiftBar가 업데이트 안 될 때

1. **Watcher 실행 확인**
   ```bash
   ps aux | grep claude-extension-watcher
   ```

2. **데이터 파일 확인**
   ```bash
   cat /tmp/claude-web-usage.json
   ```

3. **수동 테스트**
   ```bash
   bash ~/Library/Application\ Support/SwiftBar/ClaudeUsage.1m.sh
   ```

---

## 보안 및 프라이버시

### 데이터 저장 위치

- **Chrome Extension**: `chrome.storage.local` (브라우저 내부)
- **임시 파일**: `/tmp/claude-web-usage.json` (로컬)
- **다운로드 파일**: `~/Downloads/claude-auto-usage.json` (즉시 삭제)

### 외부 통신

- ❌ 외부 서버 전송 없음
- ✅ 오직 `https://claude.ai/settings/usage` 접근
- ✅ 로컬 데이터만 사용

### 권한 최소화

- `storage`: 로컬 저장
- `alarms`: 스케줄링
- `activeTab`: 현재 탭 접근
- `downloads`: 파일 다운로드
- `host_permissions`: claude.ai만 접근

---

## 성능 최적화

### 1. 다운로드 이력 자동 삭제
```javascript
// 다운로드 완료 시 Chrome 이력에서 자동 제거
chrome.downloads.onChanged.addListener((delta) => {
  if (delta.state.current === 'complete') {
    chrome.downloads.erase({ id: delta.id })
  }
})
```

### 2. 백그라운드 탭 사용
```javascript
// 사용자에게 보이지 않게 탭 열기
chrome.tabs.create({
  url: '...',
  active: false  // 백그라운드
})
```

### 3. 파일 기반 IPC
- Native Messaging 대신 파일 기반 통신 사용
- 더 간단하고 안정적

---

## 버전 관리

### Semantic Versioning

- **1.0.0**: 초기 릴리스
- **1.1.0**: 간격 설정 기능 추가
- **1.1.1**: 1시간 옵션 추가
- **1.1.2**: tabs 권한 제거

### 업데이트 시 주의사항

1. **manifest.json 버전 업데이트 필수**
2. **Chrome Web Store에 새 ZIP 업로드**
3. **권한 변경 시 재심사 필요**
