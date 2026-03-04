/* Tab1: テスト実行 */

let pollTimer = null;
let runStartTime = null;
let allResults = [];
let currentFilter = "all";
let currentSort = { col: null, asc: true };
let csvFileList = [];  // 全CSVファイル名リスト
const ALL_PATTERNS = ["auth", "pagination", "search", "boundary", "missing_required", "post_normal", "put_normal", "delete_normal", "patch_normal"];

/** CSVファイル名からAPI名を抽出する */
function extractApiName(filename) {
    const m = filename.match(/- (\d+)(.+?)\.csv$/);
    if (m) return m[1] + " " + m[2];
    return filename.replace(/\.csv$/, "");
}

/** 選択中のCSVファイル名を取得 */
function getSelectedCsvFiles() {
    const checked = document.querySelectorAll("#csvFiles input[type=checkbox]:checked");
    return [...checked].map(cb => cb.value);
}

/** 選択数表示を更新 */
function updateSelectedCount() {
    const selected = getSelectedCsvFiles();
    const total = csvFileList.length;
    const el = document.getElementById("selectedCount");
    const targetEl = document.getElementById("runTarget");

    if (selected.length === 0) {
        el.textContent = `選択なし（全${total}ファイルが対象）`;
        targetEl.textContent = `全 ${total} ファイル対象`;
    } else if (selected.length === total) {
        el.textContent = `全選択 (${total})`;
        targetEl.textContent = `全 ${total} ファイル対象`;
    } else {
        el.textContent = `${selected.length} / ${total} 選択中`;
        targetEl.textContent = `${selected.length} ファイル選択中`;
    }
}

/** 全選択/全解除（表示中の行のみ対象） */
function selectAllCsv(checked) {
    document.querySelectorAll("#csvFiles tbody tr").forEach(tr => {
        if (tr.style.display !== "none") {
            const cb = tr.querySelector("input[type=checkbox]");
            if (cb) cb.checked = checked;
        }
    });
    updateSelectedCount();
}

/** CSV検索フィルタ */
function filterCsvList() {
    const query = document.getElementById("csvSearch").value.toLowerCase();
    const rows = document.querySelectorAll("#csvFiles tbody tr");
    let visibleCount = 0;
    rows.forEach(tr => {
        const apiName = tr.querySelector("td:nth-child(3)")?.textContent?.toLowerCase() || "";
        const filename = tr.querySelector("input[type=checkbox]")?.value?.toLowerCase() || "";
        const match = !query || apiName.includes(query) || filename.includes(query);
        tr.style.display = match ? "" : "none";
        if (match) visibleCount++;
    });
    const countEl = document.getElementById("csvCount");
    if (query) {
        countEl.textContent = `(${visibleCount} / ${csvFileList.length} ファイル)`;
    } else {
        countEl.textContent = `(${csvFileList.length} ファイル)`;
    }
}

/** パターンボタンをトグル */
function togglePattern(btn) {
    btn.classList.toggle("active");
    updatePatternStatus();
}

/** パターン全選択/全解除 */
function selectAllPatterns(select) {
    document.querySelectorAll("#patternChecks .filter-btn[data-pat]").forEach(b => {
        b.classList.toggle("active", select);
    });
    updatePatternStatus();
}

/** 選択中パターンを取得 */
function getSelectedPatterns() {
    return [...document.querySelectorAll("#patternChecks .filter-btn.active[data-pat]")]
        .map(b => b.dataset.pat);
}

/** パターン選択状態の表示更新 */
function updatePatternStatus() {
    const selected = getSelectedPatterns();
    const el = document.getElementById("patternStatus");
    if (selected.length === 0) {
        el.textContent = "(未選択 - テスト実行できません)";
        el.style.color = "var(--fail)";
    } else if (selected.length === ALL_PATTERNS.length) {
        el.textContent = "(すべて)";
        el.style.color = "var(--text-secondary)";
    } else {
        el.textContent = `(${selected.length} 選択中)`;
        el.style.color = "var(--primary)";
    }
}

async function refreshCsv() {
    const dir = document.getElementById("csvDir").value;
    const data = await fetchJson(`/api/csv-files?csv_dir=${encodeURIComponent(dir)}`);
    const el = document.getElementById("csvFiles");
    const countEl = document.getElementById("csvCount");

    if (data.error) {
        el.innerHTML = `<div class="msg-error">${escapeHtml(data.error)}</div>`;
        countEl.textContent = "";
        csvFileList = [];
        updateSelectedCount();
        return;
    }
    if (!data.files.length) {
        el.innerHTML = '<div class="empty-state"><div class="icon">📂</div><p>CSV ファイルがありません</p></div>';
        countEl.textContent = "";
        csvFileList = [];
        updateSelectedCount();
        return;
    }

    csvFileList = data.files;
    countEl.textContent = `(${data.files.length} ファイル)`;

    let html = '<table><thead><tr><th style="width:36px"><input type="checkbox" id="csvSelectAll" onchange="selectAllCsv(this.checked)" checked></th><th style="width:36px">#</th><th>API名</th></tr></thead><tbody>';
    for (let i = 0; i < data.files.length; i++) {
        const f = data.files[i];
        const apiName = extractApiName(f);
        html += `<tr>
            <td><input type="checkbox" value="${escapeHtml(f)}" checked onchange="updateSelectedCount()"></td>
            <td style="color:var(--text-secondary);font-size:12px">${i + 1}</td>
            <td style="font-weight:500" title="${escapeHtml(f)}">${escapeHtml(apiName)}</td>
        </tr>`;
    }
    html += '</tbody></table>';
    el.innerHTML = html;
    updateSelectedCount();
}

async function startRun() {
    const btn = document.getElementById("runBtn");
    btn.disabled = true;
    runStartTime = Date.now();

    document.getElementById("statusBar").style.display = "flex";
    document.getElementById("progressWrap").style.display = "block";
    document.getElementById("summarySection").style.display = "none";
    document.getElementById("resultsSection").style.display = "none";
    document.getElementById("detailSection").style.display = "none";
    document.getElementById("progressFill").style.width = "0%";
    document.getElementById("progressLabel").textContent = "";
    document.getElementById("progressTime").textContent = "";
    document.getElementById("statusText").textContent = "実行中...";

    const csvDir = document.getElementById("csvDir").value;
    const selectedPatterns = getSelectedPatterns();

    if (selectedPatterns.length === 0) {
        document.getElementById("statusBar").style.display = "none";
        document.getElementById("progressWrap").style.display = "none";
        btn.disabled = false;
        showToast("パターンを1つ以上選択してください", "error");
        return;
    }

    const body = { csv_dir: csvDir };
    // 全選択でなければフィルタとして送信
    if (selectedPatterns.length < ALL_PATTERNS.length) {
        body.patterns = selectedPatterns;
    }

    // 選択ファイルフィルタ（全選択 or 未選択の場合は全ファイル対象）
    const selected = getSelectedCsvFiles();
    if (selected.length > 0 && selected.length < csvFileList.length) {
        body.csv_files = selected;
    }

    const result = await postJson("/api/run", body);

    if (result.error) {
        document.getElementById("statusBar").style.display = "none";
        document.getElementById("progressWrap").style.display = "none";
        btn.disabled = false;
        showToast(result.error, "error", 6000);
        return;
    }

    pollTimer = setInterval(pollStatus, 1500);
}

async function pollStatus() {
    const state = await fetchJson("/api/run/status");
    const elapsed = Date.now() - runStartTime;

    if (state.status === "running") {
        const pct = state.total > 0 ? Math.round(state.completed / state.total * 100) : 0;
        document.getElementById("progressFill").style.width = pct + "%";
        document.getElementById("progressLabel").textContent =
            `${state.completed} / ${state.total} 件 (${pct}%)`;
        document.getElementById("statusText").textContent =
            `実行中... ${state.completed}/${state.total}`;

        let timeText = `経過: ${formatElapsed(elapsed)}`;
        if (state.completed > 0 && state.total > state.completed) {
            const perTest = elapsed / state.completed;
            const remaining = perTest * (state.total - state.completed);
            timeText += ` / 残り約 ${formatElapsed(remaining)}`;
        }
        document.getElementById("progressTime").textContent = timeText;
        return;
    }

    clearInterval(pollTimer);
    pollTimer = null;
    document.getElementById("statusBar").style.display = "none";
    document.getElementById("runBtn").disabled = false;

    if (state.status === "error") {
        document.getElementById("progressWrap").style.display = "none";
        showToast("エラー: " + state.error, "error", 8000);
        return;
    }

    document.getElementById("progressFill").style.width = "100%";
    document.getElementById("progressLabel").textContent = "完了";
    document.getElementById("progressTime").textContent = `合計: ${formatElapsed(elapsed)}`;
    showToast(`テスト完了: ${state.summary.passed} passed / ${state.summary.failed} failed`, state.summary.failed > 0 ? "error" : "success");
    showResults(state);
}

function showResults(state) {
    const s = state.summary;
    allResults = state.results;
    currentFilter = "all";

    document.getElementById("summarySection").style.display = "block";
    document.getElementById("summaryCards").innerHTML = `
        <div class="summary-card">
            <div class="value">${s.total}</div>
            <div class="label">Total</div>
        </div>
        <div class="summary-card">
            <div class="value" style="color:var(--pass)">${s.passed}</div>
            <div class="label">Passed</div>
        </div>
        <div class="summary-card">
            <div class="value" style="color:var(--fail)">${s.failed}</div>
            <div class="label">Failed</div>
        </div>
        <div class="summary-card">
            <div class="value" style="color:var(--warn)">${s.warn || 0}</div>
            <div class="label">Warn</div>
        </div>
    `;

    const passCount = allResults.filter(r => r.label === "PASS").length;
    const failCount = allResults.filter(r => r.label === "FAIL").length;
    const warnCount = allResults.filter(r => r.label === "WARN").length;
    document.getElementById("resultFilters").innerHTML = `
        <button class="filter-btn active" onclick="filterResults('all')">すべて <span class="count">${allResults.length}</span></button>
        <button class="filter-btn" onclick="filterResults('PASS')">PASS <span class="count">${passCount}</span></button>
        <button class="filter-btn" onclick="filterResults('FAIL')">FAIL <span class="count">${failCount}</span></button>
        <button class="filter-btn" onclick="filterResults('WARN')">WARN <span class="count">${warnCount}</span></button>
    `;

    // デフォルト: FAIL → WARN → PASS の順
    const sorted = sortByStatus(allResults);
    renderResultsTable(sorted);
    document.getElementById("resultsSection").style.display = "block";
}

/** ステータス順ソート（FAIL→WARN→PASS） */
function sortByStatus(results) {
    const order = { "FAIL": 0, "WARN": 1, "PASS": 2 };
    return [...results].sort((a, b) => (order[a.label] ?? 9) - (order[b.label] ?? 9));
}

function filterResults(filter) {
    currentFilter = filter;
    currentSort = { col: null, asc: true };
    document.querySelectorAll("#resultFilters .filter-btn").forEach(b => {
        b.classList.toggle("active", b.textContent.trim().startsWith(filter === "all" ? "すべて" : filter));
    });
    document.querySelectorAll("th.sortable").forEach(th => {
        th.classList.remove("sorted");
        const icon = th.querySelector(".sort-icon");
        if (icon) icon.textContent = "▲";
    });
    const filtered = filter === "all" ? allResults : allResults.filter(r => r.label === filter);
    renderResultsTable(sortByStatus(filtered));
}

function sortResults(col) {
    if (currentSort.col === col) {
        currentSort.asc = !currentSort.asc;
    } else {
        currentSort.col = col;
        currentSort.asc = true;
    }

    document.querySelectorAll("th.sortable").forEach(th => {
        th.classList.toggle("sorted", th.dataset.col === col);
        const icon = th.querySelector(".sort-icon");
        if (th.dataset.col === col) {
            icon.textContent = currentSort.asc ? "▲" : "▼";
        } else {
            icon.textContent = "▲";
        }
    });

    const filtered = currentFilter === "all" ? [...allResults] : allResults.filter(r => r.label === currentFilter);
    filtered.sort((a, b) => {
        let va = a[col], vb = b[col];
        if (typeof va === "string") va = va.toLowerCase();
        if (typeof vb === "string") vb = vb.toLowerCase();
        if (va < vb) return currentSort.asc ? -1 : 1;
        if (va > vb) return currentSort.asc ? 1 : -1;
        return 0;
    });
    renderResultsTable(filtered);
}

function renderResultsTable(results) {
    const tbody = document.getElementById("resultsBody");
    tbody.innerHTML = "";
    document.getElementById("resultsCount").textContent = `(${results.length} 件)`;

    for (const r of results) {
        const tr = document.createElement("tr");
        tr.className = "clickable";
        if (r.label === "FAIL") tr.classList.add("row-fail");
        else if (r.label === "WARN") tr.classList.add("row-warn");
        tr.innerHTML = `
            <td>${escapeHtml(r.name)}</td>
            <td><span style="font-size:12px;color:var(--text-secondary)">${escapeHtml(r.pattern)}</span></td>
            <td>${r.expected_status}</td>
            <td>${r.actual_status}</td>
            <td style="font-variant-numeric:tabular-nums">${r.elapsed_ms}ms</td>
            <td>${badgeHtml(r.label)}</td>
        `;
        tr.addEventListener("click", () => showDetail(r));
        tbody.appendChild(tr);
    }
}

function showDetail(r) {
    const panel = document.getElementById("detailPanel");
    let lines = [];
    lines.push(`${r.method} ${r.request_url || r.url_path}`);
    lines.push("");

    if (r.request_headers && Object.keys(r.request_headers).length) {
        for (const [k, v] of Object.entries(r.request_headers)) {
            const display = k.toLowerCase() === "authorization" ? v.slice(0, 12) + "***" : v;
            lines.push(`${k}: ${display}`);
        }
    }

    if (r.query_params && Object.keys(r.query_params).length) {
        lines.push("");
        lines.push("Query Parameters:");
        for (const [k, v] of Object.entries(r.query_params)) {
            lines.push(`  ${k} = ${v}`);
        }
    }

    lines.push("");
    lines.push(`Status: ${r.actual_status} (expected ${r.expected_status}) [${r.label}] - ${r.elapsed_ms}ms`);

    if (r.schema_warnings && r.schema_warnings.length) {
        lines.push("");
        lines.push("Schema Warnings:");
        for (const w of r.schema_warnings) lines.push(`  - ${w}`);
    }

    panel.textContent = lines.join("\n");
    document.getElementById("detailSection").style.display = "block";
}

refreshCsv();
updatePatternStatus();
