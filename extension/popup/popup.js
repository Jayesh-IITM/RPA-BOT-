/**
 * MahaSetu RPA Recorder - Popup Script
 */

const DEFAULT_SERVER_URL = "http://127.0.0.1:5000";
let activeBackendUrl = DEFAULT_SERVER_URL;

document.addEventListener("DOMContentLoaded", () => {
  const statusBadge = document.getElementById("popup-status");
  const idleControls = document.getElementById("idle-controls");
  const activeControls = document.getElementById("active-controls");
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

  // Load configured backend URL
  getStoredBackendUrl((url) => {
    activeBackendUrl = url;
    serverDisplay.innerText = url.replace(/^https?:\/\//, "");
    serverDisplay.title = url;
    inputServerUrl.value = url;
    checkServerHealth(url);
  });

  // Check current recording state
  chrome.runtime.sendMessage({ type: "GET_RECORDING_STATE" }, (data) => {
    if (data && data.isRecording) {
      showRecordingState();
    } else {
      showIdleState();
    }
  });

  function showRecordingState() {
    statusBadge.innerText = "RECORDING";
    statusBadge.className = "status-badge status-recording";
    idleControls.style.display = "none";
    activeControls.style.display = "block";
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
      const tid = setTimeout(() => controller.abort(), 4000);
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

  btnStart.onclick = () => {
    chrome.runtime.sendMessage({ type: "START_RECORDING" }, (res) => {
      if (res && res.success) {
        showRecordingState();
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
      newUrl = "http://" + newUrl;
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
      setTimeout(() => { drawerMsg.style.display = "none"; }, 2000);
    });
  };

  btnTestServer.onclick = async () => {
    let url = (inputServerUrl.value || "").trim().replace(/\/+$/, "");
    if (!url) url = DEFAULT_SERVER_URL;
    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      url = "http://" + url;
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
    callback(data && data.serverUrl ? data.serverUrl : DEFAULT_SERVER_URL);
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
