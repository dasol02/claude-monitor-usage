# Chrome Extension 업데이트 가이드

## 🎯 새로운 기능: Toolbar Badge

Extension 아이콘에 실시간 사용량이 표시됩니다!

### 기능
- **아이콘 배지**: Session 사용량 % 표시 (예: "17%")
- **색상 코드**:
  - 🟢 초록색: 0-49% (안전)
  - 🟡 노란색: 50-79% (주의)
  - 🔴 빨간색: 80-100% (위험)
- **Tooltip**: 마우스 오버 시 Session/Weekly 모두 표시

## 📦 업데이트 방법

### 1. Chrome Extension 새로고침

```
1. Chrome 열기
2. chrome://extensions/ 접속
3. "Claude Usage Monitor" 찾기
4. 새로고침 버튼 (🔄) 클릭
```

### 2. 즉시 확인

Extension이 새로고침되면:
- ❓ "?" 표시 → 아직 데이터 없음
- 몇 초 후 "Scrape Now" 버튼 클릭
- ✅ "17%" 같은 퍼센트 표시됨

### 3. 마우스 오버

Extension 아이콘에 마우스 올리면:
```
Claude Usage Monitor
━━━━━━━━━━━━━━━━
Session: 17%
Weekly: 17%
━━━━━━━━━━━━━━━━
Click for details
```

## 🔄 자동 업데이트

5분마다:
1. 자동 스크래핑
2. Badge 자동 업데이트
3. 색상 자동 변경

## 🎨 색상 의미

| 색상 | 범위 | 상태 | 의미 |
|------|------|------|------|
| 🟢 초록 | 0-49% | Safe | 여유있음 |
| 🟡 노랑 | 50-79% | Warning | 주의 필요 |
| 🔴 빨강 | 80-100% | Danger | 곧 한도 도달 |

## 📊 실시간 모니터링

이제 Chrome을 사용하는 동안:
- 브라우저 툴바에서 항상 사용량 확인 가능
- Mac StatusBar + Chrome 동시 모니터링
- 80% 넘으면 빨간색으로 즉시 알림

## 🐛 문제 해결

### Badge가 "?"로 표시됨
- 아직 데이터가 없음
- "Scrape Now" 버튼 클릭

### Badge가 업데이트 안 됨
- Extension 새로고침 (🔄)
- Chrome 재시작

### 색상이 안 보임
- Extension 아이콘 확인
- Badge가 표시되지 않으면 재설치

## ✨ 사용 팁

1. **빠른 확인**: 툴바에서 한 눈에 확인
2. **상세 정보**: 아이콘 클릭 → Popup
3. **마우스 오버**: Session + Weekly 동시 확인
4. **색상 모니터링**: 빨간색 되면 사용 줄이기

## 🎯 다음 단계

이제 완전 자동화 완성!
- ✅ Chrome Extension: 5분마다 자동 스크래핑
- ✅ Toolbar Badge: 실시간 표시
- ✅ Mac StatusBar: SwiftBar 표시
- ✅ 완전 자동화: 수동 입력 불필요!
