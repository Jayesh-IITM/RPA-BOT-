/**
 * GovBridge RPA Recorder - Content Script
 * Intelligently records meaningful interactions (clicks, inputs, selects),
 * generates resilient multi-selectors, and provides an in-page floating control bar.
 */

let isRecording = false;
let recordedStepCount = 0;
let floatingBar = null;
let recordingStartTime = null;
let timerInterval = null;

// Notify web application that MahaSetu Extension is installed and active
try {
  window.postMessage({ type: "MAHASETU_EXTENSION_READY", version: "1.0.0" }, "*");
  document.dispatchEvent(new CustomEvent("MahaSetuExtensionReady", { detail: { version: "1.0.0" } }));
  window.addEventListener("message", (event) => {
    if (event.data && event.data.type === "MAHASETU_PING_EXTENSION") {
      window.postMessage({ type: "MAHASETU_EXTENSION_PONG", version: "1.0.0" }, "*");
    }
  });
} catch (e) {
  // Ignore in restricted frames
}

// Initialize on page load
chrome.storage.local.get(["isRecording", "recordedActions"], (data) => {
  if (data.isRecording) {
    startRecordingSession(data.recordedActions ? data.recordedActions.length : 0);
  }
});

// Listen for background events
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "RECORDING_STARTED") {
    startRecordingSession(0);
    sendResponse({ success: true });
  } else if (msg.type === "RECORDING_STOPPED") {
    stopRecordingSession();
    sendResponse({ success: true });
  }
});

// --------------------------------------------------------------------------
// Floating In-Page Control Bar (Bottom-Left & Movable)
// --------------------------------------------------------------------------
function injectFloatingBar() {
  if (document.getElementById("govbridge-recorder-bar")) return;

  floatingBar = document.createElement("div");
  floatingBar.id = "govbridge-recorder-bar";
  floatingBar.style.position = "fixed";
  floatingBar.style.zIndex = "2147483647";
  floatingBar.style.background = "#0f172a";
  floatingBar.style.border = "2px dashed #10b981";
  floatingBar.style.borderRadius = "10px";
  floatingBar.style.padding = "8px 12px";
  floatingBar.style.boxShadow = "0 8px 30px rgba(0,0,0,0.65), 0 0 15px rgba(16, 185, 129, 0.15)";
  floatingBar.style.display = "flex";
  floatingBar.style.alignItems = "center";
  floatingBar.style.gap = "9px";
  floatingBar.style.fontFamily = "Inter, -apple-system, sans-serif";
  floatingBar.style.fontSize = "12px";
  floatingBar.style.color = "#ffffff";
  floatingBar.style.userSelect = "none";
  floatingBar.style.cursor = "grab";
  floatingBar.style.transition = "box-shadow 0.2s ease, transform 0.1s ease";

  // Check if a saved position exists from previous page / drag
  const savedPos = getSavedBarPosition();
  if (savedPos) {
    floatingBar.style.left = `${savedPos.left}px`;
    floatingBar.style.top = `${savedPos.top}px`;
    floatingBar.style.bottom = "auto";
    floatingBar.style.right = "auto";
  } else {
    // Default initial location: BOTTOM-LEFT CORNER
    floatingBar.style.bottom = "24px";
    floatingBar.style.left = "24px";
    floatingBar.style.top = "auto";
    floatingBar.style.right = "auto";
  }

  floatingBar.innerHTML = `
    <!-- Drag Handle -->
    <div id="gov-drag-handle" title="Click and drag to move toolbar anywhere on screen" style="display: flex; align-items: center; justify-content: center; cursor: grab; padding: 2px 3px; color: #64748b; font-size: 13px; line-height: 1;">
      <svg width="10" height="16" viewBox="0 0 10 16" fill="currentColor" style="pointer-events: none;">
        <circle cx="2" cy="2" r="1.5" />
        <circle cx="8" cy="2" r="1.5" />
        <circle cx="2" cy="8" r="1.5" />
        <circle cx="8" cy="8" r="1.5" />
        <circle cx="2" cy="14" r="1.5" />
        <circle cx="8" cy="14" r="1.5" />
      </svg>
    </div>

    <!-- REC Indicator & Timer -->
    <div style="display: flex; align-items: center; gap: 6px; cursor: grab;">
      <span id="gov-rec-dot" style="width: 10px; height: 10px; border-radius: 50%; background: #ef4444; animation: govRecBlink 1s infinite;"></span>
      <strong style="color: #34d399; letter-spacing: 0.5px;">REC</strong>
      <span id="gov-rec-timer" style="color: #94a3b8; font-family: monospace; font-size: 11px;">00:00</span>
    </div>

    <div style="height: 16px; width: 1px; background: #334155;"></div>

    <!-- Step Counter Badge -->
    <span id="gov-step-counter" style="background: rgba(14, 165, 233, 0.2); color: #38bdf8; padding: 2px 7px; border-radius: 4px; font-weight: 600; font-size: 11px; cursor: grab;">
      0 steps
    </span>

    <!-- Quick Add Wait Step -->
    <button id="gov-btn-add-wait" title="Insert 1 second wait delay into recorded flow" style="background: rgba(255,255,255,0.08); border: 1px solid #334155; color: #cbd5e1; border-radius: 5px; padding: 5px 9px; cursor: pointer; font-size: 11px; font-weight: 500; transition: all 0.15s; white-space: nowrap;">
      + Wait 1s
    </button>

    <!-- Stop Recording Option (Bottom-Left default, fully movable) -->
    <button id="gov-btn-stop" title="Stop recording and send traced path to GovBridge visual builder" style="background: #10b981; border: none; color: #06150f; border-radius: 5px; padding: 6px 13px; cursor: pointer; font-weight: 700; font-size: 11px; display: flex; align-items: center; gap: 5px; white-space: nowrap; transition: background 0.15s ease;">
      <span style="font-size: 10px;">⏹</span> Stop & Send to GovBridge
    </button>
  `;

  // Add blink CSS animation & interactive hover styles
  if (!document.getElementById("govbridge-recorder-style")) {
    const styleEl = document.createElement("style");
    styleEl.id = "govbridge-recorder-style";
    styleEl.innerHTML = `
      @keyframes govRecBlink {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.3; transform: scale(0.85); }
      }
      #govbridge-recorder-bar:active {
        cursor: grabbing !important;
      }
      #gov-btn-add-wait:hover {
        background: rgba(255,255,255,0.15) !important;
        border-color: #64748b !important;
        color: #ffffff !important;
      }
      #gov-btn-stop:hover {
        filter: brightness(1.1);
        box-shadow: 0 3px 12px rgba(16, 185, 129, 0.6) !important;
      }
      #gov-drag-handle:hover {
        color: #34d399 !important;
      }
    `;
    document.head.appendChild(styleEl);
  }

  document.body.appendChild(floatingBar);

  // Enable movable dragging
  makeBarDraggable(floatingBar);

  // Button handlers
  document.getElementById("gov-btn-add-wait").onclick = (e) => {
    e.stopPropagation();
    recordWaitAction(1000);
  };

  document.getElementById("gov-btn-stop").onclick = (e) => {
    e.stopPropagation();
    stopRecordingSession();
  };
}

/**
 * Enables smooth drag-and-move for the floating recorder bar
 */
function makeBarDraggable(element) {
  let isDragging = false;
  let startX = 0;
  let startY = 0;
  let initLeft = 0;
  let initTop = 0;

  element.addEventListener("mousedown", onMouseDown);

  function onMouseDown(e) {
    // Do not drag if clicking interactive buttons
    if (e.target.closest("button, input, select, textarea, a")) {
      return;
    }

    isDragging = true;
    startX = e.clientX;
    startY = e.clientY;

    const rect = element.getBoundingClientRect();
    initLeft = rect.left;
    initTop = rect.top;

    // Convert from bottom/right relative styling to absolute viewport top/left
    element.style.bottom = "auto";
    element.style.right = "auto";
    element.style.left = `${initLeft}px`;
    element.style.top = `${initTop}px`;
    element.style.cursor = "grabbing";
    element.style.boxShadow = "0 12px 40px rgba(0,0,0,0.85), 0 0 20px rgba(16, 185, 129, 0.35)";

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    e.preventDefault();
  }

  function onMouseMove(e) {
    if (!isDragging) return;

    const dx = e.clientX - startX;
    const dy = e.clientY - startY;

    const rect = element.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;

    let newLeft = initLeft + dx;
    let newTop = initTop + dy;

    // Viewport boundaries clamp (minimum 8px from any edge)
    const minX = 8;
    const minY = 8;
    const maxX = Math.max(minX, window.innerWidth - width - 8);
    const maxY = Math.max(minY, window.innerHeight - height - 8);

    newLeft = Math.max(minX, Math.min(newLeft, maxX));
    newTop = Math.max(minY, Math.min(newTop, maxY));

    element.style.left = `${newLeft}px`;
    element.style.top = `${newTop}px`;
  }

  function onMouseUp() {
    if (!isDragging) return;
    isDragging = false;
    element.style.cursor = "grab";
    element.style.boxShadow = "0 8px 30px rgba(0,0,0,0.65), 0 0 15px rgba(16, 185, 129, 0.15)";

    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);

    // Save final position in sessionStorage so it persists across navigations
    const rect = element.getBoundingClientRect();
    try {
      sessionStorage.setItem("govbridge_bar_pos", JSON.stringify({
        left: rect.left,
        top: rect.top
      }));
    } catch (err) {}
  }

  // Handle window resizing so toolbar stays visible on screen
  window.addEventListener("resize", () => {
    if (!element || !element.parentElement) return;
    const rect = element.getBoundingClientRect();
    let left = rect.left;
    let top = rect.top;

    const maxX = Math.max(8, window.innerWidth - rect.width - 8);
    const maxY = Math.max(8, window.innerHeight - rect.height - 8);

    let adjusted = false;
    if (left > maxX) { left = maxX; adjusted = true; }
    if (top > maxY) { top = maxY; adjusted = true; }

    if (adjusted) {
      element.style.left = `${left}px`;
      element.style.top = `${top}px`;
      element.style.bottom = "auto";
      element.style.right = "auto";
    }
  });
}

function getSavedBarPosition() {
  try {
    const raw = sessionStorage.getItem("govbridge_bar_pos");
    if (!raw) return null;
    const pos = JSON.parse(raw);
    if (typeof pos.left === "number" && typeof pos.top === "number") {
      if (pos.left < window.innerWidth - 60 && pos.top < window.innerHeight - 40) {
        return pos;
      }
    }
  } catch (e) {}
  return null;
}

function removeFloatingBar() {
  const bar = document.getElementById("govbridge-recorder-bar");
  if (bar) bar.remove();
  if (timerInterval) clearInterval(timerInterval);
}

function updateBarCount(count) {
  const badge = document.getElementById("gov-step-counter");
  if (badge) badge.innerText = `${count} steps`;
}

function startRecordingSession(initialCount = 0) {
  isRecording = true;
  recordedStepCount = initialCount;
  recordingStartTime = Date.now();
  injectFloatingBar();
  updateBarCount(recordedStepCount);

  timerInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
    const mins = String(Math.floor(elapsed / 60)).padStart(2, "0");
    const secs = String(elapsed % 60).padStart(2, "0");
    const timerElem = document.getElementById("gov-rec-timer");
    if (timerElem) timerElem.innerText = `${mins}:${secs}`;
  }, 1000);

  attachListeners();
}

function stopRecordingSession() {
  isRecording = false;
  removeFloatingBar();
  detachListeners();
  chrome.runtime.sendMessage({
    type: "STOP_RECORDING",
    url: window.location.href
  });
}

// --------------------------------------------------------------------------
// --------------------------------------------------------------------------
// Smart Resilient Selector Generator (Rejects Volatile IDs & Framework Hashes)
// --------------------------------------------------------------------------

/**
 * Detects whether an ID is dynamically generated by frameworks (React 18 useId, Radix,
 * Headless UI, Material UI, hex hashes, timestamps) and should NOT be used as a primary selector.
 */
function isVolatileId(id) {
  if (!id || typeof id !== "string") return true;
  id = id.trim();
  if (id.length < 2 || id.length > 80 || /\s/.test(id)) return true;

  // React 18 useId() / Radix UI: :r0:, :r1:, radix-:r2:, radix-:r3:
  if (/^radix-/i.test(id) || /:r[0-9a-zA-Z_-]+:/i.test(id) || /^:r\d+/i.test(id)) return true;

  // Common modern framework dynamic prefixes
  if (/^(headlessui|floating-ui|chakra|mui|react-select|downshift|ember|ng-)/i.test(id)) return true;

  // Hexadecimal or random hash sequence >= 10 chars (e.g. 68fa2613fee728b2260037c5 or d41d8cd98f)
  if (/^[0-9a-fA-F]{10,}$/.test(id)) return true;

  // Auto-generated timestamp or random integer suffixes e.g. input_1788806804 or item-9481283
  if (/[_-]\d{6,}$/.test(id) || /^\d+$/.test(id)) return true;

  // UUID patterns
  if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)) return true;

  return false;
}

function cleanText(text, maxLen = 40) {
  if (!text || typeof text !== "string") return "";
  // Split on newlines (to strip hotkey text like '\nCtrl+Shift+E')
  const firstLine = text.split(/[\r\n]+/)[0].trim();
  return firstLine.slice(0, maxLen);
}

function generateResilientSelectors(el) {
  const selectors = {
    primary: "",
    fallbacks: [],
    target_name: ""
  };

  if (!el || !(el instanceof Element)) return selectors;

  const tag = el.tagName.toLowerCase();
  const rawText = el.innerText || el.textContent || "";
  const cleanedText = cleanText(rawText);

  // 1. Stable Testing Attributes (Highest Industry Priority - Never change across deploys)
  const testId = el.getAttribute("data-testid") || 
                 el.getAttribute("data-test-id") || 
                 el.getAttribute("data-cy") || 
                 el.getAttribute("data-qa") ||
                 el.getAttribute("data-component");
  if (testId) {
    const testSel = `[data-testid="${testId}"]`;
    selectors.primary = testSel;
    selectors.target_name = testId;
  }

  // 2. Stable Non-Volatile ID
  if (el.id && !isVolatileId(el.id)) {
    const idSel = `#${CSS.escape(el.id)}`;
    if (!selectors.primary) selectors.primary = idSel;
    else selectors.fallbacks.push(idSel);
  }

  // 3. Accessible Label / Aria Name
  const ariaLabel = el.getAttribute("aria-label");
  if (ariaLabel && ariaLabel.trim().length > 1) {
    const ariaSel = `${tag}[aria-label="${ariaLabel.trim()}"]`;
    if (!selectors.primary) selectors.primary = ariaSel;
    else selectors.fallbacks.push(ariaSel);
    if (!selectors.target_name) selectors.target_name = ariaLabel.trim();
  }

  // 4. Stable Text Locators for Interactive Elements (Buttons, Links, Tabs)
  if (["button", "a", "span", "div"].includes(tag) || el.getAttribute("role") === "button") {
    if (cleanedText && cleanedText.length >= 2 && cleanedText.length <= 35) {
      const textSel = `${tag}:has-text("${cleanedText.replace(/"/g, '\\"')}")`;
      if (!selectors.primary && (tag === "button" || el.getAttribute("role") === "button")) {
        selectors.primary = textSel;
      } else {
        selectors.fallbacks.push(textSel);
      }
      if (!selectors.target_name) selectors.target_name = cleanedText;
    }
  }

  // 5. Name attribute (for forms/inputs)
  const nameAttr = el.getAttribute("name");
  if (nameAttr) {
    const nameSel = `${tag}[name="${nameAttr}"]`;
    if (!selectors.primary) selectors.primary = nameSel;
    else selectors.fallbacks.push(nameSel);
    if (!selectors.target_name) selectors.target_name = nameAttr;
  }

  // 6. Placeholder / Title attributes
  const placeholder = el.getAttribute("placeholder");
  if (placeholder) {
    const plSel = `${tag}[placeholder="${placeholder}"]`;
    selectors.fallbacks.push(plSel);
    if (!selectors.target_name) selectors.target_name = placeholder;
  }

  const titleAttr = el.getAttribute("title");
  if (titleAttr) {
    selectors.fallbacks.push(`${tag}[title="${titleAttr}"]`);
    if (!selectors.target_name) selectors.target_name = titleAttr;
  }

  // 7. Clean Hierarchical CSS (excluding volatile IDs)
  const cssPath = getResilientCssPath(el);
  if (cssPath) {
    if (!selectors.primary) selectors.primary = cssPath;
    else if (!selectors.fallbacks.includes(cssPath)) selectors.fallbacks.push(cssPath);
  }

  // 8. Resilient XPath
  const xpath = getResilientXPath(el, cleanedText);
  if (xpath && !selectors.fallbacks.includes(xpath)) {
    selectors.fallbacks.push(xpath);
  }

  // Default target name
  if (!selectors.target_name) {
    selectors.target_name = cleanedText || tag;
  }

  return selectors;
}

function getResilientCssPath(el) {
  if (!(el instanceof Element)) return '';
  const path = [];
  let curr = el;

  while (curr && curr.nodeType === Node.ELEMENT_NODE && curr !== document.documentElement) {
    let selector = curr.nodeName.toLowerCase();
    
    // Use testid if available on ancestor
    const tid = curr.getAttribute("data-testid");
    if (tid) {
      selector = `[data-testid="${tid}"]`;
      path.unshift(selector);
      break;
    }

    // Only include ID if it is truly non-volatile
    if (curr.id && !isVolatileId(curr.id)) {
      selector += '#' + CSS.escape(curr.id);
      path.unshift(selector);
      break;
    } else {
      let sib = curr, nth = 1;
      while (sib = sib.previousElementSibling) {
        if (sib.nodeName.toLowerCase() === selector) nth++;
      }
      if (nth !== 1) selector += `:nth-of-type(${nth})`;
    }
    path.unshift(selector);
    curr = curr.parentNode;
    if (path.length >= 4) break; // Keep hierarchy compact and resilient
  }
  return path.join(' > ');
}

function getResilientXPath(el, text) {
  const tag = el.tagName.toLowerCase();
  if (text && (tag === "button" || tag === "a" || el.getAttribute("role") === "button")) {
    return `//${tag}[contains(normalize-space(), "${text.replace(/"/g, '')}")]`;
  }
  if (el.id && !isVolatileId(el.id)) {
    return `//*[@id="${el.id}"]`;
  }
  if (tag === "canvas") {
    return "//canvas";
  }
  return null;
}

// --------------------------------------------------------------------------
// Smart Canvas Gestures & Pointer Interaction Tracker
// --------------------------------------------------------------------------
let canvasPointerState = null;
let suppressNextCanvasClick = false;
let suppressClickTimer = null;

function handlePointerDown(e) {
  if (!isRecording) return;
  if (e.target.closest("#govbridge-recorder-bar")) return;

  const canvas = e.target.closest("canvas") || (e.target.tagName === "CANVAS" ? e.target : null);
  if (!canvas) {
    canvasPointerState = null;
    return;
  }

  const rect = canvas.getBoundingClientRect();
  canvasPointerState = {
    canvas: canvas,
    startX: e.clientX,
    startY: e.clientY,
    startOffsetX: e.clientX - rect.left,
    startOffsetY: e.clientY - rect.top,
    rectWidth: rect.width || 1,
    rectHeight: rect.height || 1,
    startTime: Date.now()
  };
}

function handlePointerUp(e) {
  if (!isRecording || !canvasPointerState) return;
  if (e.target.closest("#govbridge-recorder-bar")) {
    canvasPointerState = null;
    return;
  }

  const state = canvasPointerState;
  canvasPointerState = null;

  const rect = state.canvas.getBoundingClientRect();
  const currentOffsetX = e.clientX - rect.left;
  const currentOffsetY = e.clientY - rect.top;

  const dx = currentOffsetX - state.startOffsetX;
  const dy = currentOffsetY - state.startOffsetY;
  const distance = Math.hypot(dx, dy);

  const startPercentX = Math.min(Math.max(state.startOffsetX / state.rectWidth, 0), 1);
  const startPercentY = Math.min(Math.max(state.startOffsetY / state.rectHeight, 0), 1);
  const endPercentX = Math.min(Math.max(currentOffsetX / state.rectWidth, 0), 1);
  const endPercentY = Math.min(Math.max(currentOffsetY / state.rectHeight, 0), 1);

  const selData = generateResilientSelectors(state.canvas);

  // If drag distance >= 12px, record as a CANVAS DRAW (Rectangle / Gesture stroke)
  if (distance >= 12) {
    const p1X = Math.round(startPercentX * 100);
    const p1Y = Math.round(startPercentY * 100);
    const p2X = Math.round(endPercentX * 100);
    const p2Y = Math.round(endPercentY * 100);

    recordedStepCount++;
    updateBarCount(recordedStepCount);

    chrome.runtime.sendMessage({
      type: "SAVE_ACTION",
      action: {
        type: "canvas_draw",
        action_type: "canvas_draw",
        selector: selData.primary || "canvas",
        fallbacks: selData.fallbacks,
        target_name: `Draw on Canvas (${p1X}%, ${p1Y}% → ${p2X}%, ${p2Y}%)`,
        shape_hint: "rectangle",
        start_x: Math.round(state.startOffsetX),
        start_y: Math.round(state.startOffsetY),
        end_x: Math.round(currentOffsetX),
        end_y: Math.round(currentOffsetY),
        start_percent_x: Number(startPercentX.toFixed(4)),
        start_percent_y: Number(startPercentY.toFixed(4)),
        end_percent_x: Number(endPercentX.toFixed(4)),
        end_percent_y: Number(endPercentY.toFixed(4)),
        text: `Draw rectangle from (${p1X}%, ${p1Y}%) to (${p2X}%, ${p2Y}%)`
      }
    });

    // Suppress the subsequent click event that browsers emit upon pointerup
    suppressNextCanvasClick = true;
    clearTimeout(suppressClickTimer);
    suppressClickTimer = setTimeout(() => {
      suppressNextCanvasClick = false;
    }, 400);

  } else {
    // Precision Click on Canvas Point
    const pX = Math.round(startPercentX * 100);
    const pY = Math.round(startPercentY * 100);

    recordedStepCount++;
    updateBarCount(recordedStepCount);

    chrome.runtime.sendMessage({
      type: "SAVE_ACTION",
      action: {
        type: "canvas_click",
        action_type: "canvas_click",
        selector: selData.primary || "canvas",
        fallbacks: selData.fallbacks,
        target_name: `Canvas Point (${pX}%, ${pY}%)`,
        offset_x: Math.round(state.startOffsetX),
        offset_y: Math.round(state.startOffsetY),
        percent_x: Number(startPercentX.toFixed(4)),
        percent_y: Number(startPercentY.toFixed(4)),
        text: `Click canvas point at (${pX}%, ${pY}%)`
      }
    });

    suppressNextCanvasClick = true;
    clearTimeout(suppressClickTimer);
    suppressClickTimer = setTimeout(() => {
      suppressNextCanvasClick = false;
    }, 400);
  }
}

// --------------------------------------------------------------------------
// Event Listeners & Meaningful Action Filtering
// --------------------------------------------------------------------------
function recordWaitAction(ms) {
  recordedStepCount++;
  updateBarCount(recordedStepCount);
  chrome.runtime.sendMessage({
    type: "SAVE_ACTION",
    action: {
      type: "wait",
      duration: ms
    }
  });
}

function handleClick(e) {
  if (!isRecording) return;
  // Ignore clicks on recorder bar
  if (e.target.closest("#govbridge-recorder-bar")) return;

  // Suppress canvas clicks already captured by precision pointer tracker
  if (suppressNextCanvasClick || e.target.tagName === "CANVAS" || e.target.closest("canvas")) {
    return;
  }

  const target = e.target.closest("button, a, input[type='submit'], input[type='button'], [role='button'], select") || e.target;
  const selData = generateResilientSelectors(target);

  // Filter out text inputs (we record them on change/blur instead)
  if (target.tagName === "INPUT" && ["text", "password", "email", "number", "search"].includes(target.type)) {
    return;
  }

  recordedStepCount++;
  updateBarCount(recordedStepCount);

  const buttonText = cleanText(target.innerText || target.textContent || "");

  chrome.runtime.sendMessage({
    type: "SAVE_ACTION",
    action: {
      type: "click",
      selector: selData.primary,
      fallbacks: selData.fallbacks,
      target_name: selData.target_name,
      text: buttonText
    }
  });
}

function handleChange(e) {
  if (!isRecording) return;
  if (e.target.closest("#govbridge-recorder-bar")) return;

  const target = e.target;
  const selData = generateResilientSelectors(target);

  if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") {
    recordedStepCount++;
    updateBarCount(recordedStepCount);

    chrome.runtime.sendMessage({
      type: "SAVE_ACTION",
      action: {
        type: "input",
        selector: selData.primary,
        fallbacks: selData.fallbacks,
        target_name: selData.target_name,
        input_type: target.type || "text",
        value: target.value
      }
    });
  } else if (target.tagName === "SELECT") {
    recordedStepCount++;
    updateBarCount(recordedStepCount);

    chrome.runtime.sendMessage({
      type: "SAVE_ACTION",
      action: {
        type: "select",
        selector: selData.primary,
        fallbacks: selData.fallbacks,
        target_name: selData.target_name,
        value: target.value,
        text: target.options[target.selectedIndex]?.text || ""
      }
    });
  }
}

function attachListeners() {
  document.addEventListener("pointerdown", handlePointerDown, true);
  document.addEventListener("pointerup", handlePointerUp, true);
  document.addEventListener("mousedown", handlePointerDown, true);
  document.addEventListener("mouseup", handlePointerUp, true);
  document.addEventListener("click", handleClick, true);
  document.addEventListener("change", handleChange, true);
}

function detachListeners() {
  document.removeEventListener("pointerdown", handlePointerDown, true);
  document.removeEventListener("pointerup", handlePointerUp, true);
  document.removeEventListener("mousedown", handlePointerDown, true);
  document.removeEventListener("mouseup", handlePointerUp, true);
  document.removeEventListener("click", handleClick, true);
  document.removeEventListener("change", handleChange, true);
}

