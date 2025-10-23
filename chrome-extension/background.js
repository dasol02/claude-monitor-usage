/**
 * Chrome Extension Background Service Worker
 * 5분마다 Claude usage를 자동으로 스크래핑하여 로컬 monitor에 전송
 */

// 설정
const CONFIG = {
  SCRAPE_INTERVAL: 5, // 5분마다
  USAGE_URL: 'https://claude.ai/settings/usage',
  MONITOR_SCRIPT: '/Users/dasollee/.local/bin/claude-auto-update-usage'
};

// Extension 설치 시 초기화
chrome.runtime.onInstalled.addListener(() => {
  console.log('Claude Usage Monitor Extension installed');

  // 5분마다 알람 설정
  chrome.alarms.create('scrapeUsage', {
    periodInMinutes: CONFIG.SCRAPE_INTERVAL
  });

  // 초기 상태 저장
  chrome.storage.local.set({
    lastScrape: null,
    lastUsage: { session: null, weekly: null },
    status: 'initialized'
  });
});

// 알람 이벤트 처리 (5분마다 실행)
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'scrapeUsage') {
    console.log('Alarm triggered: scraping usage...');
    scrapeUsageData();
  }
});

// Usage 데이터 스크래핑
async function scrapeUsageData() {
  try {
    console.log('Opening usage page...');

    // Usage 페이지를 새 탭에서 열기 (백그라운드)
    const tab = await chrome.tabs.create({
      url: CONFIG.USAGE_URL,
      active: false // 백그라운드에서 열기
    });

    // 페이지 로딩 대기
    await waitForTabLoad(tab.id);

    // Content script에 메시지 전송하여 데이터 추출
    const response = await chrome.tabs.sendMessage(tab.id, {
      action: 'extractUsage'
    });

    console.log('Usage data received:', response);

    // 탭 닫기
    await chrome.tabs.remove(tab.id);

    // 데이터 저장
    if (response && response.success) {
      await saveUsageData(response.data);

      // Native messaging으로 Python 스크립트 호출
      await sendToMonitor(response.data);
    }

  } catch (error) {
    console.error('Failed to scrape usage:', error);

    chrome.storage.local.set({
      status: 'error',
      lastError: error.message
    });
  }
}

// 탭 로딩 대기
function waitForTabLoad(tabId, timeout = 10000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error('Tab load timeout'));
    }, timeout);

    chrome.tabs.onUpdated.addListener(function listener(id, info) {
      if (id === tabId && info.status === 'complete') {
        clearTimeout(timer);
        chrome.tabs.onUpdated.removeListener(listener);
        // 추가 대기 (페이지 렌더링)
        setTimeout(() => resolve(), 2000);
      }
    });
  });
}

// Usage 데이터 저장
async function saveUsageData(data) {
  await chrome.storage.local.set({
    lastScrape: new Date().toISOString(),
    lastUsage: data,
    status: 'success'
  });

  console.log('Usage data saved:', data);

  // Badge 업데이트
  await updateBadge(data);
}

// Monitor에 데이터 전송
async function sendToMonitor(data) {
  try {
    // 방법 1: Native messaging 사용
    // (manifest.json에 nativeMessaging 권한 필요)

    // 방법 2: 파일 시스템 사용 (더 간단)
    // JSON 파일로 저장하고 Python이 읽도록

    console.log('Sending to monitor:', data);

    // Chrome extension은 직접 파일 쓰기 불가
    // → Downloads API + Data URL 사용
    const jsonStr = JSON.stringify(data);
    // Service Worker에서는 URL.createObjectURL 사용 불가
    // Data URL 방식 사용 (UTF-8 → base64)
    const utf8Bytes = new TextEncoder().encode(jsonStr);
    const base64 = btoa(String.fromCharCode(...utf8Bytes));
    const dataUrl = 'data:application/json;base64,' + base64;

    // 자동 다운로드 (사용자 개입 없음)
    await chrome.downloads.download({
      url: dataUrl,
      filename: 'claude-auto-usage.json',
      conflictAction: 'overwrite',
      saveAs: false
    });

    console.log('Usage data written to file');

  } catch (error) {
    console.error('Failed to send to monitor:', error);
  }
}

// Badge 업데이트 함수
async function updateBadge(usage) {
  if (!usage || usage.session === null) {
    // 데이터 없음
    chrome.action.setBadgeText({ text: '?' });
    chrome.action.setBadgeBackgroundColor({ color: '#94a3b8' });
    chrome.action.setTitle({ title: 'Claude Usage Monitor - No data' });
    return;
  }

  const sessionPercent = usage.session;
  const weeklyPercent = usage.weekly || 0;

  // Badge 텍스트 설정
  chrome.action.setBadgeText({ text: sessionPercent + '%' });

  // 색상 설정 (사용량에 따라)
  let color;
  if (sessionPercent < 50) {
    color = '#22c55e'; // Green
  } else if (sessionPercent < 80) {
    color = '#eab308'; // Yellow
  } else {
    color = '#ef4444'; // Red
  }
  chrome.action.setBadgeBackgroundColor({ color });

  // Tooltip 설정
  const tooltip = `Claude Usage Monitor\n━━━━━━━━━━━━━━━━\nSession: ${sessionPercent}%\nWeekly: ${weeklyPercent}%\n━━━━━━━━━━━━━━━━\nClick for details`;
  chrome.action.setTitle({ title: tooltip });

  console.log(`Badge updated: ${sessionPercent}% (${color})`);
}

// 초기 Badge 설정 (Extension 로드 시)
async function initBadge() {
  const result = await chrome.storage.local.get(['lastUsage']);
  if (result.lastUsage) {
    await updateBadge(result.lastUsage);
  } else {
    // 초기 상태
    chrome.action.setBadgeText({ text: '?' });
    chrome.action.setBadgeBackgroundColor({ color: '#94a3b8' });
    chrome.action.setTitle({ title: 'Claude Usage Monitor - Waiting for first scrape...' });
  }
}

// Extension 로드 시 Badge 초기화
chrome.runtime.onStartup.addListener(() => {
  initBadge();
});

// Badge 초기화 (최초 실행)
initBadge();

// 다운로드 완료 시 이력 자동 삭제
chrome.downloads.onChanged.addListener((delta) => {
  if (delta.state && delta.state.current === 'complete') {
    // 다운로드 완료되면 Chrome 다운로드 목록에서 제거
    chrome.downloads.erase({ id: delta.id });
    console.log('Download history cleaned:', delta.id);
  }
});

// 수동 스크래핑 (popup에서 호출)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'scrapeNow') {
    scrapeUsageData().then(() => {
      sendResponse({ success: true });
    }).catch(error => {
      sendResponse({ success: false, error: error.message });
    });
    return true; // 비동기 응답
  }

  if (request.action === 'getStatus') {
    chrome.storage.local.get(['lastScrape', 'lastUsage', 'status'], (result) => {
      sendResponse(result);
    });
    return true;
  }
});

console.log('Claude Usage Monitor Background Script loaded');
