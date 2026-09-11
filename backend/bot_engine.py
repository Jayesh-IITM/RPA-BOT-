"""
Bot Engine Module - Playwright-based RPA Execution Engine
Runs automated browser tasks in headed (visible) or headless mode with
resilient multi-selector fallbacks, dynamic variable interpolation,
live visual highlighting, and real-time execution logging.
"""
import base64
import json
import os
import re
import sys
import time
from typing import Callable, Dict, List, Optional, Tuple
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

CHROME_PATH = os.getenv("CHROME_PATH", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "data", "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def interpolate_variables(text: str, variables: Dict[str, str]) -> str:
    """Replaces {{variable_name}} templates with runtime values."""
    if not isinstance(text, str):
        return text
    
    def replacer(match):
        var_name = match.group(1).strip()
        return str(variables.get(var_name, match.group(0)))
        
    return re.sub(r"\{\{\s*([a-zA-Z0-9_-]+)\s*\}\}", replacer, text)


def is_login_bot(bot_data: Dict) -> bool:
    """Detects if this bot workflow interacts with an authentication / login form."""
    variables = bot_data.get("variables", [])
    for v in variables:
        v_name = (v.get("name") or "").lower()
        v_type = (v.get("type") or "").lower()
        if v_type == "password" or "password" in v_name or "passwd" in v_name or v_name == "pwd" or v_name == "pass":
            return True

    steps = bot_data.get("steps", [])
    for s in steps:
        target = (s.get("target_description") or "").lower()
        title = (s.get("title") or "").lower()
        sel = (s.get("selector") or "").lower()
        var = (s.get("variable_name") or "").lower()
        fallbacks = " ".join(s.get("fallback_selectors") or []).lower()
        
        combined = f"{target} {title} {sel} {var} {fallbacks}"
        if "password" in combined or "passwd" in combined:
            return True

    has_input = any(s.get("action_type") == "type" for s in steps)
    has_login_btn = any(
        any(k in (s.get("title") or "").lower() or k in (s.get("target_description") or "").lower() or k in (s.get("selector") or "").lower()
            for k in ["login", "sign in", "signin"])
        for s in steps
    )
    if has_input and has_login_btn:
        return True

    return False


class BotExecutionEngine:
    def __init__(self, bot_data: Dict, variables: Optional[Dict[str, str]] = None, options: Optional[Dict] = None):
        self.bot_data = bot_data
        
        # Merge provided variables with bot's declared variable defaults
        merged_vars = {}
        for var_def in bot_data.get("variables", []):
            name = var_def.get("name")
            if name:
                merged_vars[name] = var_def.get("default_value", "")
        if variables:
            merged_vars.update(variables)
        self.variables = merged_vars
        
        self.options = options or {}
        # Default to headed=True for live testing unless explicitly requested headless
        self.headless = self.options.get("headless", False)
        self.slow_mo = self.options.get("slow_mo", 400 if not self.headless else 0)
        self.take_screenshots = self.options.get("take_screenshots", True)
        self.highlight_elements = self.options.get("highlight", True)
        
        self.logs: List[Dict] = []
        self.screenshots: List[Dict] = []
        self.extracted_data: Dict[str, str] = {}
        self.on_event: Optional[Callable[[Dict], None]] = None

    def emit_event(self, event_type: str, data: Dict):
        """Sends an event to the registered listener (e.g. SSE stream)."""
        payload = {
            "type": event_type,
            "timestamp": time.strftime("%H:%M:%S"),
            **data
        }
        self.logs.append(payload)
        if self.on_event:
            try:
                self.on_event(payload)
            except Exception:
                pass

    def _highlight_element(self, page: Page, selector: str, step_label: str):
        """Draws a glowing visual border and tooltip badge in the browser page for live visual feedback."""
        if not self.highlight_elements or self.headless:
            return
        try:
            page.evaluate(
                """([sel, label]) => {
                    const el = document.querySelector(sel);
                    if (!el) return;
                    
                    // Remove any previous highlight
                    const oldOverlay = document.getElementById('govbridge-rpa-badge');
                    if (oldOverlay) oldOverlay.remove();
                    
                    // Style element with glowing border
                    const originalOutline = el.style.outline;
                    const originalBoxShadow = el.style.boxShadow;
                    el.style.outline = '3px solid #00f2fe';
                    el.style.boxShadow = '0 0 16px rgba(0, 242, 254, 0.8)';
                    el.style.transition = 'all 0.2s ease-in-out';
                    
                    // Create floating badge
                    const rect = el.getBoundingClientRect();
                    const badge = document.createElement('div');
                    badge.id = 'govbridge-rpa-badge';
                    badge.innerText = '🤖 GovBridge Bot: ' + label;
                    badge.style.position = 'fixed';
                    badge.style.top = Math.max(10, rect.top - 32) + 'px';
                    badge.style.left = Math.max(10, rect.left) + 'px';
                    badge.style.background = '#0f172a';
                    badge.style.color = '#38bdf8';
                    badge.style.border = '1px solid #38bdf8';
                    badge.style.padding = '4px 10px';
                    badge.style.borderRadius = '6px';
                    badge.style.fontSize = '12px';
                    badge.style.fontWeight = 'bold';
                    badge.style.zIndex = '999999';
                    badge.style.boxShadow = '0 4px 12px rgba(0,0,0,0.4)';
                    badge.style.pointerEvents = 'none';
                    document.body.appendChild(badge);
                    
                    setTimeout(() => {
                        el.style.outline = originalOutline;
                        el.style.boxShadow = originalBoxShadow;
                        if (badge.parentNode) badge.remove();
                    }, 1800);
                }""",
                [selector, step_label]
            )
        except Exception:
            pass

    def _sanitize_selector(self, sel: str) -> List[str]:
        """Ensures selectors with unescaped colons or special chars work properly in Playwright."""
        if not sel or not isinstance(sel, str):
            return []
        res = [sel]
        if sel.startswith("#") and ":" in sel:
            raw_id = sel[1:]
            escaped = "#" + raw_id.replace(":", r"\:")
            if escaped not in res:
                res.append(escaped)
            attr_sel = f'[id="{raw_id}"]'
            if attr_sel not in res:
                res.append(attr_sel)
        return res

    def _resolve_element(self, page: Page, primary_selector: str, fallbacks: List[str], timeout_ms: int = 8000, step: Optional[Dict] = None):
        """
        Smart Element Resolution:
        1. Sanitizes and tests primary selector and fallbacks.
        2. If all CSS/XPath selectors fail, employs smart semantic fallbacks
           (accessible role/name, text heuristics, placeholders, data-testid).
        """
        candidates = []
        if primary_selector:
            for s in self._sanitize_selector(primary_selector):
                if s and s not in candidates:
                    candidates.append(s)
        if fallbacks:
            for fb in fallbacks:
                for s in self._sanitize_selector(fb):
                    if s and s not in candidates:
                        candidates.append(s)

        # 1. Try CSS and XPath candidates
        per_sel_timeout = max(800, timeout_ms // max(1, len(candidates)))
        last_err = None
        for sel in candidates:
            try:
                loc = page.locator(sel).first
                loc.wait_for(state="visible", timeout=per_sel_timeout)
                return loc, sel
            except Exception as e:
                last_err = e
                continue

        # 2. Smart Semantic & Text-Heuristic Fallbacks
        if step:
            step_action = step.get("action_type", "").lower()
            title = step.get("title", "")
            target_desc = step.get("target_description", "")
            step_text = step.get("text", "")

            # If targeting canvas
            if "canvas" in step_action or "canvas" in str(primary_selector).lower() or "canvas" in target_desc.lower():
                try:
                    c_loc = page.locator("canvas").first
                    c_loc.wait_for(state="attached", timeout=2000)
                    return c_loc, "canvas"
                except Exception:
                    pass

            # Extract clean keyword from title / target description / text
            keyword = ""
            for raw in [step_text, target_desc, title]:
                if raw:
                    cleaned = re.sub(r"\s*(Button|field|input|option|link)$", "", raw, flags=re.IGNORECASE).strip()
                    cleaned = cleaned.split("\n")[0].strip()
                    if cleaned and len(cleaned) <= 32:
                        keyword = cleaned
                        break

            if keyword:
                semantic_candidates = [
                    f"button:has-text('{keyword}')",
                    f"[role='button']:has-text('{keyword}')",
                    f"a:has-text('{keyword}')",
                    f"[aria-label*='{keyword}']",
                    f"[title*='{keyword}']",
                    f"text='{keyword}'"
                ]
                for sem_sel in semantic_candidates:
                    try:
                        loc = page.locator(sem_sel).first
                        if loc.is_visible(timeout=1000):
                            self.emit_event("engine_notice", {
                                "message": f"Resolved element via smart semantic heuristic: {sem_sel}"
                            })
                            return loc, sem_sel
                    except Exception:
                        continue

            # Fallback for input / textarea fields
            var_name = step.get("variable_name", "")
            if var_name:
                input_candidates = [
                    f"input[name*='{var_name}']",
                    f"textarea[name*='{var_name}']",
                    f"input[placeholder*='{var_name}']",
                    "textarea"
                ]
                for inp_sel in input_candidates:
                    try:
                        loc = page.locator(inp_sel).first
                        if loc.is_visible(timeout=1000):
                            return loc, inp_sel
                    except Exception:
                        continue

        raise RuntimeError(f"Could not locate element with selectors {candidates}. Last error: {last_err}")

    def _smart_click(self, loc, page: Page, timeout_ms: int = 4000) -> str:
        """
        Executes a click using multi-tiered resilience:
        1. Standard Playwright click
        2. Force click (bypasses overlays, animations, pointer-event interception)
        3. Native DOM dispatch_event('click')
        4. In-page JavaScript evaluate element.click()
        """
        try:
            loc.scroll_into_view_if_needed(timeout=1500)
        except Exception:
            pass

        # Strategy 1: Standard click
        try:
            loc.click(timeout=min(2500, timeout_ms))
            return "standard_click"
        except Exception as e1:
            self.emit_event("engine_notice", {
                "message": f"Standard click intercepted/delayed: {e1}; falling back to resilient force-click."
            })

        # Strategy 2: Force click (overrides Playwright's strict hit-target / overlay obstruction check)
        try:
            loc.click(force=True, timeout=2000)
            return "force_click"
        except Exception as e2:
            self.emit_event("engine_notice", {
                "message": f"Force-click encountered obstacle: {e2}; falling back to DOM event dispatch."
            })

        # Strategy 3: Native DOM dispatchEvent
        try:
            loc.dispatch_event("click")
            return "dispatch_event"
        except Exception as e3:
            pass

        # Strategy 4: Direct DOM JavaScript execution
        try:
            page.evaluate("el => el.click()", loc.element_handle())
            return "dom_evaluate_click"
        except Exception as e4:
            raise RuntimeError(f"All 4 resilient click strategies failed. Last error: {e4}")

    def _smart_type(self, loc, page: Page, value: str) -> str:
        """Types value into element with fallback for React controlled inputs / rich editors."""
        try:
            loc.scroll_into_view_if_needed(timeout=1500)
        except Exception:
            pass

        try:
            loc.fill(value, timeout=3000)
            return "fill"
        except Exception:
            pass

        # Fallback for rich-text / React controlled inputs
        try:
            self._smart_click(loc, page, timeout_ms=2000)
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.keyboard.type(value, delay=20)
            return "keyboard_type"
        except Exception as e:
            raise RuntimeError(f"Failed to type value into element: {e}")

    def _execute_canvas_draw(self, page: Page, loc, step: Dict) -> str:
        """
        Draws a rectangle, line, or gesture stroke on an HTML5 canvas or drawing surface.
        Interpolates smooth coordinates based on normalized canvas percentages.
        """
        box = loc.bounding_box()
        if not box:
            vp = page.viewport_size or {"width": 1280, "height": 800}
            box = {"x": 50, "y": 80, "width": vp["width"] - 100, "height": vp["height"] - 120}

        # Retrieve normalized coordinates
        start_px = step.get("start_percent_x")
        start_py = step.get("start_percent_y")
        end_px = step.get("end_percent_x")
        end_py = step.get("end_percent_y")

        if start_px is None or end_px is None:
            try:
                val_data = json.loads(step.get("value", "{}"))
                start_px = val_data.get("start_percent_x", 0.25)
                start_py = val_data.get("start_percent_y", 0.25)
                end_px = val_data.get("end_percent_x", 0.55)
                end_py = val_data.get("end_percent_y", 0.55)
            except Exception:
                start_px, start_py, end_px, end_py = 0.25, 0.25, 0.55, 0.55

        # Compute screen pixel positions
        start_x = box["x"] + (box["width"] * float(start_px))
        start_y = box["y"] + (box["height"] * float(start_py))
        end_x = box["x"] + (box["width"] * float(end_px))
        end_y = box["y"] + (box["height"] * float(end_py))

        # Perform human-like mouse drag gesture with 20 interpolation steps
        page.mouse.move(start_x, start_y)
        time.sleep(0.08)
        page.mouse.down()
        time.sleep(0.05)
        page.mouse.move(end_x, end_y, steps=20)
        time.sleep(0.05)
        page.mouse.up()
        time.sleep(0.15)

        p1 = f"({round(float(start_px)*100)}%, {round(float(start_py)*100)}%)"
        p2 = f"({round(float(end_px)*100)}%, {round(float(end_py)*100)}%)"
        return f"Successfully traced rectangle on canvas from {p1} to {p2}"

    def _execute_canvas_click(self, page: Page, loc, step: Dict) -> str:
        """Performs precision click on a specific relative canvas point."""
        box = loc.bounding_box()
        if not box:
            vp = page.viewport_size or {"width": 1280, "height": 800}
            box = {"x": 50, "y": 80, "width": vp["width"] - 100, "height": vp["height"] - 120}

        px = step.get("percent_x")
        py = step.get("percent_y")
        if px is None or py is None:
            try:
                val_data = json.loads(step.get("value", "{}"))
                px = val_data.get("percent_x", 0.5)
                py = val_data.get("percent_y", 0.5)
            except Exception:
                px, py = 0.5, 0.5

        target_x = box["x"] + (box["width"] * float(px))
        target_y = box["y"] + (box["height"] * float(py))

        page.mouse.click(target_x, target_y)
        return f"Clicked canvas point at ({round(float(px)*100)}%, {round(float(py)*100)}%)"


    def execute(self) -> Dict:
        """Main execution loop running the bot steps in Playwright."""
        bot_id = self.bot_data.get("id", "bot_temp")
        bot_name = self.bot_data.get("name", "Untitled Bot")
        start_time = time.time()
        
        self.emit_event("bot_start", {
            "bot_id": bot_id,
            "bot_name": bot_name,
            "variables": self.variables,
            "mode": "Headed Chrome" if not self.headless else "Headless"
        })

        launch_args = [
            "--new-window",
            "--start-maximized",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=OptimizationHints,Translate"
        ]
        
        # Create a fresh isolated temp user-data-dir so every test starts with 100% clean cache, zero cookies, and opens in a fresh window
        import tempfile
        import shutil
        temp_profile = tempfile.mkdtemp(prefix="govbridge_clean_profile_")

        overall_status = "success"
        branch_result = None
        step_results = []

        # Handle display-less cloud environments (Docker, Linux VPS, Render)
        actual_headless = self.headless
        if not actual_headless:
            if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
                self.emit_event("engine_notice", {
                    "message": "Cloud environment detected without physical DISPLAY. Executing in headless mode with live screenshot streaming."
                })
                actual_headless = True

        with sync_playwright() as p:
            try:
                launch_kwargs = {
                    "user_data_dir": temp_profile,
                    "headless": actual_headless,
                    "slow_mo": self.slow_mo if not actual_headless else 0,
                    "no_viewport": True,
                    "ignore_https_errors": True,
                    "args": launch_args
                }
                chrome_exec = os.getenv("CHROME_PATH") or CHROME_PATH
                if chrome_exec and os.path.exists(chrome_exec):
                    launch_kwargs["executable_path"] = chrome_exec

                context = p.chromium.launch_persistent_context(**launch_kwargs)
                context.clear_cookies()
                context.clear_permissions()

                page = context.pages[0] if context.pages else context.new_page()
                page.bring_to_front()
                
                steps = sorted(self.bot_data.get("steps", []), key=lambda s: s.get("step_number", 0))

                for step in steps:
                    step_num = step.get("step_number", 1)
                    title = step.get("title", f"Step {step_num}")
                    action = step.get("action_type", "click").lower()
                    step_start = time.time()

                    self.emit_event("step_start", {
                        "step_number": step_num,
                        "title": title,
                        "action_type": action
                    })

                    # Optional pre-delay
                    wait_before = step.get("wait_before_ms", 0)
                    if wait_before > 0:
                        time.sleep(wait_before / 1000.0)

                    try:
                        step_detail = self._execute_step(page, step)
                        step_duration = round((time.time() - step_start) * 1000)

                        screenshot_b64 = None
                        if self.take_screenshots:
                            try:
                                shot_bytes = page.screenshot(type="jpeg", quality=60)
                                screenshot_b64 = base64.b64encode(shot_bytes).decode("utf-8")
                            except Exception:
                                pass

                        step_res = {
                            "step_number": step_num,
                            "title": title,
                            "status": "success",
                            "duration_ms": step_duration,
                            "details": step_detail,
                            "screenshot": screenshot_b64
                        }
                        step_results.append(step_res)

                        self.emit_event("step_success", step_res)

                    except Exception as step_err:
                        step_duration = round((time.time() - step_start) * 1000)
                        err_msg = str(step_err)
                        optional = step.get("optional", False)

                        step_res = {
                            "step_number": step_num,
                            "title": title,
                            "status": "failed",
                            "duration_ms": step_duration,
                            "error": err_msg,
                            "optional": optional
                        }
                        step_results.append(step_res)

                        self.emit_event("step_failed", step_res)

                        if not optional:
                            overall_status = "failed"
                            break

                    # Optional post-delay
                    wait_after = step.get("wait_after_ms", 0)
                    if wait_after > 0:
                        time.sleep(wait_after / 1000.0)

                # Evaluate branching / outcome if defined and bot has a login form
                branch_cfg = self.bot_data.get("branching", {})
                if branch_cfg and branch_cfg.get("enabled", False) and is_login_bot(self.bot_data):
                    branch_result = self._evaluate_branching(page, branch_cfg)
                    self.emit_event("branch_evaluated", branch_result)

                # Final screenshot
                final_screenshot = None
                try:
                    shot_bytes = page.screenshot(type="jpeg", quality=75)
                    final_screenshot = base64.b64encode(shot_bytes).decode("utf-8")
                except Exception:
                    pass

                # If headed, hold open briefly so user can see completion
                if not self.headless:
                    time.sleep(1.5)

                try:
                    context.close()
                except Exception:
                    pass

                try:
                    shutil.rmtree(temp_profile, ignore_errors=True)
                except Exception:
                    pass

            except Exception as engine_err:
                overall_status = "error"
                self.emit_event("engine_error", {"error": str(engine_err)})

        total_duration = round(time.time() - start_time, 2)
        
        # Emit completion event before attaching logs to avoid circular reference
        completion_event_data = {
            "bot_id": bot_id,
            "status": overall_status,
            "total_duration_sec": total_duration,
            "step_results": step_results,
            "branch_result": branch_result,
            "extracted_data": self.extracted_data,
            "final_screenshot": final_screenshot if 'final_screenshot' in locals() else None
        }
        self.emit_event("bot_completed", completion_event_data)

        final_summary = dict(completion_event_data)
        final_summary["logs"] = list(self.logs)
        return final_summary

    def _execute_step(self, page: Page, step: Dict) -> str:
        """Executes a single step action."""
        action = step.get("action_type", "").lower()
        title = step.get("title", "")
        primary_sel = step.get("selector", "")
        fallbacks = step.get("fallback_selectors", [])
        timeout = step.get("timeout_ms", 10000)
        
        # Determine value (either fixed value or variable)
        val_mode = step.get("value_mode", "fixed")
        if val_mode == "variable":
            var_name = step.get("variable_name", "")
            raw_value = self.variables.get(var_name, step.get("value", ""))
        else:
            raw_value = step.get("value", "")
            
        value = interpolate_variables(str(raw_value), self.variables)

        if action == "navigate":
            nav_url = value or primary_sel
            if not nav_url.startswith("http://") and not nav_url.startswith("https://"):
                nav_url = "http://" + nav_url

            # Map dynamic container port for cloud deployments (Railway, Render, etc.)
            active_port = os.getenv("PORT", "5000")
            if active_port != "5000":
                nav_url = re.sub(r"://(?:127\.0\.0\.1|localhost):5000\b", f"://127.0.0.1:{active_port}", nav_url)

            page.goto(nav_url, wait_until="domcontentloaded", timeout=timeout)
            return f"Navigated to {nav_url}"

        elif action == "type":
            loc, matched_sel = self._resolve_element(page, primary_sel, fallbacks, timeout, step=step)
            self._highlight_element(page, matched_sel, f"Typing in {title}")
            strategy = self._smart_type(loc, page, value)
            return f"Typed value into {matched_sel} ({strategy})"

        elif action == "click":
            loc, matched_sel = self._resolve_element(page, primary_sel, fallbacks, timeout, step=step)
            self._highlight_element(page, matched_sel, f"Clicking {title}")
            strategy = self._smart_click(loc, page, timeout_ms=timeout)
            return f"Clicked element {matched_sel} ({strategy})"

        elif action == "canvas_draw":
            loc, matched_sel = self._resolve_element(page, primary_sel or "canvas", fallbacks, timeout, step=step)
            self._highlight_element(page, matched_sel, "Tracing on Canvas")
            return self._execute_canvas_draw(page, loc, step)

        elif action == "canvas_click":
            loc, matched_sel = self._resolve_element(page, primary_sel or "canvas", fallbacks, timeout, step=step)
            self._highlight_element(page, matched_sel, "Canvas Precision Click")
            return self._execute_canvas_click(page, loc, step)

        elif action == "select":
            loc, matched_sel = self._resolve_element(page, primary_sel, fallbacks, timeout, step=step)
            self._highlight_element(page, matched_sel, f"Selecting {value}")
            loc.select_option(value=value)
            return f"Selected option '{value}' on {matched_sel}"

        elif action == "wait":
            wait_ms = int(value or 1000)
            time.sleep(wait_ms / 1000.0)
            return f"Waited {wait_ms} ms"

        elif action == "screenshot":
            return "Captured step screenshot"

        elif action == "extract_text":
            loc, matched_sel = self._resolve_element(page, primary_sel, fallbacks, timeout, step=step)
            text = loc.inner_text()
            var_key = step.get("variable_name") or f"extracted_{step.get('step_number')}"
            self.extracted_data[var_key] = text
            return f"Extracted text '{text}' into {var_key}"

        elif action == "assert_text":
            loc, matched_sel = self._resolve_element(page, primary_sel, fallbacks, timeout, step=step)
            text = loc.inner_text()
            if value.lower() not in text.lower():
                raise AssertionError(f"Expected text '{value}' not found in '{text}'")
            return f"Assertion passed: text contains '{value}'"

        elif action == "assert_url":
            current_url = page.url
            if value.lower() not in current_url.lower():
                raise AssertionError(f"Expected URL to contain '{value}', but current is '{current_url}'")
            return f"Assertion passed: URL contains '{value}'"

        else:
            raise ValueError(f"Unsupported action type '{action}'")

    def _evaluate_branching(self, page: Page, branch_cfg: Dict) -> Dict:
        """Evaluates outcome conditions for success vs failure branches."""
        fail_sel = branch_cfg.get("failure_selector")
        success_url = branch_cfg.get("success_url_contains")
        success_sel = branch_cfg.get("success_selector")
        
        current_url = page.url
        is_failure = False
        failure_reason = ""
        
        # Check if error element is visible
        if fail_sel:
            try:
                err_loc = page.locator(fail_sel).first
                if err_loc.is_visible(timeout=1000):
                    is_failure = True
                    failure_reason = err_loc.inner_text() or "Error element detected"
            except Exception:
                pass
                
        # Check success condition
        is_success = False
        if not is_failure:
            if success_url and success_url in current_url:
                is_success = True
            elif success_sel:
                try:
                    s_loc = page.locator(success_sel).first
                    if s_loc.is_visible(timeout=1500):
                        is_success = True
                except Exception:
                    pass

        if is_failure or not is_success:
            branch = branch_cfg.get("failure_branch", {})
            return {
                "outcome": "failure",
                "branch_name": branch.get("title", "Login Failed return error"),
                "subtitle": branch.get("subtitle", "End of the RPA BOT task"),
                "message": failure_reason or branch.get("message", "Task ended in failure condition"),
                "status_code": branch.get("status_code", 400),
                "url": current_url
            }
        else:
            branch = branch_cfg.get("success_branch", {})
            return {
                "outcome": "success",
                "branch_name": branch.get("title", "Login Successful"),
                "subtitle": branch.get("subtitle", "End of the RPA BOT task"),
                "message": branch.get("message", "Workflow succeeded and reached target end state"),
                "status_code": branch.get("status_code", 200),
                "url": current_url
            }
