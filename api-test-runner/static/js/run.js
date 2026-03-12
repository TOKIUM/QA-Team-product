/* Tab1: テスト実行 */

let pollTimer = null;
let runStartTime = null;
let allResults = [];
let currentFilter = "all";
let currentSort = { col: null, asc: true };
let csvFileList = [];  // 全CSVファイル情報 [{name, method, url_path}, ...]
let showOpCols = false;  // 操作・データ変化列の表示フラグ
let getEndpoints = {};   // url_path → GETエンドポイントのマッピング（設定から取得）
let resourceCache = {};  // getEndpoint → items[] のキャッシュ
let resourceSelections = {};  // apiKey → [id, id, ...]（API別の選択状態、複数可）
const ALL_PATTERNS = ["auth", "pagination", "search", "boundary", "missing_required", "post_normal", "put_normal", "delete_normal", "patch_normal"];

/** CSVファイル名からAPI名を抽出する */
function extractApiName(filename) {
    const m = filename.match(/- (\d+)(.+?)\.csv$/);
    if (m) return m[1] + " " + m[2];
    return filename.replace(/\.csv$/, "");
}

/** 選択中のCSVファイル名を取得 */
function getSelectedCsvFiles() {
    const checked = document.querySelectorAll("#csvFiles tbody input[type=checkbox]:checked");
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
    // リソースパネルの表示制御
    updateResourcePanel();
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
        const apiName = tr.querySelector("td:nth-child(4)")?.textContent?.toLowerCase() || "";
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

    // リソース選択パネルの表示制御
    updateResourcePanel();

    // post_normal注意表示
    const warnEl = document.getElementById("postNormalWarning");
    if (selected.includes("post_normal")) {
        if (!warnEl) {
            const div = document.createElement("div");
            div.id = "postNormalWarning";
            div.style.cssText = "font-size:12px;margin-top:6px;padding:8px 12px;border-radius:8px;background:var(--warn-bg);color:#92400e;border-left:4px solid var(--warn)";
            div.textContent = "⚠ post_normal: 実データを作成/変更/削除します。テスト環境でのみ実行してください";
            document.getElementById("patternChecks").parentNode.appendChild(div);
        }
    } else {
        if (warnEl) warnEl.remove();
    }
}

// ─── リソース選択パネル ──────────────────────────

/** 選択中CSVとパターンからリソース選択パネルの表示を制御 */
function updateResourcePanel() {
    const section = document.getElementById("resourceSection");
    const patterns = getSelectedPatterns();
    const hasWritePattern = patterns.some(p =>
        ["post_normal", "put_normal", "delete_normal", "patch_normal"].includes(p));

    if (!hasWritePattern) {
        section.style.display = "none";
        return;
    }

    // 選択中のPOST系CSVで、get_endpointsにマッピングがあるものを探す
    const selectedFiles = getSelectedCsvFiles();
    const matchedApis = [];  // {apiKey, apiLabel, url_path, getEndpoint}
    for (const info of csvFileList) {
        if (info.method !== "POST") continue;
        if (selectedFiles.length > 0 && !selectedFiles.includes(info.name)) continue;
        const getEp = getEndpoints[info.url_path];
        if (!getEp) continue;
        const apiKey = info.url_path.replace(".json", "").replace("/", "-");
        // 重複除去
        if (matchedApis.some(a => a.apiKey === apiKey)) continue;
        // ラベル生成: "projects-bulk_update_job" → "projects 更新"
        const label = extractApiLabel(apiKey);
        matchedApis.push({ apiKey, apiLabel: label, url_path: info.url_path, getEndpoint: getEp });
    }

    if (matchedApis.length === 0) {
        section.style.display = "none";
        return;
    }

    section.style.display = "block";
    renderResourceGroups(matchedApis);
}

/** apiKeyからUI表示用ラベルを生成 */
function extractApiLabel(apiKey) {
    // "projects-bulk_update_job" → "projects / 更新"
    const opMap = { create: "登録", update: "更新", delete: "削除" };
    for (const [en, ja] of Object.entries(opMap)) {
        if (apiKey.includes(en)) {
            const resource = apiKey.split("-")[0];
            return `${resource} / ${ja}`;
        }
    }
    return apiKey;
}

/** API別グループでリソース選択UIを描画 */
async function renderResourceGroups(matchedApis) {
    const listEl = document.getElementById("resourceList");
    const statusEl = document.getElementById("resourceStatus");
    statusEl.textContent = `(${matchedApis.length} API)`;

    // 必要なGETエンドポイントを重複なく取得
    const uniqueEndpoints = [...new Set(matchedApis.map(a => a.getEndpoint))];

    // キャッシュにないエンドポイントを並列フェッチ
    const fetches = uniqueEndpoints
        .filter(ep => !resourceCache[ep])
        .map(async ep => {
            const data = await fetchJson(
                `/api/resources?endpoint=${encodeURIComponent(ep)}&limit=100`);
            resourceCache[ep] = data.error ? [] : (data.items || []);
        });

    if (fetches.length > 0) {
        listEl.innerHTML = '<div class="empty-state"><div class="icon">...</div><p>リソースを取得中...</p></div>';
        await Promise.all(fetches);
    }

    // グループ別描画
    let html = '';
    for (const api of matchedApis) {
        const items = resourceCache[api.getEndpoint] || [];
        const selectedId = resourceSelections[api.apiKey] || "";
        const radioName = `res_${api.apiKey}`;

        const selectedIds = selectedId || [];
        const selCount = selectedIds.length;

        html += `<details class="resource-group" open>
            <summary style="cursor:pointer;font-weight:600;padding:6px 0;border-bottom:1px solid #eee;margin-bottom:4px">
                ${escapeHtml(api.apiLabel)}
                <span style="font-weight:400;color:var(--text-secondary);font-size:12px;margin-left:8px">${api.getEndpoint} (${items.length}件)</span>
                ${selCount > 0 ? `<span style="color:var(--primary);font-size:12px;margin-left:4px">✓ ${selCount}件選択</span>` : ''}
            </summary>`;

        if (items.length === 0) {
            html += '<div style="padding:4px 8px;color:#999;font-size:13px">リソースなし</div>';
        } else {
            const idField = items[0].id !== undefined ? "id" : Object.keys(items[0])[0];
            const nameField = items[0].name !== undefined ? "name"
                : items[0].title !== undefined ? "title"
                : Object.keys(items[0]).find(k => k !== idField) || idField;

            html += `<div style="max-height:160px;overflow:auto"><table><tbody>`;
            for (const item of items) {
                const id = String(item[idField] || "");
                const name = String(item[nameField] || "");
                const checked = selectedIds.includes(id) ? "checked" : "";
                html += `<tr class="clickable" data-api-key="${escapeHtml(api.apiKey)}" data-id="${escapeHtml(id)}">
                    <td style="width:36px"><input type="checkbox" value="${escapeHtml(id)}"
                        ${checked} onchange="onResourceToggle('${escapeHtml(api.apiKey)}', this.value, this.checked)"></td>
                    <td class="text-sm" style="font-family:monospace;width:120px">${escapeHtml(id.substring(0, 12))}…</td>
                    <td style="font-weight:500">${escapeHtml(name)}</td>
                </tr>`;
            }
            html += `</tbody></table></div>`;
        }
        html += `</details>`;
    }
    listEl.innerHTML = html;

    // 行クリックでチェックボックストグル
    listEl.querySelectorAll("tbody tr.clickable").forEach(tr => {
        tr.addEventListener("click", (e) => {
            if (e.target.tagName === "INPUT") return;
            const cb = tr.querySelector("input[type=checkbox]");
            if (cb) {
                cb.checked = !cb.checked;
                onResourceToggle(tr.dataset.apiKey, tr.dataset.id, cb.checked);
            }
        });
    });
}

/** チェックボックストグル時（API別・複数選択対応） */
function onResourceToggle(apiKey, id, checked) {
    if (!resourceSelections[apiKey]) resourceSelections[apiKey] = [];
    if (checked) {
        if (!resourceSelections[apiKey].includes(id)) {
            resourceSelections[apiKey].push(id);
        }
    } else {
        resourceSelections[apiKey] = resourceSelections[apiKey].filter(v => v !== id);
    }
    updateResourceSelectionStatus();
}

/** 選択状態のサマリー表示を更新 */
function updateResourceSelectionStatus() {
    const totalSelected = Object.values(resourceSelections)
        .reduce((sum, ids) => sum + ids.length, 0);
    const apiCount = Object.values(resourceSelections)
        .filter(ids => ids.length > 0).length;
    const statusEl = document.getElementById("resourceStatus");
    if (totalSelected > 0) {
        statusEl.textContent = `(${apiCount} API / ${totalSelected}件 選択中)`;
    } else {
        statusEl.textContent = "";
    }
}

/** リソース検索フィルタ */
function filterResourceList() {
    const query = document.getElementById("resourceSearch").value.toLowerCase();
    document.querySelectorAll("#resourceList tbody tr").forEach(tr => {
        const text = tr.textContent.toLowerCase();
        tr.style.display = text.includes(query) ? "" : "none";
    });
}

/** 全選択状態からbody_overridesを構築（複数選択対応） */
function buildBodyOverrides() {
    const overrides = {};
    let hasAny = false;
    for (const [apiKey, ids] of Object.entries(resourceSelections)) {
        if (!ids || ids.length === 0) continue;
        hasAny = true;
        if (ids.length === 1) {
            overrides[apiKey] = { id: ids[0] };
        } else {
            overrides[apiKey] = ids.map(id => ({ id }));
        }
    }
    return hasAny ? overrides : null;
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

    csvFileList = data.files.map(f => typeof f === "string"
        ? { name: f, method: "", url_path: "" }
        : { name: f.name, method: f.method || "", url_path: f.url_path || "" });
    countEl.textContent = `(${data.files.length} ファイル)`;

    let html = '<table><thead><tr><th style="width:36px"><input type="checkbox" id="csvSelectAll" onchange="selectAllCsv(this.checked)" checked></th><th style="width:36px">#</th><th style="width:60px">メソッド</th><th>API名</th></tr></thead><tbody>';
    for (let i = 0; i < data.files.length; i++) {
        const item = data.files[i];
        const fname = typeof item === "string" ? item : item.name;
        const method = (typeof item === "object" && item.method) || "";
        const apiName = extractApiName(fname);
        const methodBadge = method === "POST"
            ? '<span style="background:#e3f2fd;color:#1565c0;padding:1px 6px;border-radius:3px;font-size:11px;font-weight:600">POST</span>'
            : method === "GET"
            ? '<span style="background:#e8f5e9;color:#2e7d32;padding:1px 6px;border-radius:3px;font-size:11px;font-weight:600">GET</span>'
            : `<span style="background:#f5f5f5;color:#666;padding:1px 6px;border-radius:3px;font-size:11px;font-weight:600">${escapeHtml(method)}</span>`;
        html += `<tr>
            <td><input type="checkbox" value="${escapeHtml(fname)}" checked onchange="updateSelectedCount()"></td>
            <td class="text-secondary">${i + 1}</td>
            <td>${methodBadge}</td>
            <td style="font-weight:500" title="${escapeHtml(fname)}">${escapeHtml(apiName)}</td>
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

    // リソース選択からbody_overridesを構築
    const overrides = buildBodyOverrides();
    if (overrides) {
        body.body_overrides = overrides;
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
        <div class="summary-card"><div class="value">${s.total}</div><div class="label">Total</div></div>
        <div class="summary-card"><div class="value" style="color:var(--pass)">${s.passed}</div><div class="label">Passed</div></div>
        <div class="summary-card"><div class="value" style="color:var(--fail)">${s.failed}</div><div class="label">Failed</div></div>
        <div class="summary-card"><div class="value" style="color:var(--warn)">${s.warn || 0}</div><div class="label">Warn</div></div>
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

    // 操作・データ変化列の表示判定（1回だけ）
    showOpCols = allResults.some(r => r.operation || r.data_comparison);
    const headerRow = document.getElementById("resultsHeader");
    headerRow.innerHTML = `
        <th class="sortable" data-col="name" onclick="sortResults('name')">テスト名 <span class="sort-icon">▲</span></th>
        <th class="sortable col-desc" data-col="description" onclick="sortResults('description')">検証内容 <span class="sort-icon">▲</span></th>
        ${showOpCols ? '<th>操作</th>' : ''}
        <th>期待</th>
        <th>実際</th>
        <th class="sortable" data-col="elapsed_ms" onclick="sortResults('elapsed_ms')">時間 <span class="sort-icon">▲</span></th>
        ${showOpCols ? '<th>データ変化</th>' : ''}
        <th class="sortable" data-col="label" onclick="sortResults('label')">結果 <span class="sort-icon">▲</span></th>
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

/** 操作種別バッジHTML */
function operationBadgeHtml(op) {
    const map = {
        create: { text: "追加", bg: "#e8f5e9", color: "#2e7d32", icon: "＋" },
        update: { text: "更新", bg: "#fff3e0", color: "#e65100", icon: "✎" },
        delete: { text: "削除", bg: "#fce4ec", color: "#c62828", icon: "✕" },
        post:   { text: "POST", bg: "#e3f2fd", color: "#1565c0", icon: "→" },
    };
    const m = map[op];
    if (!m) return "";
    return `<span style="background:${m.bg};color:${m.color};padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;white-space:nowrap">${m.icon} ${m.text}</span>`;
}

/** データ変化サマリーHTML（テーブル行内用） */
function dataDiffSummaryHtml(r) {
    if (!r.data_comparison) return '<span style="color:#999">—</span>';
    const dc = r.data_comparison;
    const parts = [];
    if (dc._total) {
        const d = dc._total.diff;
        if (d > 0) parts.push(`<span style="color:var(--pass);font-weight:600">+${d}件</span>`);
        else if (d < 0) parts.push(`<span style="color:var(--fail);font-weight:600">${d}件</span>`);
        else parts.push(`<span style="color:#999">±0件</span>`);
    }
    for (const [key, d] of Object.entries(dc)) {
        if (key === "_total") continue;
        if (d.changed_count > 0) {
            parts.push(`<span style="color:var(--warn);font-size:11px">${d.changed_count}件変更</span>`);
        }
    }
    return parts.join(" ") || '<span style="color:#999">—</span>';
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
        const descText = r.description || r.pattern;
        tr.innerHTML = `
            <td class="col-name" title="${escapeHtml(r.name)}">${escapeHtml(r.name)}</td>
            <td class="col-desc" title="${escapeHtml(descText)}"><span class="text-sm">${escapeHtml(descText)}</span></td>
            ${showOpCols ? `<td>${operationBadgeHtml(r.operation)}</td>` : ''}
            <td>${r.expected_status}</td>
            <td>${r.actual_status}</td>
            <td style="font-variant-numeric:tabular-nums">${r.elapsed_ms}ms</td>
            ${showOpCols ? `<td>${dataDiffSummaryHtml(r)}</td>` : ''}
            <td>${badgeHtml(r.label)}</td>
        `;
        tr.addEventListener("click", () => showDetail(r));
        tbody.appendChild(tr);
    }
}

function showDetail(r) {
    const panel = document.getElementById("detailPanel");
    let html = '';

    if (r.description) {
        html += `<div class="detail-section-label">検証内容</div>`;
        html += `<div class="detail-section-content">${escapeHtml(r.description)}</div>`;
    }

    html += `<div class="detail-section-label">リクエスト</div>`;
    html += `<div class="detail-section-content">${escapeHtml(r.method)} ${escapeHtml(r.request_url || r.url_path)}</div>`;

    if (r.request_headers && Object.keys(r.request_headers).length) {
        html += `<div class="detail-section-label">ヘッダー</div>`;
        let headerLines = [];
        for (const [k, v] of Object.entries(r.request_headers)) {
            const display = k.toLowerCase() === "authorization" ? v.slice(0, 12) + "***" : v;
            headerLines.push(`${escapeHtml(k)}: ${escapeHtml(display)}`);
        }
        html += `<div class="detail-section-content">${headerLines.join('\n')}</div>`;
    }

    if (r.query_params && Object.keys(r.query_params).length) {
        html += `<div class="detail-section-label">パラメータ</div>`;
        let paramLines = [];
        for (const [k, v] of Object.entries(r.query_params)) {
            paramLines.push(`  ${escapeHtml(k)} = ${escapeHtml(String(v))}`);
        }
        html += `<div class="detail-section-content">${paramLines.join('\n')}</div>`;
    }

    if (r.request_body && Object.keys(r.request_body).length) {
        html += `<div class="detail-section-label">リクエストボディ</div>`;
        html += `<div class="detail-section-content"><pre style="margin:0;white-space:pre-wrap">${escapeHtml(JSON.stringify(r.request_body, null, 2))}</pre></div>`;
    }

    html += `<div class="detail-section-label">結果</div>`;
    html += `<div class="detail-section-content">Status: ${r.actual_status} (expected ${r.expected_status}) [${r.label}] - ${r.elapsed_ms}ms</div>`;

    if (r.data_comparison) {
        const opLabel = { create: "追加", update: "更新", delete: "削除" }[r.operation] || "実行";
        html += `<div class="detail-section-label">データ比較 — ${opLabel}結果</div>`;
        let dcHtml = '';
        const dc = r.data_comparison;

        // 総件数カード
        if (dc._total) {
            const diff = dc._total.diff;
            const sign = diff > 0 ? '+' : '';
            const diffColor = diff > 0 ? 'var(--pass)' : diff < 0 ? 'var(--fail)' : '#999';
            dcHtml += `<div style="display:flex;align-items:center;gap:16px;margin-bottom:12px;padding:10px 14px;background:#f8f9fa;border-radius:8px;border-left:4px solid ${diffColor}">
                <div style="text-align:center"><div style="font-size:22px;font-weight:700;color:#333">${dc._total.before_total}</div><div style="font-size:11px;color:#888">実行前</div></div>
                <div style="font-size:20px;color:${diffColor};font-weight:700">→</div>
                <div style="text-align:center"><div style="font-size:22px;font-weight:700;color:#333">${dc._total.after_total}</div><div style="font-size:11px;color:#888">実行後</div></div>
                <div style="font-size:16px;font-weight:700;color:${diffColor};margin-left:8px">${sign}${diff}件</div>
            </div>`;
        }

        // リソース別詳細
        for (const [resource, d] of Object.entries(dc)) {
            if (resource === '_total') continue;

            // 追加されたリソース
            if (d.added_ids && d.added_ids.length) {
                dcHtml += `<div style="margin-bottom:8px;padding:8px 12px;background:#e8f5e9;border-radius:6px;border-left:3px solid #4caf50">`;
                dcHtml += `<div style="font-weight:600;color:#2e7d32;margin-bottom:4px">＋ 追加 (${d.added_count}件)</div>`;
                for (const id of d.added_ids) {
                    dcHtml += `<div style="font-size:12px;color:#333;margin-left:8px">ID: <code style="background:#c8e6c9;padding:1px 4px;border-radius:3px">${escapeHtml(id)}</code></div>`;
                }
                dcHtml += `</div>`;
            }

            // 削除されたリソース
            if (d.removed_ids && d.removed_ids.length) {
                dcHtml += `<div style="margin-bottom:8px;padding:8px 12px;background:#fce4ec;border-radius:6px;border-left:3px solid #e53935">`;
                dcHtml += `<div style="font-weight:600;color:#c62828;margin-bottom:4px">✕ 削除 (${d.removed_count}件)</div>`;
                for (const id of d.removed_ids) {
                    dcHtml += `<div style="font-size:12px;color:#333;margin-left:8px">ID: <code style="background:#f8bbd0;padding:1px 4px;border-radius:3px">${escapeHtml(id)}</code></div>`;
                }
                dcHtml += `</div>`;
            }

            // 変更されたリソース
            if (d.changed && Object.keys(d.changed).length) {
                dcHtml += `<div style="margin-bottom:8px;padding:8px 12px;background:#fff3e0;border-radius:6px;border-left:3px solid #ff9800">`;
                dcHtml += `<div style="font-weight:600;color:#e65100;margin-bottom:4px">✎ 変更 (${d.changed_count}件)</div>`;
                for (const [itemId, changes] of Object.entries(d.changed)) {
                    dcHtml += `<div style="font-size:12px;margin-left:8px;margin-bottom:4px">ID: <code style="background:#ffe0b2;padding:1px 4px;border-radius:3px">${escapeHtml(itemId)}</code></div>`;
                    for (const [field, vals] of Object.entries(changes)) {
                        if (field === "updated_at" || field === "created_at") continue;
                        dcHtml += `<div style="font-size:12px;margin-left:20px;color:#555">
                            <span style="color:#888">${escapeHtml(field)}:</span>
                            <span style="text-decoration:line-through;color:#c62828">${escapeHtml(String(vals.before))}</span>
                            → <span style="color:#2e7d32;font-weight:500">${escapeHtml(String(vals.after))}</span>
                        </div>`;
                    }
                }
                dcHtml += `</div>`;
            }

            // 変化なしの場合
            if (d.added_count === 0 && d.removed_count === 0 && d.changed_count === 0) {
                dcHtml += `<div style="color:#999;font-size:12px;padding:4px 0">変化なし (${resource}: ${d.before_count}件 → ${d.after_count}件)</div>`;
            }
        }
        html += `<div class="detail-section-content">${dcHtml}</div>`;
    }

    if (r.response_body) {
        html += `<div class="detail-section-label">レスポンスボディ</div>`;
        // escapeHtml してからハイライト: エスケープ済み引用符 &quot; に対応した正規表現を使用
        const escaped = escapeHtml(r.response_body);
        const highlighted = escaped.replace(
            /(&quot;(?:\\.|[^&])*?&quot;)\s*:/g,
            '<span class="json-key">$1</span>:'
        ).replace(
            /:\s*(&quot;(?:\\.|[^&])*?&quot;)/g,
            ': <span class="json-string">$1</span>'
        ).replace(
            /:\s*(-?\d+\.?\d*(?:[eE][+-]?\d+)?)/g,
            ': <span class="json-number">$1</span>'
        ).replace(
            /:\s*(true|false)/g,
            ': <span class="json-boolean">$1</span>'
        ).replace(
            /:\s*(null)/g,
            ': <span class="json-null">$1</span>'
        );
        html += `<div class="detail-section-content"><div class="json-view" style="max-height:300px">${highlighted}</div>`;
        if (r.response_body_truncated) {
            html += `<div style="margin-top:6px;font-size:12px;color:var(--text-secondary)">※ 先頭2000文字のみ表示。<a href="/response" style="color:var(--primary)">レスポンスタブ</a>で全文を確認できます</div>`;
        }
        html += `</div>`;
    }

    if (r.schema_warnings && r.schema_warnings.length) {
        html += `<div class="detail-section-label">Schema Warnings</div>`;
        let warnLines = r.schema_warnings.map(w => `  - ${escapeHtml(w)}`);
        html += `<div class="detail-section-content">${warnLines.join('\n')}</div>`;
    }

    panel.innerHTML = html;
    document.getElementById("detailSection").style.display = "block";
}

refreshCsv();

// config.yamlの設定を取得してパターン・get_endpointsを初期化
(async function initPatterns() {
    try {
        const settings = await fetchJson("/api/settings");
        if (settings.patterns && Array.isArray(settings.patterns)) {
            const activePatterns = new Set(settings.patterns);
            // get_endpointsマッピングを取得
            if (settings.get_endpoints) {
                getEndpoints = settings.get_endpoints;
            }
            document.querySelectorAll("#patternChecks .filter-btn[data-pat]").forEach(btn => {
                btn.classList.toggle("active", activePatterns.has(btn.dataset.pat));
            });
        } else {
            // patternsが未定義なら全activeにフォールバック
            selectAllPatterns(true);
        }
    } catch (e) {
        // 設定取得失敗時は全activeにフォールバック
        selectAllPatterns(true);
    }
    updatePatternStatus();
})();
