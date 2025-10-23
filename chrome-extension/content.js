/**
 * Content Script - Claude Usage 페이지에서 실행
 * 페이지의 사용량 데이터를 추출
 */

console.log('Claude Usage Monitor - Content Script loaded');

// Background script로부터 메시지 수신
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'extractUsage') {
    console.log('Extracting usage data...');

    try {
      const usageData = extractUsageFromPage();
      console.log('Extracted usage data:', usageData);

      sendResponse({
        success: true,
        data: usageData
      });
    } catch (error) {
      console.error('Failed to extract usage:', error);
      sendResponse({
        success: false,
        error: error.message
      });
    }
  }

  return true; // 비동기 응답 유지
});

/**
 * 페이지에서 Usage 데이터 추출
 *
 * 예상 구조:
 * Current session
 * 3시간 50분 후 재설정
 * 17% 사용됨
 *
 * All models
 * (화) 오전 10:59에 재설정
 * 17% 사용됨
 */
function extractUsageFromPage() {
  const pageText = document.body.innerText;
  const lines = pageText.split('\n');

  const result = {
    session: null,
    weekly: null,
    sessionResetTime: null,
    weeklyResetTime: null,
    timestamp: new Date().toISOString()
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Session 사용량 및 재설정 시간 찾기
    if (line === 'Current session') {
      // 다음 5줄에서 재설정 시간과 사용량 찾기
      for (let j = i + 1; j < Math.min(i + 6, lines.length); j++) {
        const resetMatch = lines[j].match(/(.+)\s*재설정/);
        if (resetMatch && !result.sessionResetTime) {
          result.sessionResetTime = resetMatch[1].trim();
          console.log('Found session reset time:', result.sessionResetTime);
        }

        const usageMatch = lines[j].match(/(\d+)%\s*사용/);
        if (usageMatch && !result.session) {
          result.session = parseInt(usageMatch[1]);
          console.log('Found session:', result.session + '%');
        }
      }
    }

    // Weekly 사용량 및 재설정 시간 찾기
    if (line === 'All models') {
      // 다음 5줄에서 재설정 시간과 사용량 찾기
      for (let j = i + 1; j < Math.min(i + 6, lines.length); j++) {
        const resetMatch = lines[j].match(/(.+)\s*재설정/);
        if (resetMatch && !result.weeklyResetTime) {
          result.weeklyResetTime = resetMatch[1].trim();
          console.log('Found weekly reset time:', result.weeklyResetTime);
        }

        const usageMatch = lines[j].match(/(\d+)%\s*사용/);
        if (usageMatch && !result.weekly) {
          result.weekly = parseInt(usageMatch[1]);
          console.log('Found weekly:', result.weekly + '%');
        }
      }
    }
  }

  // 검증
  if (result.session === null || result.weekly === null) {
    throw new Error('Failed to extract usage data from page');
  }

  return result;
}

// 페이지 로드 시 자동 실행 (선택사항)
if (document.readyState === 'complete') {
  console.log('Page loaded, ready to extract usage');
} else {
  window.addEventListener('load', () => {
    console.log('Page loaded, ready to extract usage');
  });
}
