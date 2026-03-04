/* Tab4: 履歴 */

let timestamps = [];
let selectedTs = new Set();

async function loadHistory() {
    const data = await fetchJson("/api/timestamps");
    timestamps = data.timestamps || [];
    const list = document.getElementById("historyList");
    const countEl = document.getElementById("histCount");
    list.innerHTML = "";
    countEl.textContent = `${timestamps.length} 件`;

    if (!timestamps.length) {
        list.innerHTML = '<div class="empty-state" style="padding:20px"><p>実行履歴がありません</p></div>';
        return;
    }

    // 各タイムスタンプに簡易レポート情報をロード
    for (const ts of timestamps) {
        const div = document.createElement("div");
        div.className = "item";
        div.dataset.ts = ts;
        div.innerHTML = `
            <div style="font-weight:500;font-size:13px">${formatTs(ts)}</div>
            <div class="pass-rate-placeholder" style="font-size:11px;color:var(--text-secondary)">読み込み中...</div>
        `;
        div.onclick = () => toggleSelect(ts, div);
        list.appendChild(div);
    }

    // バックグラウンドでレポートサマリーをロード
    loadHistorySummaries();
}

async function loadHistorySummaries() {
    for (const ts of timestamps) {
        const data = await fetchJson(`/api/report/${ts}`);
        const item = document.querySelector(`#historyList .item[data-ts="${ts}"]`);
        if (!item || data.error) continue;

        const s = data.summary || {};
        const total = s.total || 0;
        const passed = s.passed || 0;
        const failed = total - passed;
        const pct = total > 0 ? Math.round(passed / total * 100) : 0;

        const placeholder = item.querySelector(".pass-rate-placeholder");
        if (placeholder) {
            placeholder.innerHTML = `
                <span style="color:var(--pass)">${passed}✓</span> <span style="color:var(--fail)">${failed}✗</span> / ${total} (${pct}%)
                <div class="pass-rate-bar" style="width:100%;margin-top:3px">
                    <div class="pass-fill" style="width:${pct}%"></div>
                    <div class="fail-fill" style="width:${100 - pct}%"></div>
                </div>
            `;
        }
    }
}

function toggleSelect(ts, el) {
    if (selectedTs.has(ts)) {
        selectedTs.delete(ts);
        el.classList.remove("active");
    } else {
        if (selectedTs.size >= 2) {
            const oldest = [...selectedTs][0];
            selectedTs.delete(oldest);
            document.querySelector(`#historyList .item[data-ts="${oldest}"]`)?.classList.remove("active");
        }
        selectedTs.add(ts);
        el.classList.add("active");
    }

    if (selectedTs.size > 0) {
        showReport([...selectedTs].pop());
    }
}

async function showReport(ts) {
    document.getElementById("compareSection").style.display = "none";
    document.getElementById("trendSection").style.display = "none";

    const data = await fetchJson(`/api/report/${ts}`);
    if (data.error) {
        document.getElementById("historyContent").innerHTML =
            `<div class="card"><div class="msg-error">${escapeHtml(data.error)}</div></div>`;
        return;
    }

    const summary = data.summary || {};
    const total = summary.total || 0;
    const passed = summary.passed || 0;
    const failed = summary.failed || 0;
    const pct = total > 0 ? Math.round(passed / total * 100) : 0;

    let html = `
        <div class="summary-cards">
            <div class="summary-card"><div class="value">${total}</div><div class="label">Total</div></div>
            <div class="summary-card"><div class="value" style="color:var(--pass)">${passed}</div><div class="label">Passed</div></div>
            <div class="summary-card"><div class="value" style="color:var(--fail)">${failed}</div><div class="label">Failed</div></div>
            <div class="summary-card"><div class="value">${pct}%</div><div class="label">Pass Rate</div></div>
        </div>
    `;

    // パターン別
    const byPat = summary.by_pattern || {};
    if (Object.keys(byPat).length) {
        html += `<div class="card"><h3>パターン別</h3><table><thead><tr><th>パターン</th><th>Passed</th><th>Total</th><th style="width:120px">Pass Rate</th></tr></thead><tbody>`;
        for (const [pat, c] of Object.entries(byPat)) {
            const pp = c.total > 0 ? Math.round(c.passed / c.total * 100) : 0;
            html += `<tr>
                <td>${escapeHtml(pat)}</td>
                <td>${c.passed}</td>
                <td>${c.total}</td>
                <td>
                    <div style="display:flex;align-items:center;gap:8px">
                        <div class="pass-rate-bar" style="flex:1"><div class="pass-fill" style="width:${pp}%"></div><div class="fail-fill" style="width:${100-pp}%"></div></div>
                        <span style="font-size:12px;min-width:35px;text-align:right">${pp}%</span>
                    </div>
                </td>
            </tr>`;
        }
        html += `</tbody></table></div>`;
    }

    // テスト詳細
    const tests = data.tests || [];
    const failedTests = tests.filter(t => !t.passed);
    if (failedTests.length) {
        html += `<div class="card"><h3 style="color:var(--fail)">FAIL 一覧 (${failedTests.length} 件)</h3><table>
            <thead><tr><th>テスト名</th><th>パターン</th><th>期待</th><th>実際</th><th>時間</th></tr></thead><tbody>`;
        for (const t of failedTests) {
            html += `<tr>
                <td>${escapeHtml(t.name)}</td>
                <td>${escapeHtml(t.pattern)}</td>
                <td>${t.expected_status}</td>
                <td style="color:var(--fail);font-weight:600">${t.actual_status}</td>
                <td>${(t.elapsed_ms || 0).toFixed(0)}ms</td>
            </tr>`;
        }
        html += `</tbody></table></div>`;
    }

    html += `<div class="card"><h3>全テスト (${formatTs(ts)})</h3><div style="max-height:400px;overflow:auto"><table>
        <thead><tr><th>テスト名</th><th>パターン</th><th>結果</th><th>時間</th></tr></thead><tbody>`;
    for (const t of tests) {
        const label = t.passed ? "PASS" : "FAIL";
        html += `<tr>
            <td>${escapeHtml(t.name)}</td>
            <td><span style="font-size:12px;color:var(--text-secondary)">${escapeHtml(t.pattern)}</span></td>
            <td>${badgeHtml(label)}</td>
            <td style="font-variant-numeric:tabular-nums">${(t.elapsed_ms || 0).toFixed(0)}ms</td>
        </tr>`;
    }
    html += `</tbody></table></div></div>`;

    document.getElementById("historyContent").innerHTML = html;
}

async function compareRuns() {
    if (selectedTs.size !== 2) {
        showToast("2つの実行を選択してください", "info");
        return;
    }

    const [ts1, ts2] = [...selectedTs].sort();
    const data = await postJson("/api/compare", {ts1, ts2});

    if (data.error) {
        showToast(data.error, "error");
        return;
    }

    let html = `<p style="margin-bottom:14px;font-size:13px;color:var(--text-secondary)">${formatTs(ts1)} → ${formatTs(ts2)}</p>`;

    const s1 = data.summary1 || {};
    const s2 = data.summary2 || {};
    const diff = (v1, v2) => {
        const d = v2 - v1;
        if (d === 0) return "";
        return d > 0 ? `<span style="color:var(--fail)"> (+${d})</span>` : `<span style="color:var(--pass)"> (${d})</span>`;
    };

    html += `<table><thead><tr><th></th><th>前回</th><th>今回</th><th>差分</th></tr></thead><tbody>
        <tr><td>Total</td><td>${s1.total || 0}</td><td>${s2.total || 0}</td><td>${diff(s1.total||0, s2.total||0)}</td></tr>
        <tr><td>Passed</td><td>${s1.passed || 0}</td><td>${s2.passed || 0}</td><td>${diff(s1.passed||0, s2.passed||0)}</td></tr>
        <tr><td>Failed</td><td>${s1.failed || 0}</td><td>${s2.failed || 0}</td><td>${diff(s1.failed||0, s2.failed||0)}</td></tr>
    </tbody></table>`;

    if (data.status_changes && data.status_changes.length) {
        html += `<h3 style="margin:18px 0 10px">ステータス変化 (${data.status_changes.length} 件)</h3><table>
            <thead><tr><th>テスト名</th><th>前回</th><th>今回</th></tr></thead><tbody>`;
        for (const c of data.status_changes) {
            html += `<tr>
                <td>${escapeHtml(c.name)}</td>
                <td>${badgeHtml(c.old_status)}</td>
                <td>${badgeHtml(c.new_status)}</td>
            </tr>`;
        }
        html += `</tbody></table>`;
    } else {
        html += `<div class="msg-success" style="margin-top:14px">ステータス変化なし</div>`;
    }

    if (data.schema_diffs && data.schema_diffs.length) {
        html += `<h3 style="margin:18px 0 10px">スキーマ差分</h3>`;
        for (const d of data.schema_diffs) {
            html += `<div style="margin-bottom:10px"><strong>${escapeHtml(d.name)}</strong><ul style="margin:4px 0 0 20px">`;
            for (const c of d.changes) {
                const cls = c.kind === "added" ? "diff-added" : c.kind === "removed" ? "diff-removed" : "diff-changed";
                html += `<li class="${cls}" style="font-size:13px">${escapeHtml(c.kind)}: ${escapeHtml(c.path)} (${escapeHtml(c.detail)})</li>`;
            }
            html += `</ul></div>`;
        }
    }

    document.getElementById("compareContent").innerHTML = html;
    document.getElementById("compareSection").style.display = "block";
    document.getElementById("trendSection").style.display = "none";
}

async function showTrend() {
    const data = await fetchJson("/api/trend?last=10");

    if (data.error) {
        showToast(data.error, "error");
        return;
    }

    let html = "";

    if (data.degradations && data.degradations.length) {
        html += `<div class="msg-error" style="margin-bottom:14px">
            <strong>パフォーマンス劣化検知 (${data.degradations.length} 件)</strong></div>`;
        html += `<table><thead><tr><th>テスト名</th><th>前回</th><th>今回</th><th>倍率</th></tr></thead><tbody>`;
        for (const d of data.degradations) {
            html += `<tr style="color:var(--fail)">
                <td>${escapeHtml(d.name)}</td>
                <td>${d.prev_ms.toFixed(0)}ms</td>
                <td>${d.curr_ms.toFixed(0)}ms</td>
                <td><strong>${d.ratio}x</strong></td>
            </tr>`;
        }
        html += `</tbody></table>`;
    } else {
        html += `<div class="msg-success" style="margin-bottom:14px">パフォーマンス劣化なし</div>`;
    }

    if (data.runs && data.runs.length) {
        html += `<h3 style="margin:18px 0 10px">実行履歴 (直近${data.runs.length}回)</h3>`;
        html += `<table><thead><tr><th>日時</th><th>Total</th><th>Passed</th><th>Failed</th><th style="width:120px">Pass Rate</th></tr></thead><tbody>`;
        for (const r of data.runs) {
            const s = r.summary || {};
            const total = s.total || 0;
            const passed = s.passed || 0;
            const pct = total > 0 ? Math.round(passed / total * 100) : 0;
            html += `<tr>
                <td>${formatTs(r.timestamp)}</td>
                <td>${total}</td>
                <td>${passed}</td>
                <td>${s.failed || 0}</td>
                <td>
                    <div style="display:flex;align-items:center;gap:6px">
                        <div class="pass-rate-bar" style="flex:1"><div class="pass-fill" style="width:${pct}%"></div><div class="fail-fill" style="width:${100-pct}%"></div></div>
                        <span style="font-size:12px">${pct}%</span>
                    </div>
                </td>
            </tr>`;
        }
        html += `</tbody></table>`;
    }

    const timeline = data.timeline || {};
    const names = Object.keys(timeline);
    if (names.length) {
        html += `<h3 style="margin:18px 0 10px">テスト別実行時間推移</h3>`;
        html += `<div style="max-height:400px;overflow:auto"><table>
            <thead><tr><th>テスト名</th>`;
        const allTs = (data.runs || []).map(r => r.timestamp);
        for (const ts of allTs) {
            html += `<th style="font-size:10px;writing-mode:vertical-rl;text-orientation:mixed;min-width:24px">${ts.slice(4,8)}</th>`;
        }
        html += `</tr></thead><tbody>`;

        for (const name of names.slice(0, 30)) {
            html += `<tr><td style="font-size:12px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${escapeHtml(name)}">${escapeHtml(name)}</td>`;
            const entries = timeline[name];
            const entryMap = {};
            for (const e of entries) entryMap[e.timestamp] = e;
            for (const ts of allTs) {
                const e = entryMap[ts];
                if (e) {
                    const color = e.passed ? "var(--pass)" : "var(--fail)";
                    html += `<td style="font-size:11px;color:${color};text-align:center;font-variant-numeric:tabular-nums">${e.elapsed_ms.toFixed(0)}</td>`;
                } else {
                    html += `<td style="text-align:center;color:var(--text-secondary)">-</td>`;
                }
            }
            html += `</tr>`;
        }
        html += `</tbody></table></div>`;
    }

    document.getElementById("trendContent").innerHTML = html;
    document.getElementById("trendSection").style.display = "block";
    document.getElementById("compareSection").style.display = "none";
}

loadHistory();
