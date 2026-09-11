/**
 * MahaSetu RPA Recorder - Background Service Worker (Manifest V3)
 */

const DEFAULT_BACKEND = "https://rpa-bot-production.up.railway.app";

function getBackendUrl() {
  return new Promise((resolve) => {
    const storage = chrome.storage.sync || chrome.storage.local;
    storage.get(["serverUrl"], (data) => {
      // Migrate old default or missing URL to production Railway instance
      if (!data || !data.serverUrl || data.serverUrl === "http://127.0.0.1:5000" || data.serverUrl === "http://localhost:5000") {
        resolve(DEFAULT_BACKEND);
      } else {
        resolve(data.serverUrl);
      }
    });
  });
}

chrome.runtime.onInstalled.addListener(() => {
  console.log("MahaSetu RPA Recorder Extension Installed/Updated");
  chrome.storage.local.set({ isRecording: false, recordedActions: [] });
  const storage = chrome.storage.sync || chrome.storage.local;
  storage.get(["serverUrl"], (data) => {
    if (!data || !data.serverUrl || data.serverUrl === "http://127.0.0.1:5000" || data.serverUrl === "http://localhost:5000") {
      storage.set({ serverUrl: DEFAULT_BACKEND });
    }
  });
});

// Handle messages from content script or popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "GET_RECORDING_STATE") {
    chrome.storage.local.get(["isRecording", "recordedActions"], (data) => {
      sendResponse(data);
    });
    return true;
  }

  if (message.type === "GET_BACKEND_URL") {
    getBackendUrl().then((url) => sendResponse({ backendUrl: url }));
    return true;
  }

  if (message.type === "START_RECORDING") {
    chrome.storage.local.set({ isRecording: true, recordedActions: [] }, () => {
      // Notify active tab
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs[0] && tabs[0].id) {
          chrome.tabs.sendMessage(tabs[0].id, { type: "RECORDING_STARTED" });
        }
      });
      sendResponse({ success: true });
    });
    return true;
  }

  if (message.type === "STOP_RECORDING") {
    chrome.storage.local.get(["recordedActions"], async (data) => {
      chrome.storage.local.set({ isRecording: false });

      const backendUrl = await getBackendUrl();
      const actions = data.recordedActions || [];
      const currentUrl = sender.tab ? sender.tab.url : (message.url || `${backendUrl}/demo-target`);

      try {
        // Send recorded trace to MahaSetu backend
        const response = await fetch(`${backendUrl}/api/recordings`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            initial_url: currentUrl,
            actions: actions,
            name: `Recorded Path - ${new Date().toLocaleTimeString()}`
          })
        });

        const resData = await response.json();
        const targetUrl = resData.redirect_url 
          ? `${backendUrl}${resData.redirect_url}` 
          : `${backendUrl}/builder`;

        // Redirect user to MahaSetu Web Portal showing the full workflow!
        chrome.tabs.create({ url: targetUrl });
        sendResponse({ success: true, redirect_url: targetUrl });
      } catch (err) {
        console.warn("Could not reach MahaSetu server, opening builder directly:", err);
        const fallbackUrl = `${backendUrl}/builder`;
        chrome.tabs.create({ url: fallbackUrl });
        sendResponse({ success: false, error: err.message, fallback_url: fallbackUrl });
      }
    });
    return true;
  }

  if (message.type === "SAVE_ACTION") {
    chrome.storage.local.get(["recordedActions"], (data) => {
      const actions = data.recordedActions || [];
      actions.push(message.action);
      chrome.storage.local.set({ recordedActions: actions });
      sendResponse({ success: true, count: actions.length });
    });
    return true;
  }
});
