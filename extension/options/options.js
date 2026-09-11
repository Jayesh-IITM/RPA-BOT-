/**
 * MahaSetu RPA Recorder - Options / Settings Script
 */

const DEFAULT_SERVER = "http://127.0.0.1:5000";

document.addEventListener("DOMContentLoaded", () => {
  const serverInput = document.getElementById("server-url");
  const btnSave = document.getElementById("btn-save");
  const btnTest = document.getElementById("btn-test");
  const btnReset = document.getElementById("btn-reset");
  const statusBox = document.getElementById("status-box");

  const btnOpenBuilder = document.getElementById("btn-open-builder");
  const btnOpenGuide = document.getElementById("btn-open-guide");
  const btnOpenDemo = document.getElementById("btn-open-demo");

  // Load current saved setting
  getBackendUrl((url) => {
    serverInput.value = url;
  });

  btnSave.onclick = () => {
    let url = (serverInput.value || "").trim().replace(/\/+$/, "");
    if (!url) {
      url = DEFAULT_SERVER;
      serverInput.value = url;
    }
    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      url = "http://" + url;
      serverInput.value = url;
    }

    setBackendUrl(url, () => {
      showStatus(`✓ Settings saved! Active server: ${url}`, "success");
    });
  };

  btnReset.onclick = () => {
    serverInput.value = DEFAULT_SERVER;
    setBackendUrl(DEFAULT_SERVER, () => {
      showStatus(`✓ Reset to default server: ${DEFAULT_SERVER}`, "info");
    });
  };

  btnTest.onclick = async () => {
    let url = (serverInput.value || "").trim().replace(/\/+$/, "");
    if (!url) url = DEFAULT_SERVER;
    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      url = "http://" + url;
    }

    showStatus("Connecting to server...", "info");
    const startTime = Date.now();

    try {
      // Test /api/health endpoint
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 6000);

      const resp = await fetch(`${url}/api/health`, {
        method: "GET",
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      const latency = Date.now() - startTime;
      if (resp.ok) {
        const data = await resp.json();
        const ver = data.version || "1.0.0";
        const pw = data.playwright_ready ? "Playwright Ready" : "Playwright Initializing";
        showStatus(`✓ Connected successfully! Status: ${data.status.toUpperCase()} (${latency}ms) | v${ver} | ${pw}`, "success");
      } else {
        showStatus(`⚠ Server reachable but responded with HTTP ${resp.status}`, "error");
      }
    } catch (err) {
      // Fallback try /api/bots
      try {
        const resp2 = await fetch(`${url}/api/bots`);
        if (resp2.ok) {
          const latency = Date.now() - startTime;
          showStatus(`✓ Connected to MahaSetu API (${latency}ms)`, "success");
          return;
        }
      } catch (err2) {
        // failed
      }
      showStatus(`✕ Could not reach server at ${url}. Please verify host, port, and CORS settings.`, "error");
    }
  };

  btnOpenBuilder.onclick = () => {
    getBackendUrl((url) => {
      chrome.tabs.create({ url: `${url}/builder` });
    });
  };

  btnOpenGuide.onclick = () => {
    getBackendUrl((url) => {
      chrome.tabs.create({ url: `${url}/extension-guide` });
    });
  };

  btnOpenDemo.onclick = () => {
    getBackendUrl((url) => {
      chrome.tabs.create({ url: `${url}/demo-target` });
    });
  };

  function showStatus(msg, type) {
    statusBox.innerText = msg;
    statusBox.className = `status-box status-${type}`;
    statusBox.style.display = "block";
  }
});

function getBackendUrl(callback) {
  const storage = chrome.storage.sync || chrome.storage.local;
  storage.get(["serverUrl"], (res) => {
    callback(res && res.serverUrl ? res.serverUrl : DEFAULT_SERVER);
  });
}

function setBackendUrl(url, callback) {
  const storage = chrome.storage.sync || chrome.storage.local;
  storage.set({ serverUrl: url }, () => {
    if (chrome.storage.local && storage !== chrome.storage.local) {
      chrome.storage.local.set({ serverUrl: url });
    }
    if (callback) callback();
  });
}
