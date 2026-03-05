// content.js — Bridge between page's main world and service worker (isolated world)
// Receives console log messages from inject-console.js via window.postMessage
// and forwards them to the service worker via chrome.runtime.sendMessage.
//
// This script may be injected BOTH via manifest content_scripts (for new pages)
// AND via chrome.scripting.executeScript (for already-open tabs).
// Guard against double registration.

if (!window.__qaBugReplayBridgeInjected) {
  window.__qaBugReplayBridgeInjected = true;

  window.addEventListener('message', (event) => {
    // Only accept messages from the same window
    if (event.source !== window) return;

    // Only process our console capture messages
    if (!event.data || event.data.source !== 'qa-bug-replay-console') return;

    try {
      chrome.runtime.sendMessage({
        type: 'console-log',
        level: event.data.level,
        args: event.data.args,
        callSite: event.data.callSite,
        timestamp: event.data.timestamp,
      });
    } catch (e) {
      // Extension context may have been invalidated (e.g., extension reloaded)
    }
  });
}
