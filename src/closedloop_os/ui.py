LOCAL_CONSOLE_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ClosedLoop OS</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f7fb;
      --surface: #ffffff;
      --surface-soft: #f9fbff;
      --ink: #111827;
      --muted: #64748b;
      --line: #dbe3ef;
      --line-strong: #c3d0e0;
      --primary: #0f7ad1;
      --primary-dark: #075c9f;
      --success: #087f5b;
      --warning: #a16207;
      --danger: #b42318;
      --code: #0b1220;
      --shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.5 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    button, input, select, textarea { font: inherit; }

    .shell {
      min-height: 100vh;
      display: grid;
      grid-template-columns: 260px 1fr;
    }

    .sidebar {
      background: #101828;
      color: #eef4ff;
      padding: 22px 16px;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    .brand {
      padding: 4px 8px 18px;
      border-bottom: 1px solid rgba(255,255,255,0.12);
    }

    .brand h1 {
      margin: 0;
      font-size: 20px;
      letter-spacing: 0;
    }

    .brand p {
      margin: 6px 0 0;
      color: #9fb0c7;
      font-size: 13px;
    }

    .nav {
      display: grid;
      gap: 6px;
    }

    .nav button {
      width: 100%;
      text-align: left;
      border: 0;
      border-radius: 7px;
      padding: 10px 11px;
      color: #cdd8e8;
      background: transparent;
      cursor: pointer;
    }

    .nav button.active,
    .nav button:hover {
      color: #ffffff;
      background: rgba(255,255,255,0.10);
    }

    .sidebar-card {
      margin-top: auto;
      padding: 12px;
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 8px;
      background: rgba(255,255,255,0.06);
      color: #bed0e6;
      font-size: 13px;
    }

    .main {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    .topbar {
      height: 76px;
      padding: 16px 28px;
      background: var(--surface);
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
    }

    .topbar h2 {
      margin: 0;
      font-size: 22px;
      letter-spacing: 0;
    }

    .topbar p {
      margin: 2px 0 0;
      color: var(--muted);
    }

    .actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    .content {
      padding: 24px 28px 32px;
      display: grid;
      gap: 18px;
    }

    .view { display: none; }
    .view.active { display: grid; gap: 18px; }

    .grid-3 {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }

    .grid-2 {
      display: grid;
      grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr);
      gap: 18px;
      align-items: start;
    }

    .panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      box-shadow: var(--shadow);
    }

    .panel h3 {
      margin: 0 0 10px;
      font-size: 16px;
    }

    .metric {
      min-height: 112px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    .metric span {
      color: var(--muted);
      font-size: 13px;
    }

    .metric strong {
      font-size: 28px;
      letter-spacing: 0;
    }

    .connector-list {
      display: grid;
      gap: 10px;
    }

    .connector-card {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      align-items: center;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface-soft);
      cursor: pointer;
    }

    .connector-card.active {
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(15, 122, 209, 0.12);
    }

    .connector-card h4 {
      margin: 0;
      font-size: 14px;
    }

    .connector-card p {
      margin: 3px 0 0;
      color: var(--muted);
      font-size: 12px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 3px 9px;
      border-radius: 999px;
      border: 1px solid var(--line-strong);
      color: var(--muted);
      background: #ffffff;
      font-size: 12px;
      white-space: nowrap;
    }

    .badge.ok { color: var(--success); border-color: #a6e3c8; background: #effaf5; }
    .badge.warn { color: var(--warning); border-color: #f8d98a; background: #fff9e7; }
    .badge.bad { color: var(--danger); border-color: #f3b8b4; background: #fff3f2; }

    label {
      display: block;
      margin: 12px 0 6px;
      color: #334155;
      font-weight: 650;
      font-size: 13px;
    }

    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line-strong);
      border-radius: 7px;
      background: #ffffff;
      color: var(--ink);
      padding: 10px 11px;
      outline: none;
    }

    textarea {
      min-height: 122px;
      resize: vertical;
    }

    input:focus, select:focus, textarea:focus {
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(15, 122, 209, 0.12);
    }

    .button {
      border: 0;
      border-radius: 7px;
      min-height: 38px;
      padding: 9px 13px;
      color: #ffffff;
      background: var(--primary);
      cursor: pointer;
      font-weight: 700;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    .button:hover { background: var(--primary-dark); }
    .button.secondary {
      color: #1f2937;
      background: #ffffff;
      border: 1px solid var(--line-strong);
    }
    .button.secondary:hover { background: #f8fafc; }

    .button-row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 12px;
    }

    .help {
      color: var(--muted);
      font-size: 13px;
      margin: 8px 0 0;
    }

    .output {
      background: var(--code);
      color: #e7efff;
      border-radius: 8px;
      padding: 14px;
      min-height: 360px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font: 13px/1.55 "Cascadia Code", Consolas, ui-monospace, monospace;
    }

    .hidden { display: none; }

    @media (max-width: 1040px) {
      .shell { grid-template-columns: 1fr; }
      .sidebar { position: static; }
      .grid-3, .grid-2 { grid-template-columns: 1fr; }
      .topbar { height: auto; align-items: flex-start; flex-direction: column; }
      .actions { justify-content: flex-start; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <h1>ClosedLoop OS</h1>
        <p>Local control plane for tool intelligence.</p>
      </div>
      <nav class="nav">
        <button class="active" data-view="overview">Overview</button>
        <button data-view="connectors">Connect Tools</button>
        <button data-view="workbench">Test Workbench</button>
        <button data-view="intelligence">Intelligence</button>
        <button data-view="developer">Developer</button>
      </nav>
      <div class="sidebar-card">
        MCP runs at <strong>/mcp</strong>. Use <strong>/mcp-info</strong> for browser-readable details.
      </div>
    </aside>

    <main class="main">
      <header class="topbar">
        <div>
          <h2 id="page-title">Overview</h2>
          <p id="page-subtitle">Check the app, connected tools, and local runtime.</p>
        </div>
        <div class="actions">
          <a class="button secondary" href="/docs" target="_blank">API Docs</a>
          <a class="button secondary" href="/mcp-info" target="_blank">MCP Info</a>
          <button class="button" onclick="checkHealth()">Check Health</button>
        </div>
      </header>

      <div class="content">
        <section id="overview" class="view active">
          <div class="grid-3">
            <div class="panel metric">
              <span>Local API</span>
              <strong id="health-metric">Checking</strong>
              <span id="health-detail">http://127.0.0.1:8000</span>
            </div>
            <div class="panel metric">
              <span>Connected tools</span>
              <strong id="connected-count">0/0</strong>
              <span>Based on saved local settings</span>
            </div>
            <div class="panel metric">
              <span>Developer surfaces</span>
              <strong>3</strong>
              <span>UI, OpenAPI docs, MCP endpoint</span>
            </div>
          </div>

          <div class="grid-2">
            <div class="panel">
              <h3>Next steps</h3>
              <div class="connector-list">
                <div class="connector-card" onclick="showView('connectors')">
                  <div><h4>Connect a tool</h4><p>Paste API tokens or webhook secrets into local.settings.json from the UI.</p></div>
                  <span class="badge warn">Setup</span>
                </div>
                <div class="connector-card" onclick="showView('workbench')">
                  <div><h4>Send a sample event</h4><p>Test meeting upload or a sample Zendesk event from your browser.</p></div>
                  <span class="badge">Test</span>
                </div>
                <div class="connector-card" onclick="showView('intelligence')">
                  <div><h4>Ask a question</h4><p>Query indexed knowledge and inspect cited responses.</p></div>
                  <span class="badge">Ask</span>
                </div>
              </div>
            </div>
            <div class="panel">
              <h3>Output</h3>
              <pre class="output" id="output">Ready.</pre>
            </div>
          </div>
        </section>

        <section id="connectors" class="view">
          <div class="grid-2">
            <div class="panel">
              <h3>Tools</h3>
              <div class="connector-list" id="connector-list"></div>
            </div>
            <div class="panel">
              <h3 id="connector-heading">Select a tool</h3>
              <p class="help" id="connector-note">Choose a connector to configure.</p>
              <div id="connector-fields"></div>
              <div class="button-row">
                <button class="button" onclick="saveConnector()">Save Connection</button>
                <button class="button secondary" onclick="loadConnectors()">Refresh</button>
              </div>
              <p class="help">Saved values are masked in the UI and written to local.settings.json.</p>
            </div>
          </div>
        </section>

        <section id="workbench" class="view">
          <div class="grid-2">
            <div class="panel">
              <h3>Meeting transcript</h3>
              <label for="meeting">Transcript text</label>
              <textarea id="meeting">Ada: We decided ENG-101 is blocked by API-2.
Bob: Action: Ada will follow up with platform.</textarea>
              <div class="button-row">
                <button class="button" onclick="uploadMeeting()">Upload Transcript</button>
              </div>
            </div>
            <div class="panel">
              <h3>Sample Zendesk event</h3>
              <p class="help">Posts a realistic SLA breach event to the Zendesk connector.</p>
              <div class="button-row">
                <button class="button" onclick="sendZendesk()">Send SLA Breach</button>
              </div>
            </div>
          </div>
        </section>

        <section id="intelligence" class="view">
          <div class="grid-2">
            <div class="panel">
              <h3>Ask intelligence</h3>
              <label for="question">Question</label>
              <textarea id="question">What customer signals mention ENG-101?</textarea>
              <div class="button-row">
                <button class="button" onclick="askIntelligence()">Ask</button>
              </div>
            </div>
            <div class="panel">
              <h3>Search and graph</h3>
              <label for="query">Semantic search</label>
              <input id="query" value="Azure AI Search decision" />
              <label for="source">Source filter</label>
              <select id="source">
                <option value="">All sources</option>
                <option value="github">GitHub</option>
                <option value="slack">Slack</option>
                <option value="linear">Linear</option>
                <option value="jira">Jira</option>
                <option value="confluence">Confluence</option>
                <option value="zendesk">Zendesk</option>
                <option value="meeting">Meeting</option>
              </select>
              <label for="entity">Entity</label>
              <input id="entity" value="ENG-101" />
              <div class="button-row">
                <button class="button" onclick="semanticSearch()">Search</button>
                <button class="button secondary" onclick="entityGraph()">Graph</button>
                <button class="button secondary" onclick="timeline()">Timeline</button>
              </div>
            </div>
          </div>
        </section>

        <section id="developer" class="view">
          <div class="grid-2">
            <div class="panel">
              <h3>Runtime links</h3>
              <div class="button-row">
                <a class="button" href="/docs" target="_blank">OpenAPI Docs</a>
                <a class="button secondary" href="/api/status" target="_blank">API Status</a>
                <a class="button secondary" href="/mcp-info" target="_blank">MCP Info</a>
              </div>
              <p class="help">OpenAPI is best for raw endpoint testing. The MCP endpoint is for MCP clients.</p>
            </div>
            <div class="panel">
              <h3>Health</h3>
              <div class="button-row">
                <button class="button" onclick="checkHealth()">Check Health</button>
                <button class="button secondary" onclick="loadConnectors()">Refresh Connectors</button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  </div>

  <script>
    const pageTitles = {
      overview: ["Overview", "Check the app, connected tools, and local runtime."],
      connectors: ["Connect Tools", "Paste credentials once and use the tools immediately."],
      workbench: ["Test Workbench", "Send sample events and uploads through the local API."],
      intelligence: ["Intelligence", "Ask questions, search knowledge, and inspect entity context."],
      developer: ["Developer", "Open docs, MCP info, and runtime health checks."]
    };
    const output = document.getElementById("output");
    const connectorList = document.getElementById("connector-list");
    const connectorFields = document.getElementById("connector-fields");
    const connectorHeading = document.getElementById("connector-heading");
    const connectorNote = document.getElementById("connector-note");
    let connectorConfig = {};
    let selectedConnector = "";

    function show(data) {
      output.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
    }

    function showView(view) {
      document.querySelectorAll(".view").forEach((node) => node.classList.remove("active"));
      document.querySelectorAll(".nav button").forEach((node) => node.classList.remove("active"));
      document.getElementById(view).classList.add("active");
      document.querySelector(`[data-view="${view}"]`).classList.add("active");
      document.getElementById("page-title").textContent = pageTitles[view][0];
      document.getElementById("page-subtitle").textContent = pageTitles[view][1];
    }

    document.querySelectorAll(".nav button").forEach((button) => {
      button.addEventListener("click", () => showView(button.dataset.view));
    });

    async function request(path, options = {}) {
      const response = await fetch(path, options);
      const text = await response.text();
      let body;
      try { body = text ? JSON.parse(text) : null; } catch { body = text; }
      if (!response.ok) throw { status: response.status, body };
      return body;
    }

    async function run(action) {
      try {
        const result = await action();
        show(result);
        return result;
      } catch (error) {
        show({ error: true, status: error.status || "client", detail: error.body || String(error) });
        return null;
      }
    }

    async function checkHealth() {
      const result = await run(() => request("/healthz"));
      const metric = document.getElementById("health-metric");
      const detail = document.getElementById("health-detail");
      if (result && result.status === "ok") {
        metric.textContent = "Healthy";
        metric.style.color = "var(--success)";
        detail.textContent = "API responded with status ok";
      } else {
        metric.textContent = "Issue";
        metric.style.color = "var(--danger)";
        detail.textContent = "Health check failed";
      }
    }

    async function loadConnectors() {
      const result = await run(() => request("/api/connectors/config"));
      if (!result) return;
      connectorConfig = result.connectors || {};
      const entries = Object.entries(connectorConfig);
      const connected = entries.filter(([, config]) => config.connected).length;
      document.getElementById("connected-count").textContent = `${connected}/${entries.length}`;
      if (!selectedConnector && entries.length) selectedConnector = entries[0][0];
      connectorList.innerHTML = "";
      entries.forEach(([id, config]) => {
        const card = document.createElement("div");
        card.className = `connector-card ${id === selectedConnector ? "active" : ""}`;
        card.onclick = () => {
          selectedConnector = id;
          renderConnectors();
          renderConnectorForm();
        };
        card.innerHTML = `
          <div>
            <h4>${config.label}</h4>
            <p>${config.endpoint}</p>
          </div>
          <span class="badge ${config.connected ? "ok" : "warn"}">${config.connected ? "Connected" : "Needs setup"}</span>
        `;
        connectorList.appendChild(card);
      });
      renderConnectorForm();
    }

    function renderConnectors() {
      connectorList.querySelectorAll(".connector-card").forEach((card, index) => {
        const id = Object.keys(connectorConfig)[index];
        card.classList.toggle("active", id === selectedConnector);
      });
    }

    function renderConnectorForm() {
      const config = connectorConfig[selectedConnector];
      if (!config) return;
      connectorHeading.textContent = config.label;
      connectorNote.textContent = `${config.connected ? "Connected" : "Not connected"} | ${config.note}`;
      connectorFields.innerHTML = "";
      Object.entries(config.keys).forEach(([key, state]) => {
        const label = document.createElement("label");
        label.htmlFor = `cfg-${key}`;
        label.textContent = `${key}${state.configured ? ` (${state.preview})` : ""}`;
        const input = document.createElement("input");
        input.id = `cfg-${key}`;
        input.dataset.key = key;
        input.type = key.includes("SECRET") || key.includes("TOKEN") ? "password" : "text";
        input.placeholder = state.configured ? "Already saved. Paste a new value to replace." : "Paste value";
        connectorFields.appendChild(label);
        connectorFields.appendChild(input);
      });
    }

    async function saveConnector() {
      const values = {};
      connectorFields.querySelectorAll("input[data-key]").forEach((input) => {
        if (input.value.trim()) values[input.dataset.key] = input.value.trim();
      });
      if (!Object.keys(values).length) {
        show({ saved: false, message: "Paste at least one value before saving." });
        return;
      }
      const result = await run(() => request("/api/connectors/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ values })
      }));
      if (result) {
        connectorConfig = result.connectors || connectorConfig;
        await loadConnectors();
      }
    }

    async function askIntelligence() {
      await run(() => request("/api/tools/ask-intelligence", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: document.getElementById("question").value })
      }));
    }

    async function semanticSearch() {
      await run(() => request("/api/tools/semantic-search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query_text: document.getElementById("query").value,
          source_tool: document.getElementById("source").value || null,
          limit: 10
        })
      }));
    }

    async function entityGraph() {
      await run(() => request("/api/tools/entity-graph", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entity: document.getElementById("entity").value, limit: 25 })
      }));
    }

    async function timeline() {
      await run(() => request("/api/tools/timeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entity: document.getElementById("entity").value, limit: 25 })
      }));
    }

    async function uploadMeeting() {
      const blob = new Blob([document.getElementById("meeting").value], { type: "text/plain" });
      const form = new FormData();
      form.append("file", blob, "local-meeting.txt");
      await run(() => request("/api/connectors/meetings/upload", { method: "POST", body: form }));
    }

    async function sendZendesk() {
      await run(() => request("/api/demo/zendesk", { method: "POST" }));
    }

    checkHealth();
    loadConnectors();
  </script>
</body>
</html>
"""
