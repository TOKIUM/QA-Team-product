// inject-console.js — Monkey-patch console.* in the page's MAIN world
// Captures log/warn/error/info and forwards via window.postMessage to content script.
// Also captures window.onerror and unhandledrejection.

(function () {
  // Guard against double injection
  if (window.__qaBugReplayConsoleInjected) return;
  window.__qaBugReplayConsoleInjected = true;

  const LEVELS = ['log', 'warn', 'error', 'info'];
  const originals = {};

  // Save original console methods
  LEVELS.forEach(level => {
    originals[level] = console[level].bind(console);
  });

  // Safe serialization of arguments
  function safeSerialize(arg) {
    if (arg === undefined) return 'undefined';
    if (arg === null) return 'null';
    if (typeof arg === 'string') return arg;
    if (typeof arg === 'number' || typeof arg === 'boolean') return String(arg);

    if (arg instanceof Error) {
      return `${arg.name}: ${arg.message}${arg.stack ? '\n' + arg.stack : ''}`;
    }

    try {
      const seen = new WeakSet();
      return JSON.stringify(arg, function (key, value) {
        if (typeof value === 'object' && value !== null) {
          if (seen.has(value)) return '[Circular]';
          seen.add(value);
        }
        if (typeof value === 'function') return '[Function: ' + (value.name || 'anonymous') + ']';
        if (value instanceof HTMLElement) return `[${value.tagName}#${value.id || ''}]`;
        return value;
      }, 0);
    } catch (e) {
      return '[Unserializable]';
    }
  }

  // Extract callsite from stack trace
  function getCallSite() {
    try {
      const stack = new Error().stack;
      if (!stack) return null;
      const lines = stack.split('\n');
      // Skip: Error, getCallSite, patched console method
      for (let i = 3; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line && !line.includes('inject-console.js')) {
          return line.replace(/^\s*at\s+/, '');
        }
      }
    } catch (e) {}
    return null;
  }

  // Patch console methods
  LEVELS.forEach(level => {
    console[level] = function (...args) {
      // Always call original first (don't break the page)
      originals[level](...args);

      try {
        const serialized = args.map(safeSerialize);
        window.postMessage({
          source: 'qa-bug-replay-console',
          level: level,
          args: serialized,
          callSite: getCallSite(),
          timestamp: Date.now(),
        }, '*');
      } catch (e) {
        // Silently fail — never interfere with the page
      }
    };
  });

  // Capture uncaught errors
  window.addEventListener('error', (event) => {
    try {
      window.postMessage({
        source: 'qa-bug-replay-console',
        level: 'error',
        args: [
          `Uncaught ${event.error?.name || 'Error'}: ${event.message}`,
          event.error?.stack || `at ${event.filename}:${event.lineno}:${event.colno}`,
        ],
        callSite: `${event.filename}:${event.lineno}:${event.colno}`,
        timestamp: Date.now(),
      }, '*');
    } catch (e) {}
  });

  // Capture unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    try {
      const reason = event.reason;
      const msg = reason instanceof Error
        ? `Unhandled Promise Rejection: ${reason.name}: ${reason.message}`
        : `Unhandled Promise Rejection: ${safeSerialize(reason)}`;

      window.postMessage({
        source: 'qa-bug-replay-console',
        level: 'error',
        args: [msg, reason instanceof Error ? reason.stack : ''],
        callSite: reason instanceof Error ? reason.stack?.split('\n')[1]?.trim()?.replace(/^\s*at\s+/, '') : null,
        timestamp: Date.now(),
      }, '*');
    } catch (e) {}
  });
})();
