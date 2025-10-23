# Claude Usage Monitor - Chrome Extension

Chrome Extension으로 Claude Team 사용량을 자동으로 스크래핑합니다.

## 🎯 기능

- 📊 **자동 스크래핑**: 5분마다 자동 스크래핑
- 🔘 **수동 스크래핑**: "Scrape Now" 버튼
- 🟢 **Badge 표시**: Extension 아이콘에 % 표시
- 💾 **자동 저장**: 로컬 storage에 데이터 저장
- 📥 **파일 다운로드**: DataURL 방식으로 JSON 파일 생성

## 📦 설치

1. Chrome 열기
2. `chrome://extensions/` 접속
3. **개발자 모드** 켜기
4. **압축해제된 확장 프로그램을 로드합니다** 클릭
5. 이 폴더(`chrome-extension`) 선택

## 💡 사용

### Popup 사용
1. Extension 아이콘 클릭
2. 현재 사용량 확인
3. "Scrape Now" 버튼으로 업데이트

### Badge 확인
- Extension 아이콘에 Session % 표시
- 색상: 녹색(0-49%), 노란색(50-79%), 빨간색(80-100%)

## 🔧 작동 방식

### 1. 스크래핑
```
사용자 클릭 "Scrape Now"
    ↓
https://claude.ai/settings/usage 페이지 열기
    ↓
Content Script로 데이터 추출
    ↓
Session % 및 Weekly % 파싱
```

### 2. 저장
```
데이터 추출
    ↓
chrome.storage.local에 저장
    ↓
Badge 업데이트
```

### 3. 파일 생성 (SwiftBar 연동용)
```
데이터 추출
    ↓
JSON 문자열 생성
    ↓
DataURL로 변환
    ↓
chrome.downloads.download()
    ↓
~/Downloads/claude-auto-usage.json 생성
```

## 📁 파일 구조

```
chrome-extension/
├── manifest.json       # Extension 설정
├── background.js       # Service Worker (백그라운드)
├── content.js          # 페이지 스크래핑
├── popup.html          # Popup UI
├── popup.js            # Popup 로직
├── icon16.png          # 아이콘 16x16
├── icon48.png          # 아이콘 48x48
└── icon128.png         # 아이콘 128x128
```

## 🔍 디버깅

### Service Worker Console
1. `chrome://extensions/` 접속
2. 개발자 모드 ON
3. "Claude Usage Monitor" 찾기
4. "Service Worker" → "검사" 클릭
5. Console 탭에서 로그 확인

### Extension ID 확인
1. `chrome://extensions/` 접속
2. 개발자 모드 ON
3. Extension ID 복사

## 🐛 문제 해결

### "Failed to send to monitor" 에러
- Service Worker Console 확인
- DataURL 생성 오류일 수 있음
- JSON 데이터 확인

### 스크래핑이 작동하지 않음
- `https://claude.ai/settings/usage` 페이지가 열리는지 확인
- Content script가 로드되는지 확인
- 페이지 구조 변경 여부 확인 (content.js 업데이트 필요)

### 파일이 다운로드되지 않음
- Chrome 다운로드 권한 확인
- DataURL 방식이 정상 작동하는지 확인
- Service Worker Console에서 에러 확인

## 📖 기술 스택

- **Manifest V3**: 최신 Chrome Extension API
- **Service Worker**: background.js
- **Content Script**: 페이지 데이터 추출
- **Downloads API**: 파일 저장
- **Storage API**: 로컬 데이터 저장

## 📝 라이센스

MIT License
