/* 共通ユーティリティ */

async function fetchJson(url, opts) {
    const res = await fetch(url, opts);
    return res.json();
}

async function postJson(url, data) {
    return fetchJson(url, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data),
    });
}

function badgeHtml(label) {
    const cls = label === "PASS" ? "badge-pass" : label === "FAIL" ? "badge-fail" : "badge-warn";
    return `<span class="badge ${cls}">${label}</span>`;
}

function formatTs(ts) {
    if (!ts || ts.length < 14) return ts;
    return `${ts.slice(0,4)}-${ts.slice(4,6)}-${ts.slice(6,8)} ${ts.slice(8,10)}:${ts.slice(10,12)}:${ts.slice(12,14)}`;
}

function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}

/* ── トースト通知 ── */
function showToast(message, type = "info", duration = 4000) {
    let container = document.querySelector(".toast-container");
    if (!container) {
        container = document.createElement("div");
        container.className = "toast-container";
        document.body.appendChild(container);
    }
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transition = "opacity .3s";
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

/* ── JSON シンタックスハイライト ── */
function highlightJson(jsonStr) {
    return jsonStr.replace(
        /("(?:\\.|[^"\\])*")\s*:/g,
        '<span class="json-key">$1</span>:'
    ).replace(
        /:\s*("(?:\\.|[^"\\])*")/g,
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
}

/* ── クリップボードコピー ── */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast("コピーしました", "success", 1500);
    });
}

/* ── 経過時間フォーマット ── */
function formatElapsed(ms) {
    const s = Math.floor(ms / 1000);
    if (s < 60) return `${s}秒`;
    const m = Math.floor(s / 60);
    return `${m}分${s % 60}秒`;
}
