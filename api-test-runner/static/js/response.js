/* Tab2: レスポンス閲覧 */

let reportData = null;
let currentTab = "req";
let rawJson = "";

async function loadTimestamps() {
    const data = await fetchJson("/api/timestamps");
    const sel = document.getElementById("respTimestamp");
    sel.innerHTML = "";
    if (!data.timestamps || !data.timestamps.length) {
        sel.innerHTML = '<option value="">実行結果がありません</option>';
        return;
    }
    for (const ts of data.timestamps) {
        const opt = document.createElement("option");
        opt.value = ts;
        opt.textContent = formatTs(ts);
        sel.appendChild(opt);
    }
    onTimestampChange();
}

async function onTimestampChange() {
    const ts = document.getElementById("respTimestamp").value;
    if (!ts) return;

    const report = await fetchJson(`/api/report/${ts}`);
    reportData = report.error ? null : report;

    const data = await fetchJson(`/api/response/${ts}`);
    const list = document.getElementById("fileList");
    list.innerHTML = "";
    const files = data.files || [];
    document.getElementById("respFileCount").textContent = `${files.length} ファイル`;

    if (!files.length) {
        list.innerHTML = '<div class="empty-state" style="padding:20px"><p>ファイルがありません</p></div>';
        return;
    }

    for (const f of files) {
        const div = document.createElement("div");
        div.className = "item";
        // ファイル名から .json を除去して見やすく
        div.textContent = f.replace(/\.json$/, "");
        div.title = f;
        div.onclick = () => selectFile(ts, f, div);
        list.appendChild(div);
    }

    document.getElementById("reqPanel").textContent = "(ファイルを選択してください)";
    document.getElementById("resPanel").textContent = "(ファイルを選択してください)";
}

async function selectFile(ts, filename, el) {
    document.querySelectorAll("#fileList .item").forEach(i => i.classList.remove("active"));
    el.classList.add("active");

    const data = await fetchJson(`/api/response/${ts}/${encodeURIComponent(filename)}`);
    const resPanel = document.getElementById("resPanel");

    if (data.error) {
        resPanel.textContent = data.error;
        rawJson = "";
    } else {
        rawJson = JSON.stringify(data.data, null, 4);
        resPanel.innerHTML = `<button class="copy-btn" onclick="copyToClipboard(rawJson)">Copy</button>` +
            highlightJson(escapeHtml(rawJson));
    }

    document.getElementById("reqPanel").textContent = buildRequestInfo(filename);
    showTab(currentTab);
}

function buildRequestInfo(filename) {
    if (!reportData) return "(report.json がないため、リクエスト情報を表示できません)";

    const entry = (reportData.tests || []).find(t => t.output_file === filename);
    if (!entry) return `(report.json に ${filename} の情報がありません)`;

    let lines = [];
    const url = entry.request_url || entry.url_path || "";
    lines.push(`${entry.method || "GET"} ${url}`);
    lines.push("");

    const headers = entry.request_headers;
    if (headers && Object.keys(headers).length) {
        lines.push("Headers:");
        for (const [k, v] of Object.entries(headers)) lines.push(`  ${k}: ${v}`);
    } else {
        lines.push("Headers:");
        lines.push("  Accept: application/json");
        lines.push(entry.use_auth ? "  Authorization: Bearer ***" : "  (認証なし)");
    }

    const params = entry.query_params || {};
    if (Object.keys(params).length) {
        lines.push("");
        lines.push("Query Parameters:");
        for (const [k, v] of Object.entries(params)) lines.push(`  ${k} = ${v}`);
    }

    lines.push("");
    const label = entry.passed ? "PASS" : "FAIL";
    lines.push(`Status: ${entry.actual_status} (expected ${entry.expected_status}) [${label}] - ${(entry.elapsed_ms || 0).toFixed(0)}ms`);

    return lines.join("\n");
}

function showTab(tab) {
    currentTab = tab;
    document.getElementById("reqPanel").style.display = tab === "req" ? "block" : "none";
    document.getElementById("resPanel").style.display = tab === "res" ? "block" : "none";
    document.getElementById("tabReq").style.background = tab === "req" ? "#e2e8f0" : "";
    document.getElementById("tabRes").style.background = tab === "res" ? "#e2e8f0" : "";
}

showTab("req");
loadTimestamps();
