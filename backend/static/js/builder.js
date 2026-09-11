/**
 * GovBridge RPA Builder - Interactive Workflow Canvas & Execution Controller
 */

let currentBot = window.INITIAL_BOT_DATA || {
  id: "govbridge_login_bot_01",
  name: "GovBridge Portal Citizen Login",
  initial_url: "http://127.0.0.1:5000/demo-target",
  variables: [
    { name: "username", default_value: "gov_citizen", type: "string" },
    { name: "password", default_value: "GovPass@2026", type: "password" }
  ],
  steps: [],
  branching: {
    enabled: true,
    failure_branch: { title: "Login Failed return error", subtitle: "End of the RPA BOT task" },
    success_branch: { title: "Login Successful", subtitle: "End of the RPA BOT task" }
  }
};

let activeEditingStepIndex = null;
let testEventSource = null;
let activePopoverConnectorIdx = null;
let autoSaveTimer = null;
let isSaving = false;

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
  initLocalStorageSync();
  renderWorkflowCanvas();
  bindGlobalEvents();
  initBotCatalogSelector();
  updateAutoSaveUI("saved");

  // Close quick-insert popovers when clicking outside
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".connector-quick-insert-popover") && !e.target.closest(".connector-plus-btn")) {
      closeAllQuickInsertPopovers();
    }
  });
});

function bindGlobalEvents() {
  const saveBtn = document.getElementById("btn-save-bot");
  if (saveBtn) saveBtn.addEventListener("click", () => autoSaveChanges(true));

  const testBtn = document.getElementById("btn-test-bot");
  if (testBtn) testBtn.addEventListener("click", openTestBotModal);

  const titleInput = document.getElementById("bot-title-input");
  if (titleInput) {
    titleInput.addEventListener("input", (e) => {
      currentBot.name = e.target.value.trim() || "Untitled Bot";
      triggerAutoSave();
    });
  }
}

// --------------------------------------------------------------------------
// Visual Canvas Rendering
// --------------------------------------------------------------------------
function renderWorkflowCanvas() {
  const container = document.getElementById("flow-container");
  if (!container) return;
  container.innerHTML = "";

  const steps = currentBot.steps || [];

  steps.forEach((step, idx) => {
    // Re-index step numbers
    step.step_number = idx + 1;

    // 1. Render Step Card
    const card = createStepCard(step, idx);
    container.appendChild(card);

    // 2. Render Connector Arrow + Quick Insert Plus Button
    const connector = createConnector(idx);
    container.appendChild(connector);
  });

  // 3. Render Final Branching (if enabled)
  if (currentBot.branching && currentBot.branching.enabled) {
    const branchContainer = createBranchingNode();
    container.appendChild(branchContainer);
  }
}

function createStepCard(step, idx) {
  const card = document.createElement("div");
  card.className = "node-card";
  card.dataset.stepIndex = idx;

  const isNav = step.action_type === "navigate";
  const stepNum = idx + 1;

  // Top header: step number, title, delete button
  const header = document.createElement("div");
  header.className = "node-header";

  const numTitle = document.createElement("div");
  numTitle.innerHTML = `
    <div style="display: flex; align-items: center; gap: 8px;">
      <div class="node-step-num">${stepNum}</div>
      ${step.optional ? '<span class="node-optional-badge">OPTIONAL</span>' : ''}
    </div>
    <div class="node-title">${escapeHtml(step.title || `Step ${stepNum}`)}</div>
  `;

  header.appendChild(numTitle);

  // Direct, working Delete Button on every non-initial step
  if (idx > 0 || !isNav) {
    const delBadge = document.createElement("button");
    delBadge.type = "button";
    delBadge.className = "node-delete-badge";
    delBadge.innerText = "DELETE";
    delBadge.title = "Delete this step";
    delBadge.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      deleteStep(idx);
    });
    header.appendChild(delBadge);
  }

  card.appendChild(header);

  // Inner box for value/variable or action status
  const innerBox = document.createElement("div");
  innerBox.className = "node-inner-box";

  if (isNav) {
    innerBox.innerHTML = `<strong>${escapeHtml(step.value || "www.example.com")}</strong>`;
  } else if (step.action_type === "type") {
    const isVar = step.value_mode === "variable";
    innerBox.innerHTML = `
      <div class="node-toggle-group">
        <span class="toggle-pill ${!isVar ? 'active' : ''}" onclick="toggleValueMode(event, ${idx}, 'fixed')">Value Entered</span>
        <span>OR</span>
        <span class="toggle-pill ${isVar ? 'active' : ''}" onclick="toggleValueMode(event, ${idx}, 'variable')">Set Variable</span>
      </div>
      <div style="margin-top: 4px;">
        ${isVar ? `<span class="node-variable-tag">{{${escapeHtml(step.variable_name || 'variable')}}}</span>` : `<span>"${escapeHtml(step.value || '')}"</span>`}
      </div>
    `;
  } else if (step.action_type === "canvas_draw") {
    let p1 = "";
    let p2 = "";
    if (step.start_percent_x !== undefined) {
      p1 = `${Math.round(step.start_percent_x * 100)}%, ${Math.round(step.start_percent_y * 100)}%`;
      p2 = `${Math.round(step.end_percent_x * 100)}%, ${Math.round(step.end_percent_y * 100)}%`;
    }
    innerBox.innerHTML = `
      <div style="display: flex; align-items: center; gap: 6px; color: #38bdf8; font-weight: 600; font-size: 0.8rem;">
        <span>✏️</span> Draw Rectangle on Canvas
      </div>
      <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 3px;">
        Vector: ${p1 ? `${p1} → ${p2}` : 'Scaled Canvas Gesture'}
      </div>
    `;
  } else if (step.action_type === "canvas_click") {
    let p = "";
    if (step.percent_x !== undefined) {
      p = `(${Math.round(step.percent_x * 100)}%, ${Math.round(step.percent_y * 100)}%)`;
    }
    innerBox.innerHTML = `
      <div style="display: flex; align-items: center; gap: 6px; color: #34d399; font-weight: 600; font-size: 0.8rem;">
        Precision Point Click
      </div>
      <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 3px;">
        Target: ${p || 'Relative Center'}
      </div>
    `;
  } else if (step.action_type === "click") {
    innerBox.innerHTML = `<span>Click Initiated</span>`;
  } else if (step.action_type === "wait") {
    innerBox.innerHTML = `<span>Wait ${step.value || 1000} ms</span>`;
  } else if (step.action_type === "screenshot") {
    innerBox.innerHTML = `<span>Capture Screenshot</span>`;
  } else {
    innerBox.innerHTML = `<span>${escapeHtml(step.action_type)}</span>`;
  }

  card.appendChild(innerBox);

  // Click card body to open Step Inspector
  card.onclick = () => openStepInspector(idx);

  return card;
}

// --------------------------------------------------------------------------
// Connector with Working Quick-Insert Popover on '+' Click
// --------------------------------------------------------------------------
function createConnector(insertAfterIdx) {
  const group = document.createElement("div");
  group.className = "connector-group";
  group.id = `connector-group-${insertAfterIdx}`;

  const arrow = document.createElement("div");
  arrow.className = "connector-arrow";

  const plusBtn = document.createElement("button");
  plusBtn.type = "button";
  plusBtn.className = "connector-plus-btn";
  plusBtn.innerHTML = "+";
  plusBtn.title = "Quick Insert Step Here";
  plusBtn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    toggleQuickInsertPopover(insertAfterIdx, group);
  });

  group.appendChild(arrow);
  group.appendChild(plusBtn);
  return group;
}

function toggleQuickInsertPopover(insertAfterIdx, groupElement) {
  const existingPopover = groupElement.querySelector(".connector-quick-insert-popover");
  if (existingPopover) {
    existingPopover.remove();
    activePopoverConnectorIdx = null;
    return;
  }

  // Close any other open popovers
  closeAllQuickInsertPopovers();
  activePopoverConnectorIdx = insertAfterIdx;

  // Render floating Quick Insert Bar matching the user's wireframe
  const popover = document.createElement("div");
  popover.className = "connector-quick-insert-popover";
  popover.addEventListener("click", (e) => e.stopPropagation());

  popover.innerHTML = `
    <span class="popover-label">QUICK INSERT:</span>
    <button type="button" class="quick-pill" onclick="insertQuickStep(${insertAfterIdx}, 'wait')">
      ADD WAIT (1 SEC)
    </button>
    <button type="button" class="quick-pill" onclick="insertQuickStep(${insertAfterIdx}, 'screenshot')">
      CAPTURE SCREENSHOT
    </button>
    <button type="button" class="quick-pill" onclick="insertCustomStep(${insertAfterIdx})">
      CUSTOM ACTION
    </button>
    <button type="button" class="popover-close-btn" onclick="closeAllQuickInsertPopovers()" title="Close">✕</button>
  `;

  groupElement.appendChild(popover);
}

function closeAllQuickInsertPopovers() {
  document.querySelectorAll(".connector-quick-insert-popover").forEach(p => p.remove());
  activePopoverConnectorIdx = null;
}

// --------------------------------------------------------------------------
// Quick Insert Steps (Both from Connector '+' and bottom strip)
// --------------------------------------------------------------------------
function insertQuickStep(insertAfterIdx, type) {
  closeAllQuickInsertPopovers();
  const steps = currentBot.steps || [];
  const targetPos = (insertAfterIdx >= 0) ? insertAfterIdx + 1 : steps.length;
  const nextNum = targetPos + 1;

  let newStep = null;

  if (type === "wait") {
    newStep = {
      id: `step_${Date.now()}`,
      step_number: nextNum,
      title: "Wait 1 Second",
      action_type: "wait",
      target_description: "Wait Timer",
      selector: "",
      fallback_selectors: [],
      value_mode: "fixed",
      value: "1000",
      variable_name: "",
      wait_before_ms: 0,
      wait_after_ms: 0,
      timeout_ms: 5000,
      optional: true,
      highlight: false
    };
  } else if (type === "screenshot") {
    newStep = {
      id: `step_${Date.now()}`,
      step_number: nextNum,
      title: "Capture Screenshot",
      action_type: "screenshot",
      target_description: "Screen snapshot",
      selector: "",
      fallback_selectors: [],
      value_mode: "fixed",
      value: "",
      variable_name: "",
      wait_before_ms: 200,
      wait_after_ms: 200,
      timeout_ms: 5000,
      optional: true,
      highlight: false
    };
  }

  if (newStep) {
    steps.splice(targetPos, 0, newStep);
    // Re-index all steps
    steps.forEach((s, i) => s.step_number = i + 1);
    renderWorkflowCanvas();
    triggerAutoSave();
    showToast(`Added ${type === 'wait' ? 'Wait Step' : 'Screenshot Step'} at position ${nextNum}!`);
  }
}

function quickInsert(type) {
  // Bottom strip inserts at the end of steps
  const steps = currentBot.steps || [];
  insertQuickStep(steps.length - 1, type);
}

function insertCustomStep(insertAfterIdx) {
  closeAllQuickInsertPopovers();
  const steps = currentBot.steps || [];
  const targetPos = (insertAfterIdx >= 0) ? insertAfterIdx + 1 : steps.length;
  const nextNum = targetPos + 1;

  const newStep = {
    id: `step_${Date.now()}`,
    step_number: nextNum,
    title: "New Action Step",
    action_type: "click",
    target_description: "Element",
    selector: "#btn",
    fallback_selectors: [],
    value_mode: "fixed",
    value: "",
    variable_name: "",
    wait_before_ms: 200,
    wait_after_ms: 300,
    timeout_ms: 10000,
    optional: false,
    highlight: true
  };

  steps.splice(targetPos, 0, newStep);
  steps.forEach((s, i) => s.step_number = i + 1);
  renderWorkflowCanvas();
  triggerAutoSave();
  openStepInspector(targetPos);
}

// --------------------------------------------------------------------------
// Direct Working Step Deletion
// --------------------------------------------------------------------------
function deleteStep(stepIdx) {
  if (stepIdx < 0 || stepIdx >= currentBot.steps.length) return;
  const deletedTitle = currentBot.steps[stepIdx].title || `Step ${stepIdx + 1}`;
  
  // Instant deletion
  currentBot.steps.splice(stepIdx, 1);
  
  // Re-number remaining steps
  currentBot.steps.forEach((s, i) => {
    s.step_number = i + 1;
  });

  renderWorkflowCanvas();
  triggerAutoSave();
  showToast(`"${deletedTitle}" removed & auto-saved`);
}

function deleteCurrentInspectedStep() {
  if (activeEditingStepIndex !== null) {
    const idx = activeEditingStepIndex;
    closeStepInspector();
    deleteStep(idx);
  }
}

function createBranchingNode() {
  const wrapper = document.createElement("div");
  wrapper.className = "branching-wrapper";

  const bConfig = currentBot.branching || {};
  const fail = bConfig.failure_branch || { title: "Login Failed return error", subtitle: "End of the RPA BOT task" };
  const succ = bConfig.success_branch || { title: "Login Successful", subtitle: "End of the RPA BOT task" };

  wrapper.innerHTML = `
    <div class="branch-node branch-failure">
      <div class="branch-title" style="color: #f43f5e;">${escapeHtml(fail.title)}</div>
      <div class="branch-subtitle">${escapeHtml(fail.subtitle)}</div>
    </div>
    <div style="text-align: center; color: #64748b; font-weight: 700; font-size: 0.8rem;">OR</div>
    <div class="branch-node branch-success">
      <div class="branch-title" style="color: #34d399;">${escapeHtml(succ.title)}</div>
      <div class="branch-subtitle">${escapeHtml(succ.subtitle)}</div>
    </div>
  `;

  return wrapper;
}

function toggleValueMode(event, stepIdx, mode) {
  event.stopPropagation();
  const step = currentBot.steps[stepIdx];
  if (!step) return;

  step.value_mode = mode;
  if (mode === "variable" && !step.variable_name) {
    step.variable_name = "username";
  }
  renderWorkflowCanvas();
}

// --------------------------------------------------------------------------
// Step Inspector Modal
// --------------------------------------------------------------------------
function openStepInspector(idx) {
  activeEditingStepIndex = idx;
  const step = currentBot.steps[idx];
  if (!step) return;

  document.getElementById("edit-step-title").value = step.title || "";
  document.getElementById("edit-step-action").value = step.action_type || "click";
  document.getElementById("edit-step-selector").value = step.selector || "";
  document.getElementById("edit-step-fallbacks").value = (step.fallback_selectors || []).join("\n");
  document.getElementById("edit-step-mode").value = step.value_mode || "fixed";
  document.getElementById("edit-step-value").value = step.value || "";
  document.getElementById("edit-step-variable").value = step.variable_name || "";
  document.getElementById("edit-step-wait-before").value = step.wait_before_ms || 200;
  document.getElementById("edit-step-wait-after").value = step.wait_after_ms || 300;
  document.getElementById("edit-step-optional").checked = !!step.optional;

  toggleInspectorValueFields();

  const modal = document.getElementById("step-inspector-modal");
  if (modal) modal.classList.add("active");
}

function closeStepInspector() {
  const modal = document.getElementById("step-inspector-modal");
  if (modal) modal.classList.remove("active");
  activeEditingStepIndex = null;
}

function toggleInspectorValueFields() {
  const mode = document.getElementById("edit-step-mode").value;
  const valGroup = document.getElementById("group-fixed-val");
  const varGroup = document.getElementById("group-variable-name");
  if (mode === "variable") {
    valGroup.style.display = "none";
    varGroup.style.display = "block";
  } else {
    valGroup.style.display = "block";
    varGroup.style.display = "none";
  }
}

function saveStepInspector() {
  if (activeEditingStepIndex === null) return;
  const step = currentBot.steps[activeEditingStepIndex];
  if (!step) return;

  step.title = document.getElementById("edit-step-title").value.trim();
  step.action_type = document.getElementById("edit-step-action").value;
  step.selector = document.getElementById("edit-step-selector").value.trim();
  
  const fbLines = document.getElementById("edit-step-fallbacks").value.split("\n");
  step.fallback_selectors = fbLines.map(s => s.trim()).filter(s => s.length > 0);

  step.value_mode = document.getElementById("edit-step-mode").value;
  step.value = document.getElementById("edit-step-value").value;
  step.variable_name = document.getElementById("edit-step-variable").value.trim();

  // If variable, ensure it's registered in bot's variables definition
  if (step.value_mode === "variable" && step.variable_name) {
    if (!currentBot.variables.some(v => v.name === step.variable_name)) {
      currentBot.variables.push({
        name: step.variable_name,
        default_value: step.value || "",
        type: "string",
        required: true
      });
    }
  }

  step.wait_before_ms = parseInt(document.getElementById("edit-step-wait-before").value) || 0;
  step.wait_after_ms = parseInt(document.getElementById("edit-step-wait-after").value) || 0;
  step.optional = document.getElementById("edit-step-optional").checked;

  closeStepInspector();
  renderWorkflowCanvas();
  triggerAutoSave();
  showToast("Step updated & auto-saved");
}

// --------------------------------------------------------------------------
// Auto-Save & Local Browser Path Storage
// --------------------------------------------------------------------------
function initLocalStorageSync() {
  if (!currentBot || !currentBot.id) return;
  try {
    const localKey = "govbridge_bot_" + currentBot.id;
    const localData = localStorage.getItem(localKey);
    if (localData) {
      const parsed = JSON.parse(localData);
      if (parsed && Array.isArray(parsed.steps) && parsed.steps.length > 0) {
        if (!currentBot.steps || currentBot.steps.length === 0) {
          currentBot = parsed;
        }
      }
    }
    savePathToLocalStorage(currentBot);
  } catch (e) {
    console.warn("LocalStorage sync error:", e);
  }
}

function savePathToLocalStorage(bot) {
  if (!bot || !bot.id) return;
  try {
    const key = "govbridge_bot_" + bot.id;
    localStorage.setItem(key, JSON.stringify(bot));
    localStorage.setItem("govbridge_last_active_path", JSON.stringify({
      id: bot.id,
      name: bot.name,
      saved_at: new Date().toISOString()
    }));
  } catch (e) {}
}

function triggerAutoSave() {
  savePathToLocalStorage(currentBot);
  updateAutoSaveUI("saving");

  if (autoSaveTimer) clearTimeout(autoSaveTimer);
  autoSaveTimer = setTimeout(() => {
    autoSaveChanges();
  }, 400);
}

async function autoSaveChanges(forceImmediate = false) {
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer);
    autoSaveTimer = null;
  }

  savePathToLocalStorage(currentBot);
  updateAutoSaveUI("saving");

  try {
    isSaving = true;
    const res = await fetch("/api/bots", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentBot)
    });
    const data = await res.json();
    if (data.success && data.bot) {
      currentBot.id = data.bot.id;
      currentBot.updated_at = data.bot.updated_at;
      savePathToLocalStorage(currentBot);
      updateAutoSaveUI("saved");
      return true;
    } else {
      updateAutoSaveUI("error");
      return false;
    }
  } catch (err) {
    console.warn("Auto-save sync to server error:", err);
    updateAutoSaveUI("offline");
    return false;
  } finally {
    isSaving = false;
  }
}

function updateAutoSaveUI(state) {
  const indicator = document.getElementById("auto-save-indicator");
  if (!indicator) return;

  if (state === "saving") {
    indicator.innerText = "● Saving...";
    indicator.className = "auto-save-badge saving";
  } else if (state === "saved") {
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    indicator.innerText = `✓ Auto-Saved ${timeStr}`;
    indicator.className = "auto-save-badge";
  } else if (state === "offline") {
    indicator.innerText = "Saved in Browser (Local)";
    indicator.className = "auto-save-badge saving";
  } else {
    indicator.innerText = "Auto-Save Failed";
    indicator.className = "auto-save-badge error";
  }
}

async function saveBotToServer() {
  await autoSaveChanges(true);
  showToast("Bot saved to server and browser storage!");
}

// --------------------------------------------------------------------------
// Live TEST BOT Feature (Playwright Headed Real Window + Clean Cache)
// --------------------------------------------------------------------------
function openTestBotModal() {
  const modal = document.getElementById("test-bot-modal");
  if (!modal) return;

  // Populate variable inputs dynamically
  const container = document.getElementById("test-variables-container");
  container.innerHTML = "";

  const vars = currentBot.variables || [];
  if (vars.length === 0) {
    container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.85rem;">No dynamic variables required for this bot.</p>`;
  } else {
    vars.forEach(v => {
      const formGroup = document.createElement("div");
      formGroup.className = "form-group";
      formGroup.innerHTML = `
        <label class="form-label">${escapeHtml(v.description || v.name)} (<code>{{${escapeHtml(v.name)}}}</code>)</label>
        <input type="${v.type === 'password' ? 'password' : 'text'}" 
               class="form-control test-var-input" 
               data-var-name="${escapeHtml(v.name)}" 
               value="${escapeHtml(v.default_value || '')}" />
      `;
      container.appendChild(formGroup);
    });
  }

  // Clear previous logs
  const terminal = document.getElementById("terminal-output");
  if (terminal) {
    terminal.innerHTML = `<div class="log-entry log-info"><span class="log-time">[Ready]</span> Click "Run Live Chrome Bot" to launch a clean visible Google Chrome window.</div>`;
  }

  const badge = document.getElementById("test-status-badge");
  if (badge) {
    badge.innerText = "READY";
    badge.className = "badge-status badge-active";
    badge.style.background = "";
    badge.style.color = "";
  }

  const shotsRow = document.getElementById("test-screenshots-row");
  if (shotsRow) shotsRow.innerHTML = "";

  modal.classList.add("active");
}

function closeTestBotModal() {
  if (testEventSource) {
    testEventSource.close();
    testEventSource = null;
  }
  const modal = document.getElementById("test-bot-modal");
  if (modal) modal.classList.remove("active");
}

async function startLiveTestExecution() {
  const terminal = document.getElementById("terminal-output");
  const badge = document.getElementById("test-status-badge");
  const launchBtn = document.getElementById("btn-launch-test");

  if (launchBtn) {
    launchBtn.disabled = true;
    launchBtn.innerText = "Syncing & Launching...";
  }

  if (badge) {
    badge.innerText = "SYNCING";
    badge.className = "badge-status";
    badge.style.background = "var(--gov-amber-surface)";
    badge.style.color = "var(--gov-amber)";
  }

  terminal.innerHTML = `<div class="log-entry log-info"><span class="log-time">[Sync]</span> Auto-saving active workflow to guarantee latest steps, deletions, and options are applied...</div>`;

  // 1. Force immediate server save & local storage sync before running test!
  await autoSaveChanges(true);

  if (launchBtn) {
    launchBtn.innerText = "Opening Chrome Window...";
  }

  if (badge) {
    badge.innerText = "RUNNING";
    badge.className = "badge-status";
    badge.style.background = "var(--gov-blue-surface)";
    badge.style.color = "var(--gov-blue-light)";
  }

  appendLog("log-info", "Launching Google Chrome in visible window with fresh session (zero cache)...");

  // Gather variables
  const queryParams = new URLSearchParams();
  document.querySelectorAll(".test-var-input").forEach(input => {
    const varName = input.dataset.varName;
    const val = input.value.trim();
    queryParams.append(`var_${varName}`, val);
  });

  // Check window mode (headed vs headless)
  const selectedMode = document.querySelector('input[name="test-window-mode"]:checked')?.value || "headed";
  const isHeadless = selectedMode === "headless";

  queryParams.append("headless", isHeadless ? "true" : "false");
  queryParams.append("slow_mo", isHeadless ? "0" : "500");
  queryParams.append("clean_cache", "true");

  const streamUrl = `/api/bots/${currentBot.id}/test-stream?${queryParams.toString()}`;

  if (testEventSource) {
    testEventSource.close();
  }

  testEventSource = new EventSource(streamUrl);

  testEventSource.onmessage = (e) => {
    try {
      const evt = JSON.parse(e.data);
      handleLiveStreamEvent(evt);
    } catch (err) {
      console.error("Error parsing event:", err);
    }
  };

  testEventSource.onerror = (err) => {
    appendLog("log-error", "Execution finished or connection ended.");
    if (testEventSource) {
      testEventSource.close();
      testEventSource = null;
    }
    if (launchBtn) {
      launchBtn.disabled = false;
      launchBtn.innerHTML = "Run Live Chrome Bot";
    }
  };
}

function handleLiveStreamEvent(evt) {
  const type = evt.type;
  const timeStr = evt.timestamp || new Date().toLocaleTimeString();

  if (type === "bot_start") {
    appendLog("log-info", `Bot execution started in ${evt.mode} with clean cache & session.`);
  } else if (type === "step_start") {
    appendLog("log-info", `Step ${evt.step_number}: ${evt.title} (${evt.action_type})`);
  } else if (type === "step_success") {
    appendLog("log-success", `Step ${evt.step_number} completed in ${evt.duration_ms}ms: ${evt.details}`);
    if (evt.screenshot) {
      addScreenshotThumbnail(evt.step_number, evt.title, evt.screenshot);
    }
  } else if (type === "step_failed") {
    appendLog("log-error", `Step ${evt.step_number} failed (${evt.duration_ms}ms): ${evt.error}`);
  } else if (type === "branch_evaluated") {
    const isSucc = evt.outcome === "success";
    appendLog(isSucc ? "log-success" : "log-error", `Branch evaluated: ${evt.branch_name} (${evt.subtitle}) - ${evt.message}`);
  } else if (type === "bot_completed") {
    const isSuccess = evt.status === "success";
    appendLog(isSuccess ? "log-success" : "log-error", `RPA Task Finished in ${evt.total_duration_sec}s with status: ${evt.status.toUpperCase()}`);

    const badge = document.getElementById("test-status-badge");
    if (badge) {
      badge.innerText = isSuccess ? "COMPLETED" : "FAILED";
      badge.style.background = isSuccess ? "rgba(16, 185, 129, 0.2)" : "rgba(244, 63, 94, 0.2)";
      badge.style.color = isSuccess ? "#34d399" : "#f43f5e";
    }

    const launchBtn = document.getElementById("btn-launch-test");
    if (launchBtn) {
      launchBtn.disabled = false;
      launchBtn.innerHTML = "Run Live Chrome Bot";
    }

    if (testEventSource) {
      testEventSource.close();
      testEventSource = null;
    }
  }
}

function appendLog(styleClass, text) {
  const terminal = document.getElementById("terminal-output");
  if (!terminal) return;
  const entry = document.createElement("div");
  entry.className = `log-entry ${styleClass}`;
  const now = new Date().toLocaleTimeString();
  entry.innerHTML = `<span class="log-time">[${now}]</span> ${escapeHtml(text)}`;
  terminal.appendChild(entry);
  terminal.scrollTop = terminal.scrollHeight;
}

function addScreenshotThumbnail(stepNum, title, b64) {
  const row = document.getElementById("test-screenshots-row");
  if (!row) return;
  const col = document.createElement("div");
  col.style.display = "flex";
  col.style.flexDirection = "column";
  col.style.gap = "4px";
  col.innerHTML = `
    <span style="font-size: 10px; color: #94a3b8;">Step ${stepNum}: ${escapeHtml(title.slice(0, 15))}</span>
    <img src="data:image/jpeg;base64,${b64}" style="width: 110px; height: 70px; object-fit: cover; border-radius: 4px; border: 1px solid #334155; cursor: pointer;" onclick="viewFullImage('data:image/jpeg;base64,${b64}')" />
  `;
  row.appendChild(col);
}

function viewFullImage(src) {
  const win = window.open("");
  win.document.write(`<body style="margin:0; background:#000; display:flex; justify-content:center; align-items:center; height:100vh;"><img src="${src}" style="max-width:100%; max-height:100%;" /></body>`);
}



function copyCodeFromElement(elemId) {
  const elem = document.getElementById(elemId);
  if (!elem) return;
  navigator.clipboard.writeText(elem.innerText);
  showToast("Copied to clipboard!");
}

// --------------------------------------------------------------------------
// Toast Utility
// --------------------------------------------------------------------------
function showToast(message) {
  let toast = document.getElementById("global-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "global-toast";
    toast.style.position = "fixed";
    toast.style.bottom = "24px";
    toast.style.right = "24px";
    toast.style.background = "#131620";
    toast.style.border = "1px solid #2d3345";
    toast.style.color = "#f8fafc";
    toast.style.padding = "10px 18px";
    toast.style.borderRadius = "8px";
    toast.style.boxShadow = "0 8px 24px rgba(0,0,0,0.6)";
    toast.style.fontWeight = "600";
    toast.style.fontSize = "13px";
    toast.style.zIndex = "99999";
    toast.style.transition = "all 0.3s ease";
    document.body.appendChild(toast);
  }
  toast.innerText = message;
  toast.style.opacity = "1";
  toast.style.transform = "translateY(0)";

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
  }, 2500);
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

// --------------------------------------------------------------------------
// Bot Catalog Quick Selector
// --------------------------------------------------------------------------
async function initBotCatalogSelector() {
  const select = document.getElementById("bot-catalog-select");
  if (!select) return;

  try {
    const res = await fetch("/api/bots");
    const data = await res.json();
    if (data && data.success && Array.isArray(data.bots)) {
      select.innerHTML = "";
      data.bots.forEach(b => {
        const opt = document.createElement("option");
        opt.value = b.id;
        opt.innerText = `${b.name} (${(b.steps || []).length} steps)`;
        if (b.id === currentBot.id) {
          opt.selected = true;
        }
        select.appendChild(opt);
      });

      select.addEventListener("change", (e) => {
        const targetId = e.target.value;
        if (targetId && targetId !== currentBot.id) {
          window.location.href = `/builder?bot_id=${encodeURIComponent(targetId)}`;
        }
      });
    }
  } catch (err) {
    console.warn("Could not load bot catalog:", err);
  }
}

// --------------------------------------------------------------------------
// API Activation & Payloads Modal Controller
// --------------------------------------------------------------------------
let activeApiPayloadData = null;

async function openApiModal() {
  const modal = document.getElementById("api-integration-modal");
  if (!modal) return;

  const endpointUrl = `${window.location.origin}/api/bots/${currentBot.id}/execute`;
  const endpointElem = document.getElementById("api-endpoint-url");
  if (endpointElem) endpointElem.innerText = endpointUrl;

  // Build default variables dictionary
  const sampleVars = {};
  (currentBot.variables || []).forEach(v => {
    sampleVars[v.name] = v.default_value || "";
  });

  const defaultJson = {
    variables: sampleVars,
    options: {
      headless: true,
      timeout_ms: 15000,
      take_screenshots: true
    },
    webhook_url: "https://your-backend.com/api/rpa/callback"
  };

  // Populate dynamic test variable fields
  const testVarsContainer = document.getElementById("api-test-vars-container");
  if (testVarsContainer) {
    testVarsContainer.innerHTML = "";
    if (!currentBot.variables || currentBot.variables.length === 0) {
      testVarsContainer.innerHTML = `<p style="color: var(--text-muted); font-size: 0.8rem; grid-column: 1 / -1;">No runtime variables required for this bot. Ready to trigger!</p>`;
    } else {
      currentBot.variables.forEach(v => {
        const grp = document.createElement("div");
        grp.className = "form-group";
        grp.style.marginBottom = "0.4rem";
        grp.innerHTML = `
          <label class="form-label" style="font-size: 0.75rem; margin-bottom: 3px;">
            ${escapeHtml(v.description || v.name)} (<code>${escapeHtml(v.name)}</code>)
          </label>
          <input type="${v.type === 'password' ? 'password' : 'text'}"
                 class="form-control api-test-var-input"
                 style="padding: 0.35rem 0.6rem; font-size: 0.8rem;"
                 data-var-name="${escapeHtml(v.name)}"
                 value="${escapeHtml(v.default_value || '')}" />
        `;
        testVarsContainer.appendChild(grp);
      });
    }
  }

  // Pre-fill panes with local defaults first
  renderApiSnippets(endpointUrl, defaultJson);

  modal.classList.add("active");

  // Fetch verified server-generated payloads & snippets
  try {
    const res = await fetch(`/api/bots/${currentBot.id}/payloads`);
    const data = await res.json();
    if (data && data.success) {
      activeApiPayloadData = data;
      renderApiSnippets(data.endpoint || endpointUrl, data.json_body, data.xml_body, data.snippets);
    }
  } catch (err) {
    console.warn("Could not fetch remote snippets:", err);
  }
}

function renderApiSnippets(endpoint, jsonBody, xmlBody = "", snippets = {}) {
  const codeJson = document.getElementById("code-json-payload");
  if (codeJson) codeJson.innerText = JSON.stringify(jsonBody, null, 2);

  const codeCurl = document.getElementById("code-curl-payload");
  if (codeCurl) {
    codeCurl.innerText = snippets.curl_json || `curl -X POST "${endpoint}" \\\n  -H "Content-Type: application/json" \\\n  -d '${JSON.stringify(jsonBody, null, 2)}'`;
  }

  const codeNode = document.getElementById("code-nodejs-payload");
  if (codeNode) {
    codeNode.innerText = snippets.javascript || `const response = await fetch("${endpoint}", {\n  method: "POST",\n  headers: { "Content-Type": "application/json" },\n  body: JSON.stringify(${JSON.stringify(jsonBody, null, 2)})\n});\n\nconst result = await response.json();\nconsole.log("RPA Result:", result);`;
  }

  const codePy = document.getElementById("code-python-payload");
  if (codePy) {
    codePy.innerText = snippets.python || `import requests\n\nurl = "${endpoint}"\nheaders = {"Content-Type": "application/json"}\npayload = ${JSON.stringify(jsonBody, null, 4)}\n\nresponse = requests.post(url, json=payload, headers=headers)\nprint("Status Code:", response.status_code)\nprint("Response:", response.json())`;
  }

  const codeXml = document.getElementById("code-xml-payload");
  if (codeXml) {
    codeXml.innerText = xmlBody || `<?xml version="1.0" encoding="UTF-8"?>\n<RpaExecutionRequest>\n  <BotId>${currentBot.id}</BotId>\n  <Variables>\n${Object.entries(jsonBody.variables || {}).map(([k,v]) => `    <Variable name="${k}">${v}</Variable>`).join("\n")}\n  </Variables>\n  <Options>\n    <Headless>true</Headless>\n    <TimeoutMs>15000</TimeoutMs>\n  </Options>\n</RpaExecutionRequest>`;
  }
}

function closeApiModal() {
  const modal = document.getElementById("api-integration-modal");
  if (modal) modal.classList.remove("active");
}

function switchApiTab(tabName) {
  document.querySelectorAll(".api-tab").forEach(tab => {
    tab.classList.toggle("active", tab.dataset.tab === tabName);
  });
  document.querySelectorAll(".api-pane").forEach(pane => {
    pane.classList.toggle("active", pane.id === `api-pane-${tabName}`);
  });
}

function copyApiEndpoint() {
  const endpoint = document.getElementById("api-endpoint-url")?.innerText;
  if (endpoint) {
    navigator.clipboard.writeText(endpoint);
    showToast("✓ Endpoint copied to clipboard!");
  }
}

async function executeApiSimulation() {
  const btn = document.getElementById("btn-run-api-test");
  const respArea = document.getElementById("api-test-response-area");
  const respCode = document.getElementById("api-test-response-json");
  const statusPill = document.getElementById("api-test-status-pill");

  // Collect test variables
  const vars = {};
  document.querySelectorAll(".api-test-var-input").forEach(inp => {
    const name = inp.dataset.varName;
    if (name) vars[name] = inp.value;
  });

  const isHeadless = document.getElementById("api-test-headless")?.checked !== false;

  const payload = {
    variables: vars,
    options: {
      headless: isHeadless,
      take_screenshots: true
    }
  };

  btn.disabled = true;
  btn.innerText = "⏳ Calling API Endpoint...";
  respArea.style.display = "block";
  respCode.innerText = "Sending HTTP POST request to /api/bots/" + currentBot.id + "/execute ...";
  statusPill.innerText = "PENDING";
  statusPill.className = "badge-status";
  statusPill.style.background = "rgba(56, 189, 248, 0.2)";
  statusPill.style.color = "#38bdf8";

  const startTime = Date.now();
  try {
    const res = await fetch(`/api/bots/${currentBot.id}/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const latency = Date.now() - startTime;
    const json = await res.json();

    respCode.innerText = JSON.stringify(json, null, 2);
    if (res.ok && json.success) {
      statusPill.innerText = `HTTP ${res.status} OK (${latency}ms)`;
      statusPill.style.background = "rgba(16, 185, 129, 0.2)";
      statusPill.style.color = "#34d399";
      showToast("✓ RPA Bot executed successfully via API!");
    } else {
      statusPill.innerText = `HTTP ${res.status} ${res.statusText || 'Error'} (${latency}ms)`;
      statusPill.style.background = "rgba(244, 63, 94, 0.2)";
      statusPill.style.color = "#f43f5e";
    }
  } catch (err) {
    respCode.innerText = "Network Error: " + err.message;
    statusPill.innerText = "FAILED";
    statusPill.style.background = "rgba(244, 63, 94, 0.2)";
    statusPill.style.color = "#f43f5e";
  } finally {
    btn.disabled = false;
    btn.innerText = "⚡ Trigger via API Now";
  }
}

