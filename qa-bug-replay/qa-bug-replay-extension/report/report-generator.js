// report-generator.js — JSON/HTML report generation for bug clips
// Used by the service worker to build the export JSON and HTML report.

/**
 * Build the JSON report object
 */
function buildReport({ videoFilename, pageUrl, videoStartTime, windowSeconds, consoleLogs, networkLogs, bugDescription }) {
  return {
    version: '1.0',
    exportTime: new Date().toISOString(),
    windowSeconds,
    videoFile: videoFilename,
    pageUrl,
    bugDescription: bugDescription || null,
    console: consoleLogs.map(e => ({
      videoOffsetSec: parseFloat(((e.timestamp - videoStartTime) / 1000).toFixed(1)),
      level: e.level,
      args: e.args,
      callSite: e.callSite || null,
    })),
    network: networkLogs.map(e => ({
      videoOffsetSec: parseFloat(((e.startTime - videoStartTime) / 1000).toFixed(1)),
      url: e.url,
      method: e.method,
      statusCode: e.statusCode,
      duration: e.duration,
      resourceType: e.resourceType,
      fromCache: e.fromCache || false,
      error: e.error || null,
    })),
  };
}

/**
 * Build a self-contained HTML report for developers
 */
function buildHtmlReport(report) {
  const esc = (s) => String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');

  const consoleErrors = report.console.filter(e => e.level === 'error').length;
  const consoleWarns = report.console.filter(e => e.level === 'warn').length;
  const network4xx = report.network.filter(e => e.statusCode >= 400 && e.statusCode < 500).length;
  const network5xx = report.network.filter(e => e.statusCode >= 500).length;
  const networkErr = report.network.filter(e => e.error).length;

  const desc = report.bugDescription;

  const consoleRowsHtml = report.console.map(e => {
    const args = Array.isArray(e.args) ? e.args.join(' ') : String(e.args);
    const levelClass = e.level === 'error' ? 'level-error'
      : e.level === 'warn' ? 'level-warn'
      : e.level === 'info' ? 'level-info'
      : 'level-log';
    return `<tr class="${levelClass}">
      <td class="col-offset">${e.videoOffsetSec}s</td>
      <td class="col-level">${esc(e.level)}</td>
      <td class="col-msg">${esc(args)}${e.callSite ? `<br><span class="call-site">${esc(e.callSite)}</span>` : ''}</td>
    </tr>`;
  }).join('\n');

  const networkRowsHtml = report.network.map(e => {
    const statusClass = e.error || (e.statusCode && e.statusCode >= 400) ? 'status-error'
      : e.statusCode >= 300 ? 'status-redirect'
      : 'status-ok';
    return `<tr>
      <td class="col-offset">${e.videoOffsetSec}s</td>
      <td class="col-status ${statusClass}">${e.error ? 'ERR' : (e.statusCode || '...')}</td>
      <td class="col-method">${esc(e.method)}</td>
      <td class="col-url" title="${esc(e.url)}">${esc(e.url)}</td>
      <td class="col-duration">${e.duration != null ? e.duration + 'ms' : ''}</td>
      <td class="col-type">${esc(e.resourceType || '')}</td>
    </tr>`;
  }).join('\n');

  return `<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bug Report — ${esc(desc?.summary || report.videoFile)}</title>
<style>
:root {
  --bg: #0a0e17;
  --surface: #111827;
  --border: #1e2a3a;
  --text: #e2e8f0;
  --text-muted: #64748b;
  --accent: #f43f5e;
  --green: #10b981;
  --yellow: #f59e0b;
  --blue: #3b82f6;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: 'Segoe UI', 'Noto Sans JP', sans-serif;
  font-size: 13px;
  line-height: 1.6;
  padding: 24px;
}
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(30,42,58,0.3) 1px, transparent 1px),
    linear-gradient(90deg, rgba(30,42,58,0.3) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 0;
}
.container { position: relative; z-index: 1; max-width: 960px; margin: 0 auto; }
.header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border);
}
.logo {
  width: 40px; height: 40px;
  background: linear-gradient(135deg, var(--accent), #e11d48);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
  box-shadow: 0 0 16px rgba(244,63,94,0.3);
  flex-shrink: 0;
}
.header-text h1 {
  font-family: 'Segoe UI Mono', 'Consolas', monospace;
  font-size: 16px;
  font-weight: 700;
}
.header-text h1 span { font-size: 11px; color: var(--text-muted); font-weight: 400; }
.header-text p { font-size: 11px; color: var(--text-muted); }
.meta-table {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
  font-family: 'Segoe UI Mono', 'Consolas', monospace;
  font-size: 12px;
}
.meta-table dt { color: var(--text-muted); float: left; width: 90px; clear: left; }
.meta-table dd { margin-left: 100px; margin-bottom: 4px; word-break: break-all; }
.bug-desc {
  background: rgba(244,63,94,0.08);
  border: 1px solid rgba(244,63,94,0.2);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
}
.bug-desc h3 { font-size: 13px; color: var(--accent); margin-bottom: 6px; }
.bug-desc .steps { white-space: pre-wrap; font-size: 12px; color: var(--text-muted); margin-top: 6px; }
.summary-cards {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.summary-card {
  flex: 1;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 16px;
  text-align: center;
}
.summary-card .num {
  font-size: 24px;
  font-weight: 700;
  font-family: 'Segoe UI Mono', monospace;
}
.summary-card .label {
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 2px;
}
.summary-card.error .num { color: var(--accent); }
.summary-card.warn .num { color: var(--yellow); }
.summary-card.net-err .num { color: var(--yellow); }
.section-title {
  font-family: 'Segoe UI Mono', monospace;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--text-muted);
  margin: 20px 0 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--border);
}
table {
  width: 100%;
  border-collapse: collapse;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  font-family: 'Segoe UI Mono', 'Consolas', monospace;
  font-size: 11px;
}
th {
  background: rgba(30,42,58,0.5);
  text-align: left;
  padding: 6px 10px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  font-size: 10px;
  letter-spacing: 0.5px;
}
td {
  padding: 4px 10px;
  border-top: 1px solid rgba(30,42,58,0.5);
  vertical-align: top;
}
.col-offset { color: var(--text-muted); width: 50px; white-space: nowrap; }
.col-level { width: 50px; text-transform: uppercase; font-weight: 600; }
.col-msg { word-break: break-all; }
.col-status { width: 40px; font-weight: 700; text-align: right; }
.col-method { width: 50px; color: var(--text-muted); }
.col-url { word-break: break-all; }
.col-duration { width: 60px; color: var(--text-muted); text-align: right; }
.col-type { width: 60px; color: var(--text-muted); text-transform: uppercase; font-size: 9px; }
.level-error td { color: var(--accent); }
.level-warn td { color: var(--yellow); }
.level-info td { color: var(--blue); }
.level-log td { color: var(--text); }
.call-site { color: var(--text-muted); font-size: 10px; }
.status-ok { color: var(--green); }
.status-redirect { color: var(--yellow); }
.status-error { color: var(--accent); }
.video-ref {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 16px;
  margin-top: 20px;
  font-size: 12px;
  color: var(--text-muted);
  font-family: 'Segoe UI Mono', monospace;
}
.footer {
  text-align: center;
  margin-top: 24px;
  font-size: 10px;
  color: var(--text-muted);
}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="logo">🐛</div>
    <div class="header-text">
      <h1>QA Bug Replay <span>Report</span></h1>
      <p>バグレポート — ${esc(report.exportTime)}</p>
    </div>
  </div>

  <dl class="meta-table">
    <dt>URL</dt><dd>${esc(report.pageUrl || '(不明)')}</dd>
    <dt>日時</dt><dd>${esc(report.exportTime)}</dd>
    <dt>動画</dt><dd>${esc(report.videoFile)}</dd>
    <dt>記録時間</dt><dd>${report.windowSeconds}秒</dd>
  </dl>

  ${desc ? `
  <div class="bug-desc">
    <h3>${esc(desc.summary)}</h3>
    ${desc.steps ? `<div class="steps">${esc(desc.steps)}</div>` : ''}
  </div>
  ` : ''}

  <div class="summary-cards">
    <div class="summary-card error">
      <div class="num">${consoleErrors}</div>
      <div class="label">Console Errors</div>
    </div>
    <div class="summary-card warn">
      <div class="num">${consoleWarns}</div>
      <div class="label">Console Warns</div>
    </div>
    <div class="summary-card net-err">
      <div class="num">${network4xx + network5xx + networkErr}</div>
      <div class="label">Network Errors</div>
    </div>
  </div>

  <div class="section-title">Console Logs (${report.console.length})</div>
  <table>
    <thead><tr><th>Offset</th><th>Level</th><th>Message</th></tr></thead>
    <tbody>
      ${consoleRowsHtml || '<tr><td colspan="3" style="text-align:center;color:var(--text-muted)">ログなし</td></tr>'}
    </tbody>
  </table>

  <div class="section-title">Network Requests (${report.network.length})</div>
  <table>
    <thead><tr><th>Offset</th><th>Status</th><th>Method</th><th>URL</th><th>Duration</th><th>Type</th></tr></thead>
    <tbody>
      ${networkRowsHtml || '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">リクエストなし</td></tr>'}
    </tbody>
  </table>

  <div class="video-ref">
    📹 同フォルダの <strong>${esc(report.videoFile)}</strong> を参照してください
  </div>

  <div class="footer">
    Generated by QA Bug Replay v1.0 — ${esc(report.exportTime)}
  </div>
</div>
</body>
</html>`;
}

export { buildReport, buildHtmlReport };
