// log-buffer.js — Rolling 60-second buffer for console and network logs
// Keeps 2x30s (60s) of entries, auto-prunes old ones.

const BUFFER_WINDOW_MS = 60_000; // 60 seconds total buffer

class LogBuffer {
  constructor() {
    this.consoleLogs = [];
    this.networkLogs = [];
    // Map of requestId -> partial network entry (for joining start/complete/error)
    this.pendingRequests = new Map();
  }

  // --- Console ---

  addConsoleEntry(entry) {
    // entry: { timestamp, level, args, callSite? }
    this.consoleLogs.push({
      timestamp: entry.timestamp || Date.now(),
      level: entry.level,
      args: entry.args,
      callSite: entry.callSite || null,
    });
    this._pruneConsole();
  }

  // --- Network ---

  onRequestStart(details) {
    const entry = {
      requestId: details.requestId,
      url: details.url,
      method: details.method,
      resourceType: details.type,
      startTime: Date.now(),
      statusCode: null,
      duration: null,
      fromCache: false,
      error: null,
    };
    this.pendingRequests.set(details.requestId, entry);
  }

  onRequestCompleted(details) {
    const entry = this.pendingRequests.get(details.requestId);
    if (entry) {
      entry.statusCode = details.statusCode;
      entry.fromCache = details.fromCache || false;
      entry.endTime = Date.now();
      entry.duration = entry.endTime - entry.startTime;
      this.pendingRequests.delete(details.requestId);
      this.networkLogs.push(entry);
      this._pruneNetwork();
    } else {
      // Request started before extension was active
      this.networkLogs.push({
        requestId: details.requestId,
        url: details.url,
        method: details.method || 'GET',
        resourceType: details.type,
        startTime: Date.now(),
        statusCode: details.statusCode,
        duration: null,
        fromCache: details.fromCache || false,
        error: null,
      });
      this._pruneNetwork();
    }
  }

  onRequestError(details) {
    const entry = this.pendingRequests.get(details.requestId);
    if (entry) {
      entry.error = details.error;
      entry.endTime = Date.now();
      entry.duration = entry.endTime - entry.startTime;
      this.pendingRequests.delete(details.requestId);
      this.networkLogs.push(entry);
      this._pruneNetwork();
    }
  }

  // --- Retrieval ---

  getLogsForWindow(windowMs = 30_000) {
    const cutoff = Date.now() - windowMs;
    return {
      console: this.consoleLogs.filter(e => e.timestamp >= cutoff),
      network: this.networkLogs.filter(e => e.startTime >= cutoff),
    };
  }

  getRecentConsoleLogs(count = 100) {
    return this.consoleLogs.slice(-count);
  }

  getRecentNetworkLogs(count = 100) {
    return this.networkLogs.slice(-count);
  }

  // --- Pruning ---

  _pruneConsole() {
    const cutoff = Date.now() - BUFFER_WINDOW_MS;
    while (this.consoleLogs.length > 0 && this.consoleLogs[0].timestamp < cutoff) {
      this.consoleLogs.shift();
    }
  }

  _pruneNetwork() {
    const cutoff = Date.now() - BUFFER_WINDOW_MS;
    while (this.networkLogs.length > 0 && this.networkLogs[0].startTime < cutoff) {
      this.networkLogs.shift();
    }
    // Also prune stale pending requests (older than 2 minutes)
    const staleCutoff = Date.now() - 120_000;
    for (const [id, entry] of this.pendingRequests) {
      if (entry.startTime < staleCutoff) {
        this.pendingRequests.delete(id);
      }
    }
  }

  clear() {
    this.consoleLogs = [];
    this.networkLogs = [];
    this.pendingRequests.clear();
  }
}

export { LogBuffer };
