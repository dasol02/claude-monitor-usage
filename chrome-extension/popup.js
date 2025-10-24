/**
 * Popup UI Script
 */

document.addEventListener('DOMContentLoaded', () => {
  loadStatus();
  loadInterval();

  // Interval 설정 변경
  document.getElementById('intervalSelect').addEventListener('change', async (e) => {
    const interval = parseInt(e.target.value);
    await chrome.storage.local.set({ scrapeInterval: interval });
    await chrome.runtime.sendMessage({ action: 'updateInterval', interval: interval });
    console.log('Scrape interval updated to:', interval, 'minutes');
  });

  // Scrape Now 버튼
  document.getElementById('scrapeBtn').addEventListener('click', async () => {
    const btn = document.getElementById('scrapeBtn');
    btn.disabled = true;
    btn.textContent = '⏳ Scraping...';

    try {
      const response = await chrome.runtime.sendMessage({ action: 'scrapeNow' });

      if (response.success) {
        btn.textContent = '✅ Done!';
        setTimeout(() => {
          btn.textContent = '🔄 Scrape Now';
          btn.disabled = false;
          loadStatus();
        }, 2000);
      } else {
        throw new Error(response.error);
      }
    } catch (error) {
      btn.textContent = '❌ Failed';
      alert('Failed to scrape: ' + error.message);
      setTimeout(() => {
        btn.textContent = '🔄 Scrape Now';
        btn.disabled = false;
      }, 2000);
    }
  });

  // Open Usage Page 버튼
  document.getElementById('openUsageBtn').addEventListener('click', () => {
    chrome.tabs.create({
      url: 'https://claude.ai/settings/usage'
    });
  });
});

// 상태 로드
async function loadStatus() {
  try {
    const response = await chrome.runtime.sendMessage({ action: 'getStatus' });

    // Status
    const statusText = document.getElementById('statusText');
    if (response.status === 'success') {
      statusText.textContent = '✅ Active';
      statusText.className = 'value success';
    } else if (response.status === 'error') {
      statusText.textContent = '❌ Error';
      statusText.className = 'value error';
    } else {
      statusText.textContent = '⚠️ Waiting';
      statusText.className = 'value';
    }

    // Session & Weekly
    if (response.lastUsage) {
      document.getElementById('sessionValue').textContent =
        response.lastUsage.session !== null ? response.lastUsage.session + '%' : '--';
      document.getElementById('weeklyValue').textContent =
        response.lastUsage.weekly !== null ? response.lastUsage.weekly + '%' : '--';

      // Reset times (no icon)
      document.getElementById('sessionResetTime').textContent =
        response.lastUsage.sessionResetTime || '';
      document.getElementById('weeklyResetTime').textContent =
        response.lastUsage.weeklyResetTime || '';
    }

    // Last Update
    if (response.lastScrape) {
      const date = new Date(response.lastScrape);
      const now = new Date();
      const diff = Math.floor((now - date) / 1000 / 60); // minutes

      if (diff < 1) {
        document.getElementById('lastUpdate').textContent = 'Just now';
      } else if (diff < 60) {
        document.getElementById('lastUpdate').textContent = diff + 'm ago';
      } else {
        document.getElementById('lastUpdate').textContent = date.toLocaleTimeString();
      }
    }

  } catch (error) {
    console.error('Failed to load status:', error);
  }
}

// Interval 설정 로드
async function loadInterval() {
  try {
    const result = await chrome.storage.local.get(['scrapeInterval']);
    const interval = result.scrapeInterval !== undefined ? result.scrapeInterval : 5;
    document.getElementById('intervalSelect').value = interval;
  } catch (error) {
    console.error('Failed to load interval:', error);
  }
}
