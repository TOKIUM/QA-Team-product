/* Tab3: 設定 */

let keyVisible = false;

async function loadSettings() {
    const s = await fetchJson("/api/settings");
    document.getElementById("baseUrl").value = s.base_url || "";
    document.getElementById("apiKey").value = s.api_key || "";
    document.getElementById("timeout").value = s.timeout || 30;
    document.getElementById("pagOffset").value = (s.pagination || {}).offset || 0;
    document.getElementById("pagLimit").value = (s.pagination || {}).limit || 5;
    document.getElementById("concurrency").value = s.concurrency || 3;
    document.getElementById("slackUrl").value = s.slack_webhook_url || "";
    document.getElementById("slackFailOnly").checked = s.slack_failure_only !== false;

    const patterns = s.patterns || [];
    document.querySelectorAll("#patternChecks input").forEach(cb => {
        cb.checked = patterns.includes(cb.value);
    });
}

function toggleKey() {
    keyVisible = !keyVisible;
    document.getElementById("apiKey").type = keyVisible ? "text" : "password";
}

async function saveSettings() {
    const patterns = [];
    document.querySelectorAll("#patternChecks input:checked").forEach(cb => {
        patterns.push(cb.value);
    });

    const data = {
        base_url: document.getElementById("baseUrl").value,
        api_key: document.getElementById("apiKey").value,
        timeout: parseInt(document.getElementById("timeout").value) || 30,
        patterns: patterns,
        pagination_offset: parseInt(document.getElementById("pagOffset").value) || 0,
        pagination_limit: parseInt(document.getElementById("pagLimit").value) || 5,
        concurrency: parseInt(document.getElementById("concurrency").value) || 3,
        slack_webhook_url: document.getElementById("slackUrl").value,
        slack_failure_only: document.getElementById("slackFailOnly").checked,
    };

    const result = await postJson("/api/settings", data);
    const msgArea = document.getElementById("msgArea");

    if (result.status === "error") {
        showToast("設定エラー: " + result.errors.join("; "), "error", 6000);
    } else if (result.warnings && result.warnings.length) {
        showToast("保存しました（警告あり）", "info");
    } else {
        showToast("config.yaml と .env を更新しました", "success");
    }
    msgArea.innerHTML = "";
}

loadSettings();
