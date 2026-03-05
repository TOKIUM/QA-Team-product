// service-worker.js — Central orchestrator for QA Bug Replay extension
//
// Key design: tabCapture.getMediaStreamId() can ONLY be called inside
// action.onClicked or commands.onCommand callbacks (Chrome's security model).
// So the flow is:
//   1. User clicks extension icon on target tab
//   2. action.onClicked fires → getMediaStreamId() → start recording → open side panel
//   3. Side panel is a control panel (stop / save bug)

import { LogBuffer } from './log-buffer.js';
const SEGMENT_MS = 30_000;
const logBuffer = new LogBuffer();

let isCapturing = false;
let captureTabId = null;
let segmentStartTime = null;
let pendingExport = null;
// Error/state stored for side panel to pick up on init
// (because sidePanel.open() must be called BEFORE any await,
//  so the panel may not be ready to receive broadcast messages)
let pendingError = null;
let lastCaptureTabUrl = null;

// ============================================================
// Action button click → open side panel + capture
// ============================================================
// IMPORTANT ordering constraints:
//   - sidePanel.open() MUST be called synchronously (before any await)
//     because Chrome requires a user gesture context.
//   - tabCapture.getMediaStreamId() needs the "invoked" context from
//     action.onClicked, which persists across awaits.
// So: sidePanel.open() first (no await), then await getMediaStreamId().
// ============================================================
chrome.action.onClicked.addListener(async (tab) => {
  // Always open side panel FIRST — must happen before any await
  // to preserve the user gesture context
  chrome.sidePanel.open({ windowId: tab.windowId });

  // If already capturing, just let the panel open to show current state
  if (isCapturing) return;

  // Reject chrome:// and edge:// internal pages
  if (!tab.url || tab.url.startsWith('chrome://') || tab.url.startsWith('edge://') || tab.url.startsWith('chrome-extension://')) {
    pendingError = 'Chrome 内部ページはキャプチャできません。対象の Web ページに移動してからアイコンをクリックしてください。';
    return;
  }

  try {
    // Get stream ID — uses "invoked" context (persists across awaits)
    const streamId = await chrome.tabCapture.getMediaStreamId({
      targetTabId: tab.id,
    });

    // Start recording with the obtained streamId
    const result = await startCapture(tab.id, streamId);

    if (result.success) {
      lastCaptureTabUrl = tab.url;
      // Try to notify side panel (it may or may not be ready yet;
      // if not ready, it will pick up state via get-status on init)
      broadcastToSidePanel({ type: 'capture-started', tabUrl: tab.url });
    } else {
      pendingError = result.error;
    }
  } catch (err) {
    pendingError = `キャプチャ失敗: ${err.message}`;
  }
});

// ============================================================
// Keyboard shortcut: Ctrl+B → save bug
// ============================================================
chrome.commands.onCommand.addListener((command) => {
  if (command === 'save-bug') {
    handleBugFound(null);
  }
});

// ============================================================
// Network request monitoring (webRequest)
// ============================================================
chrome.webRequest.onBeforeRequest.addListener(
  (details) => {
    if (!isCapturing) return;
    if (captureTabId !== null && details.tabId !== captureTabId) return;
    logBuffer.onRequestStart(details);
  },
  { urls: ['<all_urls>'] }
);

chrome.webRequest.onCompleted.addListener(
  (details) => {
    if (!isCapturing) return;
    if (captureTabId !== null && details.tabId !== captureTabId) return;
    logBuffer.onRequestCompleted(details);
    broadcastToSidePanel({
      type: 'network-entry',
      entry: logBuffer.networkLogs[logBuffer.networkLogs.length - 1],
    });
  },
  { urls: ['<all_urls>'] }
);

chrome.webRequest.onErrorOccurred.addListener(
  (details) => {
    if (!isCapturing) return;
    if (captureTabId !== null && details.tabId !== captureTabId) return;
    logBuffer.onRequestError(details);
    broadcastToSidePanel({
      type: 'network-entry',
      entry: logBuffer.networkLogs[logBuffer.networkLogs.length - 1],
    });
  },
  { urls: ['<all_urls>'] }
);

// ============================================================
// Offscreen document management
// ============================================================
async function ensureOffscreenDocument() {
  const existingContexts = await chrome.runtime.getContexts({
    contextTypes: ['OFFSCREEN_DOCUMENT'],
  });
  if (existingContexts.length > 0) return;

  await chrome.offscreen.createDocument({
    url: 'offscreen/offscreen.html',
    reasons: ['USER_MEDIA'],
    justification: 'Recording tab capture stream via MediaRecorder',
  });
}

async function closeOffscreenDocument() {
  const existingContexts = await chrome.runtime.getContexts({
    contextTypes: ['OFFSCREEN_DOCUMENT'],
  });
  if (existingContexts.length > 0) {
    await chrome.offscreen.closeDocument();
  }
}

// ============================================================
// Start / Stop capture
// ============================================================
async function startCapture(tabId, streamId) {
  if (isCapturing) return { success: false, error: 'Already capturing' };

  try {
    captureTabId = tabId;

    // Create offscreen document for MediaRecorder
    await ensureOffscreenDocument();

    // Send stream ID to offscreen document to start recording
    chrome.runtime.sendMessage({
      type: 'start-recording',
      target: 'offscreen',
      streamId: streamId,
      segmentMs: SEGMENT_MS,
    });

    isCapturing = true;
    segmentStartTime = Date.now();
    logBuffer.clear();

    // Inject console capture into the tab
    await injectConsoleCapture(tabId);

    // Update badge
    chrome.action.setBadgeText({ text: 'REC' });
    chrome.action.setBadgeBackgroundColor({ color: '#f43f5e' });

    return { success: true };
  } catch (err) {
    captureTabId = null;
    return { success: false, error: err.message };
  }
}

async function stopCapture() {
  if (!isCapturing) return;

  isCapturing = false;

  // Tell offscreen to stop recording
  chrome.runtime.sendMessage({
    type: 'stop-recording',
    target: 'offscreen',
  });

  // Close offscreen document after a short delay to let it finish
  setTimeout(() => closeOffscreenDocument(), 1000);

  captureTabId = null;
  segmentStartTime = null;
  logBuffer.clear();

  chrome.action.setBadgeText({ text: '' });
}

// ============================================================
// Console capture injection
// ============================================================
// Two scripts must be injected:
//   1. content.js (ISOLATED world) — bridge that listens to postMessage
//      and forwards to SW via chrome.runtime.sendMessage.
//      Manifest content_scripts only covers pages loaded AFTER install,
//      so we also inject it dynamically for already-open tabs.
//   2. inject-console.js (MAIN world) — monkey-patches console.*
//      and sends via window.postMessage to the bridge.
// Order matters: bridge first, then console patch.
// ============================================================
async function injectConsoleCapture(tabId) {
  try {
    // 1. Inject bridge (ISOLATED world) — has double-injection guard
    await chrome.scripting.executeScript({
      target: { tabId: tabId, allFrames: true },
      files: ['content/content.js'],
      world: 'ISOLATED',
    });
  } catch (err) {
    console.warn('Failed to inject content bridge:', err);
  }

  try {
    // 2. Inject console monkey-patch (MAIN world) — has double-injection guard
    await chrome.scripting.executeScript({
      target: { tabId: tabId, allFrames: true },
      files: ['content/inject-console.js'],
      world: 'MAIN',
    });
  } catch (err) {
    console.warn('Failed to inject console capture:', err);
  }
}

// ============================================================
// Bug found! — Collect logs + trigger video export
// ============================================================
async function handleBugFound(description) {
  if (!isCapturing) return;

  let pageUrl = '';
  if (captureTabId) {
    try {
      const tab = await chrome.tabs.get(captureTabId);
      pageUrl = tab.url || '';
    } catch (e) {}
  }

  const logs = logBuffer.getLogsForWindow(SEGMENT_MS);

  chrome.runtime.sendMessage({
    type: 'get-bug-clip',
    target: 'offscreen',
  });

  pendingExport = { logs, pageUrl, description };

  broadcastToSidePanel({ type: 'saving-started' });
}

// ============================================================
// Message handling
// ============================================================
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  switch (msg.type) {
    // --- From side panel ---
    case 'stop-capture': {
      stopCapture();
      broadcastToSidePanel({ type: 'capture-stopped' });
      sendResponse({ success: true });
      break;
    }

    case 'save-bug': {
      handleBugFound(msg.description || null);
      sendResponse({ success: true });
      break;
    }

    case 'get-status': {
      // Return current state + any pending error from action.onClicked
      const error = pendingError;
      pendingError = null; // consume once
      sendResponse({
        isCapturing,
        captureTabId,
        tabUrl: lastCaptureTabUrl,
        error,
      });
      break;
    }

    case 'get-logs': {
      sendResponse({
        console: logBuffer.getRecentConsoleLogs(200),
        network: logBuffer.getRecentNetworkLogs(200),
      });
      break;
    }

    // --- From content script (console logs) ---
    case 'console-log': {
      if (!isCapturing) break;
      logBuffer.addConsoleEntry({
        timestamp: msg.timestamp,
        level: msg.level,
        args: msg.args,
        callSite: msg.callSite || null,
      });
      broadcastToSidePanel({
        type: 'console-entry',
        entry: {
          timestamp: msg.timestamp,
          level: msg.level,
          args: msg.args,
          callSite: msg.callSite || null,
        },
      });
      break;
    }

    // --- From offscreen document ---
    case 'segment-completed': {
      segmentStartTime = Date.now();
      broadcastToSidePanel({
        type: 'segment-completed',
        duration: msg.duration,
        size: msg.size,
      });
      break;
    }

    case 'recording-status': {
      broadcastToSidePanel({
        type: 'recording-status',
        status: msg.status,
      });
      break;
    }

    case 'bug-clip-ready': {
      if (pendingExport) {
        finishExport(msg.blobUrl, msg.segmentStartTime);
      }
      break;
    }

    case 'recording-error': {
      broadcastToSidePanel({
        type: 'recording-error',
        error: msg.error,
      });
      break;
    }
  }
});

// ============================================================
// Finish export: download video + JSON report + HTML report
// ============================================================
// The offscreen document creates a blob URL (it has URL.createObjectURL).
// We use that blob URL directly with chrome.downloads.download().
// This avoids data URL / base64 conversion for large blobs.
// ============================================================
async function finishExport(blobUrl, videoStartTime) {
  if (!pendingExport) return;

  const { logs, pageUrl, description } = pendingExport;
  pendingExport = null;
  segmentStartTime = Date.now();

  const now = new Date();
  const ts = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, '0'),
    String(now.getDate()).padStart(2, '0'),
    String(now.getHours()).padStart(2, '0'),
    String(now.getMinutes()).padStart(2, '0'),
    String(now.getSeconds()).padStart(2, '0'),
  ].join('-');

  const videoFilename = `bug-replay_${ts}.webm`;

  try {
    // Download video using the blob URL from offscreen document
    chrome.downloads.download({
      url: blobUrl,
      filename: videoFilename,
      saveAs: false,
    }, () => {
      // Revoke the blob URL in offscreen after download starts
      chrome.runtime.sendMessage({
        type: 'revoke-blob-url',
        target: 'offscreen',
        url: blobUrl,
      });
    });

    broadcastToSidePanel({
      type: 'saving-completed',
      videoFilename,
      description,
    });
  } catch (err) {
    broadcastToSidePanel({ type: 'saving-error', error: err.message });
  }
}

// ============================================================
// Broadcast helper
// ============================================================
function broadcastToSidePanel(msg) {
  chrome.runtime.sendMessage({ ...msg, target: 'sidepanel' }).catch(() => {
    // Side panel may not be open yet
  });
}

// ============================================================
// Tab removal: stop capture if the captured tab is closed
// ============================================================
chrome.tabs.onRemoved.addListener((tabId) => {
  if (tabId === captureTabId) {
    stopCapture();
    broadcastToSidePanel({ type: 'capture-stopped', reason: 'Tab closed' });
  }
});
