# Claude Usage Monitor - Chrome Extension

Chrome Extension으로 claude.ai의 사용량을 자동으로 스크래핑하여 로컬 모니터에 전송합니다.

## ✨ 기능

- 🔄 **자동 스크래핑**: 5분마다 자동으로 사용량 확인
- 🎯 **백그라운드 실행**: 브라우저가 열려있으면 자동 작동
- 📊 **실시간 업데이트**: 스크래핑된 데이터를 모니터에 자동 전송
- 🖱️ **수동 스크래핑**: 필요시 버튼 클릭으로 즉시 업데이트

## 📦 설치 방법

### 1. Extension 설치

1. Chrome 열기
2. 주소창에 `chrome://extensions/` 입력
3. 우측 상단 "개발자 모드" 활성화
4. "압축해제된 확장 프로그램을 로드합니다" 클릭
5. `/Users/dasollee/claude-monitor/chrome-extension` 폴더 선택

### 2. 권한 설정

Extension 설치 후 자동으로 필요한 권한을 요청합니다:
- ✅ `https://claude.ai/*` - Claude.ai 접근
- ✅ Storage - 데이터 저장
- ✅ Alarms - 주기적 실행
- ✅ Downloads - 데이터 파일 저장

### 3. 로그인 확인

- Chrome에서 https://claude.ai 접속 후 로그인
- 로그인 상태 유지 (쿠키)

## 🚀 사용 방법

### 자동 모드 (권장)

Extension 설치 후 아무것도 하지 않아도 5분마다 자동으로:
1. Usage 페이지 열기 (백그라운드)
2. 사용량 데이터 추출
3. 로컬 파일에 저장 (`~/.claude-monitor/auto-usage.json`)
4. 탭 자동 닫기

### 수동 모드

1. Chrome 우측 상단 Extension 아이콘 클릭
2. "🔄 Scrape Now" 버튼 클릭
3. 몇 초 후 결과 확인

## 📂 데이터 구조

스크래핑된 데이터는 JSON 형식으로 저장됩니다:

```json
{
  "session": 17,
  "weekly": 17,
  "timestamp": "2025-10-22T15:30:00.000Z"
}
```

저장 위치: `~/Downloads/.claude-monitor/auto-usage.json`

## 🔧 Monitor 연동

### 자동 연동 스크립트

`~/.local/bin/claude-auto-update-usage` 생성:

```bash
#!/bin/bash
# Chrome Extension에서 생성한 usage 파일을 읽어서 자동 calibration

USAGE_FILE="$HOME/Downloads/.claude-monitor/auto-usage.json"

if [ -f "$USAGE_FILE" ]; then
    # JSON 파싱
    SESSION=$(jq -r '.session' "$USAGE_FILE")
    WEEKLY=$(jq -r '.weekly' "$USAGE_FILE")

    if [ "$SESSION" != "null" ] && [ "$WEEKLY" != "null" ]; then
        echo "📊 Auto-updating usage: Session=$SESSION%, Weekly=$WEEKLY%"
        claude-calibrate $SESSION $WEEKLY

        # 파일 삭제 (처리 완료)
        rm "$USAGE_FILE"
    fi
fi
```

```bash
chmod +x ~/.local/bin/claude-auto-update-usage
```

### Cron으로 자동 확인 (선택사항)

```bash
# 1분마다 usage 파일 확인
* * * * * ~/.local/bin/claude-auto-update-usage
```

## 🐛 트러블슈팅

### Extension이 작동하지 않음

1. Chrome에서 `chrome://extensions/` 열기
2. "Claude Usage Monitor" 찾기
3. "세부정보" 클릭
4. "백그라운드 페이지" 확인 (활성 상태여야 함)
5. 콘솔에서 에러 확인

### 로그인 필요 에러

- Chrome에서 https://claude.ai 접속
- 로그인 후 재시도

### 데이터가 추출되지 않음

1. Extension 아이콘 클릭 → "📊 Open Usage Page"
2. 페이지에서 "Current session"과 "All models" 텍스트 확인
3. 페이지 구조가 변경되었으면 `content.js` 업데이트 필요

## 📊 작동 확인

### 1. Extension Popup 확인
- Extension 아이콘 클릭
- Status: ✅ Active
- Session/Weekly 값 표시
- Last Update 시간 확인

### 2. 로그 확인
```bash
# Extension 콘솔 (chrome://extensions/)
# Background page → Console 확인

# Monitor 로그
tail -f ~/.claude-monitor/monitor.log
```

### 3. 수동 테스트
```bash
# Extension에서 "Scrape Now" 클릭
# 다운로드 폴더 확인
ls -la ~/Downloads/.claude-monitor/auto-usage.json
cat ~/Downloads/.claude-monitor/auto-usage.json
```

## 🔄 업데이트

Extension 코드 수정 후:
1. `chrome://extensions/` 열기
2. "Claude Usage Monitor" 찾기
3. 새로고침 버튼 (🔄) 클릭

## 📝 파일 구조

```
chrome-extension/
├── manifest.json       # Extension 설정
├── background.js       # 백그라운드 서비스 워커 (스크래핑 로직)
├── content.js         # Usage 페이지에서 실행 (데이터 추출)
├── popup.html         # Extension 팝업 UI
├── popup.js          # 팝업 로직
├── icon16.png        # 아이콘 16x16
├── icon48.png        # 아이콘 48x48
├── icon128.png       # 아이콘 128x128
└── README.md         # 이 파일
```

## ⚙️ 설정 변경

### 스크래핑 주기 변경

`background.js` 수정:

```javascript
const CONFIG = {
  SCRAPE_INTERVAL: 5, // 5분 → 원하는 시간(분)으로 변경
  // ...
};
```

변경 후 Extension 새로고침 필요.

## 🎯 다음 단계

1. ✅ Extension 설치 및 테스트
2. ✅ 자동 스크래핑 확인 (5분 대기)
3. ✅ Monitor 연동 스크립트 설정
4. ✅ Cron 설정 (선택)
5. ✅ 완전 자동화 완성!

## 📞 문제 해결

문제가 발생하면:
1. Extension 콘솔 확인
2. Usage 페이지 수동 접속하여 구조 확인
3. `content.js`의 파싱 로직 디버그
