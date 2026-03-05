// sidepanel.js — UI logic for the QA Bug Replay side panel
//
// Capture is started by clicking the extension icon (action.onClicked in SW).
// This panel only handles: stop, save-bug, and display.

const $ = (id) => document.getElementById(id);

let isCapturing = false;
let hasBuffer = false;
let elapsedSec = 0;
let displayTimer = null;
let consoleCount = 0;
let networkCount = 0;
let savedClips = [];
let activeTab = 'console';
let filterErrorsOnly = false;

// ============================================================
// UI Helpers
// ============================================================

function setStatus(state, label) {
  $('statusDot').className = 'status-dot ' + state;
  $('statusLabel').textContent = label || {
    idle: '待機中',
    ready: '録画中 — 保存可能',
    saving: '保存中...',
  }[state] || '';
}

function updateBufferDisplay(sec) {
  $('bufferTime').textContent = `${sec}s`;
  $('bufferFill').style.width = '100%';
}

function setGuideVisible(visible) {
  $('guideBanner').style.display = visible ? 'block' : 'none';
}

function activityLog(msg, type = '') {
  const t = new Date().toLocaleTimeString('ja-JP');
  const el = document.createElement('div');
  el.className = 'log-entry';
  el.innerHTML = `<span class="log-time">${t}</span><span class="log-msg ${type}">${msg}</span>`;
  $('activityLog').appendChild(el);
  $('activityLog').scrollTop = $('activityLog').scrollHeight;
}

function formatTime(ts) {
  const d = new Date(ts);
  return d.toLocaleTimeString('ja-JP', { hour12: false });
}

function truncateUrl(url, maxLen = 60) {
  if (!url || url.length <= maxLen) return url;
  return url.substring(0, maxLen - 3) + '...';
}

// ============================================================
// Console log rendering
// ============================================================

function addConsoleEntry(entry) {
  consoleCount++;
  updateBadgeCounts();

  const panel = $('consolePanel');
  const el = document.createElement('div');
  el.className = 'log-entry';

  const level = entry.level || 'log';
  el.dataset.level = level;
  const args = Array.isArray(entry.args) ? entry.args.join(' ') : String(entry.args);
  const time = formatTime(entry.timestamp);

  el.innerHTML = `<span class="log-time">${time}</span><span class="log-msg ${level}">${escapeHtml(args)}</span>`;

  // Click to copy individual entry
  el.style.cursor = 'pointer';
  el.title = 'クリックでコピー';
  el.addEventListener('click', () => {
    const text = `[${time}] [${level.toUpperCase()}] ${args}`;
    copyToClipboard(text);
    flashCopied(el);
  });

  // Apply filter if active
  if (filterErrorsOnly && level !== 'error' && level !== 'warn') {
    el.classList.add('filtered-out');
  }

  panel.appendChild(el);
  panel.scrollTop = panel.scrollHeight;
}

// ============================================================
// Network log rendering
// ============================================================

function addNetworkEntry(entry) {
  if (!entry) return;
  networkCount++;
  updateBadgeCounts();

  const panel = $('networkPanel');
  const el = document.createElement('div');
  el.className = 'net-entry';

  const status = entry.statusCode || (entry.error ? 'ERR' : '...');
  let statusClass = 'ok';
  const isError = entry.error || (entry.statusCode && entry.statusCode >= 400);
  if (isError) statusClass = 'error';
  else if (entry.statusCode && entry.statusCode >= 300) statusClass = 'redirect';

  el.dataset.isError = isError ? '1' : '0';

  const duration = entry.duration != null ? `${entry.duration}ms` : '';
  const method = entry.method || 'GET';
  const url = truncateUrl(entry.url || '', 80);
  const type = entry.resourceType || '';

  el.innerHTML = `
    <span class="net-status ${statusClass}">${status}</span>
    <span class="net-method">${method}</span>
    <span class="net-url" title="${escapeHtml(entry.url || '')}">${escapeHtml(url)}</span>
    <span class="net-duration">${duration}</span>
    <span class="net-type">${type}</span>
  `;

  // Click to copy individual entry
  el.style.cursor = 'pointer';
  el.title = 'クリックでコピー';
  el.addEventListener('click', () => {
    const text = `[${status}] ${method} ${entry.url || ''} (${duration})`;
    copyToClipboard(text);
    flashCopied(el);
  });

  // Apply filter if active
  if (filterErrorsOnly && !isError) {
    el.classList.add('filtered-out');
  }

  panel.appendChild(el);
  panel.scrollTop = panel.scrollHeight;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// ============================================================
// Clipboard helpers
// ============================================================

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

function flashCopied(el) {
  el.style.outline = '1px solid var(--green)';
  setTimeout(() => { el.style.outline = ''; }, 600);
}

// ============================================================
// Copy all logs in current tab
// ============================================================

function copyCurrentLogs() {
  let text = '';
  if (activeTab === 'console') {
    const entries = $('consolePanel').querySelectorAll('.log-entry');
    const lines = [];
    entries.forEach(el => {
      if (filterErrorsOnly && el.classList.contains('filtered-out')) return;
      const time = el.querySelector('.log-time')?.textContent || '';
      const level = el.dataset.level || 'log';
      const msg = el.querySelector('.log-msg')?.textContent || '';
      lines.push(`[${time}] [${level.toUpperCase()}] ${msg}`);
    });
    text = lines.join('\n');
  } else {
    const entries = $('networkPanel').querySelectorAll('.net-entry');
    const lines = [];
    entries.forEach(el => {
      if (filterErrorsOnly && el.classList.contains('filtered-out')) return;
      const status = el.querySelector('.net-status')?.textContent || '';
      const method = el.querySelector('.net-method')?.textContent || '';
      const url = el.querySelector('.net-url')?.getAttribute('title') || '';
      const dur = el.querySelector('.net-duration')?.textContent || '';
      lines.push(`[${status}] ${method} ${url} (${dur})`);
    });
    text = lines.join('\n');
  }

  if (!text) {
    text = '(ログがありません)';
  }

  copyToClipboard(text).then(() => {
    const btn = $('btnCopyLog');
    btn.textContent = 'コピー済み ✓';
    btn.classList.add('copied');
    setTimeout(() => {
      btn.textContent = '📋 コピー';
      btn.classList.remove('copied');
    }, 1500);
  });
}

// ============================================================
// Error filter
// ============================================================

function toggleErrorFilter() {
  filterErrorsOnly = !filterErrorsOnly;
  $('btnFilter').classList.toggle('active', filterErrorsOnly);

  // Apply/remove filter on console entries
  $('consolePanel').querySelectorAll('.log-entry').forEach(el => {
    const level = el.dataset.level || 'log';
    if (filterErrorsOnly && level !== 'error' && level !== 'warn') {
      el.classList.add('filtered-out');
    } else {
      el.classList.remove('filtered-out');
    }
  });

  // Apply/remove filter on network entries
  $('networkPanel').querySelectorAll('.net-entry').forEach(el => {
    if (filterErrorsOnly && el.dataset.isError !== '1') {
      el.classList.add('filtered-out');
    } else {
      el.classList.remove('filtered-out');
    }
  });

  updateBadgeCounts();
}

function updateBadgeCounts() {
  if (filterErrorsOnly) {
    const consoleVisible = $('consolePanel').querySelectorAll('.log-entry:not(.filtered-out)').length;
    const networkVisible = $('networkPanel').querySelectorAll('.net-entry:not(.filtered-out)').length;
    $('consoleBadge').textContent = consoleVisible;
    $('networkBadge').textContent = networkVisible;
  } else {
    $('consoleBadge').textContent = consoleCount;
    $('networkBadge').textContent = networkCount;
  }
}

// ============================================================
// Tab switching
// ============================================================

$('tabConsole').addEventListener('click', () => switchTab('console'));
$('tabNetwork').addEventListener('click', () => switchTab('network'));

function switchTab(tab) {
  activeTab = tab;
  $('tabConsole').classList.toggle('active', tab === 'console');
  $('tabNetwork').classList.toggle('active', tab === 'network');
  $('consolePanel').classList.toggle('hidden', tab !== 'console');
  $('networkPanel').classList.toggle('hidden', tab !== 'network');
}

// ============================================================
// Button handlers
// ============================================================

$('btnStop').addEventListener('click', () => {
  chrome.runtime.sendMessage({ type: 'stop-capture' }, () => {
    onCaptureStopped();
  });
});

// Copy log button
$('btnCopyLog').addEventListener('click', () => copyCurrentLogs());

// Filter toggle button
$('btnFilter').addEventListener('click', () => toggleErrorFilter());

// Bug button → immediately save
$('btnBug').addEventListener('click', () => {
  if (!isCapturing || !hasBuffer) return;
  $('btnBug').disabled = true;
  setStatus('saving');
  activityLog('バグクリップを保存中...', 'warn');
  chrome.runtime.sendMessage({ type: 'save-bug' });
});

// ============================================================
// Notification banner
// ============================================================

function showNotifyBanner(title, files) {
  const banner = $('notifyBanner');
  banner.innerHTML = `
    <div class="notify-title">${escapeHtml(title)}</div>
    <div class="notify-files">${files.map(f => escapeHtml(f)).join('<br>')}</div>
  `;
  banner.classList.remove('hidden', 'fade-out');
  setTimeout(() => {
    banner.classList.add('fade-out');
    setTimeout(() => banner.classList.add('hidden'), 500);
  }, 3000);
}

// ============================================================
// Capture state transitions
// ============================================================

function onCaptureStarted(tabUrl) {
  isCapturing = true;
  hasBuffer = true;
  elapsedSec = 0;

  setGuideVisible(false);
  setStatus('ready');
  $('btnStop').disabled = false;
  $('btnBug').disabled = false;

  // Clear log panels
  $('consolePanel').innerHTML = '';
  $('networkPanel').innerHTML = '';
  consoleCount = 0;
  networkCount = 0;
  $('consoleBadge').textContent = '0';
  $('networkBadge').textContent = '0';

  // Reset filter
  filterErrorsOnly = false;
  $('btnFilter').classList.remove('active');

  // Start elapsed timer display
  clearInterval(displayTimer);
  displayTimer = setInterval(() => {
    if (!isCapturing) return;
    elapsedSec++;
    updateBufferDisplay(elapsedSec);
  }, 1000);

  if (tabUrl) {
    activityLog(`キャプチャ開始: ${truncateUrl(tabUrl, 50)}`, 'success');
  } else {
    activityLog('キャプチャ開始', 'success');
  }
}

function onCaptureStopped(reason) {
  isCapturing = false;
  hasBuffer = false;
  clearInterval(displayTimer);

  setGuideVisible(true);
  setStatus('idle');
  $('btnStop').disabled = true;
  $('btnBug').disabled = true;
  updateBufferDisplay(0);

  activityLog(reason ? `キャプチャ停止: ${reason}` : 'キャプチャ停止', 'warn');
}

// ============================================================
// Saved clips rendering (enhanced cards)
// ============================================================

function addSavedClip(videoFilename, description) {
  savedClips.push({
    videoFilename,
    description,
    time: new Date().toLocaleTimeString('ja-JP'),
  });
  renderSavedList();
}

function renderSavedList() {
  if (savedClips.length === 0) {
    $('savedList').innerHTML = '<div class="empty-state">まだクリップはありません</div>';
    return;
  }
  $('savedList').innerHTML = savedClips.map((c, idx) => {
    const summary = c.description?.summary || c.videoFilename;

    return `
    <div class="saved-item" data-clip-index="${idx}">
      <div class="saved-item-summary">${escapeHtml(summary)}</div>
      <div class="saved-item-header">
        <span class="saved-item-name">🎬 ${escapeHtml(c.videoFilename)}</span>
        <span class="saved-item-meta">${c.time}</span>
      </div>
      <div class="saved-item-files">
        <span>📹 .webm</span>
      </div>
    </div>
  `;
  }).reverse().join('');
}

// ============================================================
// Message listener (from service worker)
// ============================================================

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.target && msg.target !== 'sidepanel') return;

  switch (msg.type) {
    case 'capture-started':
      if (!isCapturing) onCaptureStarted(msg.tabUrl);
      break;

    case 'capture-stopped':
      onCaptureStopped(msg.reason);
      break;

    case 'capture-error':
      activityLog(`エラー: ${msg.error}`, 'error');
      setGuideVisible(true);
      break;

    case 'console-entry':
      addConsoleEntry(msg.entry);
      break;

    case 'network-entry':
      addNetworkEntry(msg.entry);
      break;

    case 'recording-status':
      if (msg.status === 'recording' && !isCapturing) {
        onCaptureStarted();
      } else if (msg.status === 'stopped') {
        onCaptureStopped();
      }
      break;

    case 'saving-started':
      setStatus('saving');
      $('btnBug').disabled = true;
      break;

    case 'saving-completed': {
      activityLog(`保存完了: ${msg.videoFilename}`, 'success');
      showNotifyBanner(
        '保存完了！ダウンロードフォルダに動画を保存しました',
        [`📹 ${msg.videoFilename}`]
      );
      addSavedClip(msg.videoFilename, msg.description);
      // Recorder was restarted — reset elapsed counter but keep button enabled
      elapsedSec = 0;
      updateBufferDisplay(0);
      if (isCapturing) {
        setStatus('ready');
        $('btnBug').disabled = false;
      }
      break;
    }

    case 'saving-error':
      activityLog(`保存エラー: ${msg.error}`, 'error');
      if (isCapturing && hasBuffer) {
        setStatus('ready');
        $('btnBug').disabled = false;
      } else if (isCapturing) {
        setStatus('recording');
      }
      break;

    case 'recording-error':
      activityLog(`録画エラー: ${msg.error}`, 'error');
      break;
  }
});

// ============================================================
// Init: check current state from service worker
// ============================================================
chrome.runtime.sendMessage({ type: 'get-status' }, (response) => {
  if (chrome.runtime.lastError || !response) return;

  // Show any pending error from action.onClicked
  if (response.error) {
    activityLog(`エラー: ${response.error}`, 'error');
  }

  if (response.isCapturing) {
    onCaptureStarted(response.tabUrl);
    // Fetch existing logs
    chrome.runtime.sendMessage({ type: 'get-logs' }, (logResponse) => {
      if (logResponse?.console) {
        logResponse.console.forEach(e => addConsoleEntry(e));
      }
      if (logResponse?.network) {
        logResponse.network.forEach(e => addNetworkEntry(e));
      }
    });
  }
});

activityLog('QA Bug Replay 準備完了', 'success');
if (!isCapturing) {
  activityLog('対象ページで拡張アイコンをクリックして開始', '');
}
