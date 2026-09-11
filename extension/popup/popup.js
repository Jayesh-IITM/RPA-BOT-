/**
 * MahaSetu RPA Recorder - Popup Script
 * Enhanced with Live Action Counter & Saved Bot API Quick Runner
 */

const DEFAULT_SERVER_URL = "https://rpa-bot-production.up.railway.app";
let activeBackendUrl = DEFAULT_SERVER_URL;

document.addEventListener("DOMContentLoaded", () => {
  const statusBadge = document.getElementById("popup-status");
  const idleControls = document.getElementById("idle-controls");
  const activeControls = document.getElementById("active-controls");
  const actionCounter = document.getElementById("action-counter");
  const btnStart = document.getElementById("btn-start-record");
  const btnStop = document.getElementById("btn-stop-record");
  const btnPortal = document.getElementById("btn-open-portal");
  const btnDemo = document.getElementById("btn-open-demo");

  // Server indicator elements
  const serverDisplay = document.getElementById("server-url-display");
  const serverStatusDot = document.getElementById("server-status-dot");
  const serverPingBadge = document.getElementById("server-ping-badge");
  const btnToggleSettings = document.getElementById("btn-toggle-settings");
  const settingsDrawer = document.getElementById("settings-drawer");
  const btnCloseDrawer = document.getElementById("btn-close-drawer");
  const inputServerUrl = document.getElementById("input-server-url");
  const btnSaveServer = document.getElementById("btn-save-server");
  const btnTestServer = document.getElementById("btn-test-server");
  const btnOpenOptions = document.getElementById("btn-open-options");
  const drawerMsg = document.getElementById("drawer-msg");

  // Bots Section
  const btnToggleBots = document.getElementById("btn-toggle-bots");
  const botsChevron = document.getElementById("bots-chevron");
  const botsListContainer = document.getElementById("bots-list-container");

  // Load configured backend URL
  getStoredBackendUrl((url) => {
    activeBackendUrl = url;
    serverDisplay.innerText = url.replace(/^https?:\/\//, "");
    serverDisplay.title = url;
    inputServerUrl.value = url;
    checkServerHealth(url);
    loadSavedBots(url);
  });

  // Check current recording state
  chrome.runtime.sendMessage({ type: "GET_RECORDING_STATE" }, (data) => {
    if (data && data.isRecording) {
      showRecordingState((data.recordedActions || []).length);
    } else {
      showIdleState();
    }
  });

  // Poll action count while popup is open and recording is active
  const actionPoller = setInterval(() => {
    chrome.storage.local.get(["isRecording", "recordedActions"], (data) => {
      if (data && data.isRecording) {
        showRecordingState((data.recordedActions || []).length);
      }
    });
  }, 1000);

  window.addEventListener("unload", () => {
    clearInterval(actionPoller);
  });

  function showRecordingState(count = 0) {
    statusBadge.innerText = "RECORDING";
    statusBadge.className = "status-badge status-recording";
    idleControls.style.display = "none";
    activeControls.style.display = "block";
    if (actionCounter) {
      actionCounter.innerText = `${count} action${count === 1 ? '' : 's'}`;
    }
  }

  function showIdleState() {
    statusBadge.innerText = "IDLE";
    statusBadge.className = "status-badge status-idle";
    idleControls.style.display = "block";
    activeControls.style.display = "none";
  }

  async function checkServerHealth(url) {
    serverStatusDot.className = "server-dot";
    serverPingBadge.innerText = "...";
    const start = Date.now();
    try {
      const controller = new AbortController();
      const tid = setTimeout(() => controller.abort(), 4500);
      const res = await fetch(`${url}/api/health`, { signal: controller.signal });
      clearTimeout(tid);
      const latency = Date.now() - start;
      if (res.ok) {
        serverStatusDot.className = "server-dot online";
        serverPingBadge.innerText = `${latency}ms`;
        serverStatusDot.title = `Server Online (${latency}ms)`;
      } else {
        serverStatusDot.className = "server-dot offline";
        serverPingBadge.innerText = `HTTP ${res.status}`;
      }
    } catch (e) {
      serverStatusDot.className = "server-dot offline";
      serverPingBadge.innerText = "Offline";
      serverStatusDot.title = "Server unreachable";
    }
  }

  // Fetch saved bots from server to display in popup
  async function loadSavedBots(url) {
    if (!botsListContainer) return;
    try {
      const controller = new AbortController();
      const tid = setTimeout(() => controller.abort(), 4000);
      const res = await fetch(`${url}/api/bots`, { signal: controller.signal });
      clearTimeout(tid);

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const bots = data.bots || [];

      if (bots.length === 0) {
        botsListContainer.innerHTML = `<div style="color: #64748b; font-size: 10px; padding: 4px;">No saved bots yet. Record one above!</div>`;
        return;
      }

      botsListContainer.innerHTML = "";
      bots.forEach((b) => {
        const item = document.createElement("div");
        item.className = "bot-item";

        const botTitle = b.name.length > 22 ? b.name.substring(0, 20) + "..." : b.name;
        item.innerHTML = `
          <div style="overflow: hidden; max-width: 190px;">
            <div style="color: #e2e8f0; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escapeHtml(b.name)}">
              ${escapeHtml(botTitle)}
            </div>
            <div style="color: #64748b; font-size: 9px;">${(b.steps || []).length} steps &bull; ${b.id}</div>
          </div>
          <div style="display: flex; gap: 4px;">
            <button class="btn-sm btn-api-copy" data-bot-id="${b.id}" style="background: rgba(255,255,255,0.05); color: #94a3b8; border: 1px solid rgba(255,255,255,0.08);" title="Copy Direct API Endpoint">API</button>
            <button class="btn-sm btn-run-bot" data-bot-id="${b.id}" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3);" title="Trigger Bot Headless">⚡ Run</button>
          </div>
        `;
        botsListContainer.appendChild(item);
      });

      // Bind copy and run buttons
      botsListContainer.querySelectorAll(".btn-api-copy").forEach((btn) => {
        btn.onclick = (e) => {
          e.stopPropagation();
          const botId = btn.dataset.botId;
          const ep = `${activeBackendUrl}/api/bots/${botId}/execute`;
          navigator.clipboard.writeText(ep);
          btn.innerText = "✓ Copied";
          setTimeout(() => { btn.innerText = "API"; }, 1500);
        };
      });

      botsListContainer.querySelectorAll(".btn-run-bot").forEach((btn) => {
        btn.onclick = async (e) => {
          e.stopPropagation();
          const botId = btn.dataset.botId;
          btn.disabled = true;
          btn.innerText = "⏳...";

          try {
            const r = await fetch(`${activeBackendUrl}/api/bots/${botId}/execute`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ options: { headless: true } })
            });
            const resJson = await r.json();
            if (resJson.success) {
              btn.innerText = "✓ Done";
              btn.style.background = "rgba(16, 185, 129, 0.2)";
              btn.style.color = "#34d399";
            } else {
              btn.innerText = "✕ Err";
              btn.style.background = "rgba(239, 68, 68, 0.2)";
              btn.style.color = "#f87171";
            }
          } catch (err) {
            btn.innerText = "✕ Err";
          } finally {
            setTimeout(() => {
              btn.disabled = false;
              btn.innerText = "⚡ Run";
              btn.style.background = "rgba(56, 189, 248, 0.15)";
              btn.style.color = "#38bdf8";
            }, 2500);
          }
        };
      });

    } catch (err) {
      botsListContainer.innerHTML = `<div style="color: #94a3b8; font-size: 10px; padding: 4px;">Could not connect to bot catalog.</div>`;
    }
  }

  // Toggle Bots accordion
  if (btnToggleBots) {
    btnToggleBots.onclick = () => {
      const isVisible = botsListContainer.style.display === "block";
      botsListContainer.style.display = isVisible ? "none" : "block";
      botsChevron.innerText = isVisible ? "▼" : "▲";
    };
  }

  btnStart.onclick = () => {
    chrome.runtime.sendMessage({ type: "START_RECORDING" }, (res) => {
      if (res && res.success) {
        showRecordingState(0);
        window.close();
      }
    });
  };

  btnStop.onclick = () => {
    chrome.runtime.sendMessage({ type: "STOP_RECORDING" }, (res) => {
      showIdleState();
      window.close();
    });
  };

  btnPortal.onclick = () => {
    chrome.tabs.create({ url: `${activeBackendUrl}/builder` });
    window.close();
  };

  btnDemo.onclick = () => {
    chrome.tabs.create({ url: `${activeBackendUrl}/demo-target` });
    window.close();
  };

  // Settings Drawer handlers
  btnToggleSettings.onclick = () => {
    settingsDrawer.style.display = settingsDrawer.style.display === "block" ? "none" : "block";
  };

  btnCloseDrawer.onclick = () => {
    settingsDrawer.style.display = "none";
  };

  btnSaveServer.onclick = () => {
    let newUrl = (inputServerUrl.value || "").trim().replace(/\/+$/, "");
    if (!newUrl) newUrl = DEFAULT_SERVER_URL;
    if (!newUrl.startsWith("http://") && !newUrl.startsWith("https://")) {
      newUrl = "https://" + newUrl;
    }
    inputServerUrl.value = newUrl;
    activeBackendUrl = newUrl;
    serverDisplay.innerText = newUrl.replace(/^https?:\/\//, "");
    serverDisplay.title = newUrl;

    storeBackendUrl(newUrl, () => {
      drawerMsg.innerText = "✓ Saved!";
      drawerMsg.style.color = "#34d399";
      drawerMsg.style.display = "block";
      checkServerHealth(newUrl);
      loadSavedBots(newUrl);
      setTimeout(() => { drawerMsg.style.display = "none"; }, 2000);
    });
  };

  btnTestServer.onclick = async () => {
    let url = (inputServerUrl.value || "").trim().replace(/\/+$/, "");
    if (!url) url = DEFAULT_SERVER_URL;
    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      url = "https://" + url;
    }
    drawerMsg.innerText = "Pinging...";
    drawerMsg.style.color = "#38bdf8";
    drawerMsg.style.display = "block";

    const start = Date.now();
    try {
      const res = await fetch(`${url}/api/health`);
      const latency = Date.now() - start;
      if (res.ok) {
        drawerMsg.innerText = `✓ Connected (${latency}ms)`;
        drawerMsg.style.color = "#34d399";
      } else {
        drawerMsg.innerText = `⚠ Error: HTTP ${res.status}`;
        drawerMsg.style.color = "#f87171";
      }
    } catch (e) {
      drawerMsg.innerText = "✕ Unreachable";
      drawerMsg.style.color = "#f87171";
    }
  };

  btnOpenOptions.onclick = () => {
    if (chrome.runtime.openOptionsPage) {
      chrome.runtime.openOptionsPage();
    } else {
      window.open(chrome.runtime.getURL("options/options.html"));
    }
  };
});

function getStoredBackendUrl(callback) {
  const storage = chrome.storage.sync || chrome.storage.local;
  storage.get(["serverUrl"], (data) => {
    if (!data || !data.serverUrl || data.serverUrl === "http://127.0.0.1:5000" || data.serverUrl === "http://localhost:5000") {
      callback(DEFAULT_SERVER_URL);
    } else {
      callback(data.serverUrl);
    }
  });
}

function storeBackendUrl(url, callback) {
  const storage = chrome.storage.sync || chrome.storage.local;
  storage.set({ serverUrl: url }, () => {
    if (chrome.storage.local && storage !== chrome.storage.local) {
      chrome.storage.local.set({ serverUrl: url });
    }
    if (callback) callback();
  });
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
