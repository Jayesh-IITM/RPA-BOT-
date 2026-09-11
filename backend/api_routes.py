import os
import sys
import json
import queue
import threading
import time
from flask import Blueprint, Response, jsonify, render_template, request, send_file
import xmltodict

from bot_engine import BotExecutionEngine
from bot_storage import storage

api_bp = Blueprint("api", __name__)


# --------------------------------------------------------------------------
# Health Check & System Status Endpoint
# --------------------------------------------------------------------------

@api_bp.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint for container orchestrators (Kubernetes, Docker),
    cloud platforms (Render, Railway, AWS ALB), and extension connectivity checks.
    """
    playwright_ok = True
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        playwright_ok = False

    data_dir = getattr(storage, "data_dir", os.path.join(os.path.dirname(__file__), "data"))
    storage_ok = os.path.exists(data_dir) and os.access(data_dir, os.W_OK)
    
    return jsonify({
        "status": "healthy" if storage_ok else "degraded",
        "service": "MahaSetu RPA Ecosystem",
        "version": "1.0.0",
        "timestamp": time.time(),
        "environment": os.getenv("FLASK_ENV", "production"),
        "playwright_ready": playwright_ok,
        "storage_ready": storage_ok,
        "saved_bots_count": len(storage.list_bots())
    }), 200 if storage_ok else 503


# --------------------------------------------------------------------------
# Chrome Extension Distribution Endpoint
# --------------------------------------------------------------------------

@api_bp.route("/extension/download", methods=["GET"])
def download_extension_bundle():
    """
    Provides direct in-browser download of the pre-packaged Chrome Extension zip bundle.
    Generates the bundle on demand if not already present.
    """
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dist_zip = os.path.join(root_dir, "dist", "mahasetu-rpa-recorder-v1.0.0.zip")
    downloads_zip = os.path.join(os.path.dirname(__file__), "static", "downloads", "mahasetu-rpa-recorder.zip")

    target_zip = downloads_zip if os.path.exists(downloads_zip) else (dist_zip if os.path.exists(dist_zip) else None)

    if not target_zip:
        try:
            sys_path_added = False
            scripts_dir = os.path.join(root_dir, "scripts")
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
                sys_path_added = True
            import package_extension
            target_zip = package_extension.package_extension()
        except Exception as e:
            return jsonify({"success": False, "error": f"Failed to package extension: {e}"}), 500

    return send_file(
        target_zip,
        mimetype="application/zip",
        as_attachment=True,
        download_name="mahasetu-rpa-recorder-v1.0.0.zip"
    )


# --------------------------------------------------------------------------
# Bot Management CRUD Endpoints
# --------------------------------------------------------------------------

@api_bp.route("/bots", methods=["GET"])
def list_bots():
    """List all saved bots in the ecosystem."""
    bots = storage.list_bots()
    return jsonify({"success": True, "count": len(bots), "bots": bots})


@api_bp.route("/bots/<bot_id>", methods=["GET"])
def get_bot(bot_id):
    """Retrieve details for a specific bot."""
    bot = storage.get_bot(bot_id)
    if not bot:
        return jsonify({"success": False, "error": f"Bot with ID '{bot_id}' not found"}), 404
    return jsonify({"success": True, "bot": bot})


@api_bp.route("/bots", methods=["POST"])
def create_or_save_bot():
    """Create or update a bot."""
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"success": False, "error": "Invalid or missing JSON payload"}), 400
        
    saved_bot = storage.save_bot(data)
    return jsonify({
        "success": True,
        "message": "Bot saved successfully",
        "bot": saved_bot,
        "endpoint": f"/api/bots/{saved_bot['id']}/execute"
    }), 201


@api_bp.route("/bots/<bot_id>", methods=["PUT"])
def update_bot(bot_id):
    """Update an existing bot."""
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"success": False, "error": "Invalid or missing JSON payload"}), 400
        
    data["id"] = bot_id
    saved_bot = storage.save_bot(data)
    return jsonify({"success": True, "message": "Bot updated", "bot": saved_bot})


@api_bp.route("/bots/<bot_id>", methods=["DELETE"])
def delete_bot(bot_id):
    """Delete a bot from the catalog."""
    deleted = storage.delete_bot(bot_id)
    if not deleted:
        return jsonify({"success": False, "error": f"Bot '{bot_id}' not found"}), 404
    return jsonify({"success": True, "message": f"Bot '{bot_id}' deleted successfully"})


# --------------------------------------------------------------------------
# Third-Party Backend Execution Endpoint (Accepts BOTH JSON and XML)
# --------------------------------------------------------------------------

def _parse_execution_request(req):
    """Parses incoming execution payload supporting both JSON and XML bodies."""
    content_type = req.headers.get("Content-Type", "").lower()
    variables = {}
    options = {}
    webhook_url = None

    if "xml" in content_type:
        try:
            xml_raw = req.get_data(as_text=True)
            parsed = xmltodict.parse(xml_raw)
            # Find root element
            root_key = list(parsed.keys())[0]
            root = parsed[root_key]

            # Parse variables
            vars_node = root.get("Variables", {})
            if vars_node:
                var_items = vars_node.get("Variable", [])
                if isinstance(var_items, dict):
                    var_items = [var_items]
                for item in var_items:
                    if isinstance(item, dict):
                        var_name = item.get("@name") or item.get("name")
                        var_val = item.get("#text") or item.get("value", "")
                        if var_name:
                            variables[var_name] = var_val

            # Parse options
            opts_node = root.get("Options", {})
            if opts_node:
                for k, v in opts_node.items():
                    # clean string booleans
                    if str(v).lower() in ("true", "1"):
                        options[k.lower()] = True
                    elif str(v).lower() in ("false", "0"):
                        options[k.lower()] = False
                    else:
                        options[k.lower()] = v

            webhook_url = root.get("WebhookUrl")

        except Exception as e:
            raise ValueError(f"Failed to parse XML payload: {e}")
    else:
        # Default JSON parsing
        try:
            body = req.get_json(force=True, silent=True) or {}
            variables = body.get("variables", {})
            options = body.get("options", {})
            webhook_url = body.get("webhook_url")
        except Exception as e:
            raise ValueError(f"Failed to parse JSON payload: {e}")

    return variables, options, webhook_url


@api_bp.route("/bots/<bot_id>/execute", methods=["POST"])
def execute_bot_api(bot_id):
    """
    Direct API endpoint to trigger the bot from other website backends.
    Accepts:
      - Content-Type: application/json
      - Content-Type: application/xml or text/xml
    """
    bot = storage.get_bot(bot_id)
    if not bot:
        return jsonify({"success": False, "error": f"Bot '{bot_id}' not found"}), 404

    try:
        variables, options, webhook_url = _parse_execution_request(request)
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400

    # Backend trigger defaults to headless unless requested otherwise
    if "headless" not in options:
        options["headless"] = True

    engine = BotExecutionEngine(bot_data=bot, variables=variables, options=options)
    result = engine.execute()

    # If caller requested XML response
    accept_header = request.headers.get("Accept", "").lower()
    if "xml" in accept_header:
        xml_output = xmltodict.unparse({
            "RpaExecutionResponse": {
                "BotId": bot_id,
                "Status": result["status"],
                "TotalDurationSec": result["total_duration_sec"],
                "BranchResult": result.get("branch_result") or {},
                "ExtractedData": result.get("extracted_data") or {}
            }
        }, pretty=True)
        return Response(xml_output, mimetype="application/xml")

    return jsonify({
        "success": result["status"] == "success",
        "bot_id": bot_id,
        "result": result
    })


# --------------------------------------------------------------------------
# Sample Payloads & Endpoints Generator (JSON & XML)
# --------------------------------------------------------------------------

@api_bp.route("/bots/<bot_id>/payloads", methods=["GET"])
def get_bot_payloads(bot_id):
    """Generates ready-to-use JSON and XML request bodies, plus cURL and Python snippets."""
    bot = storage.get_bot(bot_id)
    if not bot:
        return jsonify({"success": False, "error": f"Bot '{bot_id}' not found"}), 404

    # Build sample variable dict
    sample_vars = {}
    for var in bot.get("variables", []):
        sample_vars[var.get("name")] = var.get("default_value", "sample_value")

    # JSON Body
    json_body = {
        "variables": sample_vars,
        "options": {
            "headless": True,
            "timeout_ms": 15000,
            "take_screenshots": True
        },
        "webhook_url": "https://your-backend.com/api/rpa/callback"
    }

    # XML Body
    xml_dict = {
        "RpaExecutionRequest": {
            "BotId": bot_id,
            "Variables": {
                "Variable": [
                    {"@name": k, "#text": v} for k, v in sample_vars.items()
                ]
            },
            "Options": {
                "Headless": "true",
                "TimeoutMs": "15000",
                "TakeScreenshots": "true"
            },
            "WebhookUrl": "https://your-backend.com/api/rpa/callback"
        }
    }
    xml_body = xmltodict.unparse(xml_dict, pretty=True)

    base_url = request.host_url.rstrip("/")
    endpoint = f"{base_url}/api/bots/{bot_id}/execute"

    curl_json = f"""curl -X POST "{endpoint}" \\
  -H "Content-Type: application/json" \\
  -d '{json.dumps(json_body, indent=2)}'"""

    curl_xml = f"""curl -X POST "{endpoint}" \\
  -H "Content-Type: application/xml" \\
  --data-binary @- << 'EOF'
{xml_body}
EOF"""

    python_code = f"""import requests

url = "{endpoint}"
headers = {{"Content-Type": "application/json"}}
payload = {json.dumps(json_body, indent=4)}

response = requests.post(url, json=payload, headers=headers)
print("Status Code:", response.status_code)
print("Response:", response.json())
"""

    node_code = f"""const response = await fetch("{endpoint}", {{
  method: "POST",
  headers: {{ "Content-Type": "application/json" }},
  body: JSON.stringify({json.dumps(json_body, indent=2)})
}});

const result = await response.json();
console.log("RPA Result:", result);
"""

    return jsonify({
        "success": True,
        "bot_id": bot_id,
        "endpoint": endpoint,
        "json_body": json_body,
        "xml_body": xml_body,
        "snippets": {
            "curl_json": curl_json,
            "curl_xml": curl_xml,
            "python": python_code,
            "javascript": node_code
        }
    })


# --------------------------------------------------------------------------
# Live Test Bot Feature (SSE Stream with Headed Chrome Window)
# --------------------------------------------------------------------------

@api_bp.route("/bots/<bot_id>/test-stream", methods=["GET"])
def test_bot_stream(bot_id):
    """
    Opens Chrome in a NEW VISIBLE WINDOW in front of the user (Playwright headless=False),
    and streams live step execution events, logs, and screenshots back via Server-Sent Events (SSE).
    """
    bot = storage.get_bot(bot_id)
    if not bot:
        return jsonify({"error": f"Bot '{bot_id}' not found"}), 404

    # Extract query params for variables if any
    variables = {}
    for k, v in request.args.items():
        if k.startswith("var_"):
            var_name = k[4:]
            variables[var_name] = v

    headless_param = request.args.get("headless", "false").lower() == "true"
    slow_mo_param = int(request.args.get("slow_mo", "450"))

    event_q = queue.Queue()

    def sse_callback(event):
        event_q.put(event)

    engine = BotExecutionEngine(
        bot_data=bot,
        variables=variables,
        options={
            "headless": headless_param,
            "slow_mo": slow_mo_param,
            "take_screenshots": True,
            "highlight": True
        }
    )
    engine.on_event = sse_callback

    def run_thread():
        try:
            engine.execute()
        except Exception as e:
            event_q.put({"type": "engine_error", "error": str(e)})
        finally:
            event_q.put(None)  # Sentinel to end stream

    threading.Thread(target=run_thread, daemon=True).start()

    def event_generator():
        while True:
            try:
                evt = event_q.get(timeout=60)
                if evt is None:
                    break
                data_str = json.dumps(evt)
                yield f"data: {data_str}\n\n"
            except queue.Empty:
                yield ": keep-alive\n\n"

    return Response(event_generator(), mimetype="text/event-stream")


# --------------------------------------------------------------------------
# Extension Recording Ingestion Endpoint
# --------------------------------------------------------------------------

@api_bp.route("/recordings", methods=["POST"])
def upload_recording():
    """
    Called by the Chrome Extension when user stops recording.
    Converts raw recorded actions into a structured GovBridge bot workflow.
    """
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"success": False, "error": "Missing recording payload"}), 400

    raw_actions = data.get("actions", [])
    initial_url = data.get("initial_url", "http://127.0.0.1:5000/demo-target")

    # Transform raw actions into clean GovBridge steps
    steps = []
    variables_found = {}
    step_idx = 1

    # Step 1: Initial Navigation
    steps.append({
        "id": f"step_{step_idx}",
        "step_number": step_idx,
        "title": f"Extension initiated on {initial_url.split('://')[-1].split('/')[0]}",
        "action_type": "navigate",
        "target_description": "Initial URL",
        "selector": "",
        "fallback_selectors": [],
        "value_mode": "fixed",
        "value": initial_url,
        "variable_name": "",
        "wait_before_ms": 200,
        "wait_after_ms": 500,
        "timeout_ms": 15000,
        "optional": False,
        "highlight": True
    })
    step_idx += 1

    for action in raw_actions:
        a_type = action.get("type")
        target_name = action.get("target_name") or action.get("placeholder") or action.get("id") or "field"
        
        if a_type in ("input", "type"):
            val = action.get("value", "")
            # Auto detect password or username fields for dynamic variable binding
            is_pass = "password" in target_name.lower() or action.get("input_type") == "password"
            var_name = "password" if is_pass else ("username" if "user" in target_name.lower() else f"var_{target_name.replace(' ', '_').lower()[:12]}")
            
            variables_found[var_name] = {
                "name": var_name,
                "default_value": val,
                "type": "password" if is_pass else "string",
                "description": f"Input for {target_name}",
                "required": True
            }

            steps.append({
                "id": f"step_{step_idx}",
                "step_number": step_idx,
                "title": f"Input in {target_name.title()} field",
                "action_type": "type",
                "target_description": f"{target_name} field",
                "selector": action.get("selector", ""),
                "fallback_selectors": action.get("fallbacks", []),
                "value_mode": "variable",
                "value": val,
                "variable_name": var_name,
                "wait_before_ms": 250,
                "wait_after_ms": 300,
                "timeout_ms": 10000,
                "optional": False,
                "highlight": True
            })
            step_idx += 1

        elif a_type == "canvas_draw":
            start_px = action.get("start_percent_x", 0.2)
            start_py = action.get("start_percent_y", 0.2)
            end_px = action.get("end_percent_x", 0.5)
            end_py = action.get("end_percent_y", 0.5)
            p1 = f"{round(start_px * 100)}%, {round(start_py * 100)}%"
            p2 = f"{round(end_px * 100)}%, {round(end_py * 100)}%"

            steps.append({
                "id": f"step_{step_idx}",
                "step_number": step_idx,
                "title": f"Draw Rectangle on Canvas",
                "action_type": "canvas_draw",
                "target_description": f"Canvas Gesture ({p1} → {p2})",
                "selector": action.get("selector", "canvas"),
                "fallback_selectors": action.get("fallbacks", []),
                "value_mode": "fixed",
                "value": json.dumps({
                    "start_percent_x": start_px,
                    "start_percent_y": start_py,
                    "end_percent_x": end_px,
                    "end_percent_y": end_py,
                    "start_x": action.get("start_x", 0),
                    "start_y": action.get("start_y", 0),
                    "end_x": action.get("end_x", 0),
                    "end_y": action.get("end_y", 0),
                    "steps": 20
                }),
                "start_percent_x": start_px,
                "start_percent_y": start_py,
                "end_percent_x": end_px,
                "end_percent_y": end_py,
                "variable_name": "",
                "wait_before_ms": 300,
                "wait_after_ms": 600,
                "timeout_ms": 10000,
                "optional": False,
                "highlight": True
            })
            step_idx += 1

        elif a_type == "canvas_click":
            px = action.get("percent_x", 0.5)
            py = action.get("percent_y", 0.5)
            p_str = f"{round(px * 100)}%, {round(py * 100)}%"

            steps.append({
                "id": f"step_{step_idx}",
                "step_number": step_idx,
                "title": f"Click Canvas Point ({p_str})",
                "action_type": "canvas_click",
                "target_description": f"Canvas Point ({p_str})",
                "selector": action.get("selector", "canvas"),
                "fallback_selectors": action.get("fallbacks", []),
                "value_mode": "fixed",
                "value": json.dumps({
                    "percent_x": px,
                    "percent_y": py,
                    "offset_x": action.get("offset_x", 0),
                    "offset_y": action.get("offset_y", 0)
                }),
                "percent_x": px,
                "percent_y": py,
                "variable_name": "",
                "wait_before_ms": 300,
                "wait_after_ms": 500,
                "timeout_ms": 10000,
                "optional": False,
                "highlight": True
            })
            step_idx += 1

        elif a_type == "click":
            raw_text = action.get("text") or target_name or "Button"
            clean_title = raw_text.split("\n")[0].strip()
            if len(clean_title) > 32:
                clean_title = clean_title[:32] + "..."
            if not clean_title:
                clean_title = "Click Element"

            title_str = f"{clean_title.title()} Button" if not clean_title.lower().endswith("button") else clean_title.title()

            steps.append({
                "id": f"step_{step_idx}",
                "step_number": step_idx,
                "title": title_str,
                "action_type": "click",
                "target_description": f"{clean_title} Button",
                "selector": action.get("selector", ""),
                "fallback_selectors": action.get("fallbacks", []),
                "value_mode": "fixed",
                "value": "",
                "variable_name": "",
                "wait_before_ms": 300,
                "wait_after_ms": 800,
                "timeout_ms": 10000,
                "optional": False,
                "highlight": True
            })
            step_idx += 1

        elif a_type == "select":
            sel_val = action.get("value", "")
            sel_txt = action.get("text") or sel_val
            steps.append({
                "id": f"step_{step_idx}",
                "step_number": step_idx,
                "title": f"Select '{sel_txt}'",
                "action_type": "select",
                "target_description": f"{target_name} option",
                "selector": action.get("selector", ""),
                "fallback_selectors": action.get("fallbacks", []),
                "value_mode": "fixed",
                "value": sel_val,
                "variable_name": "",
                "wait_before_ms": 250,
                "wait_after_ms": 400,
                "timeout_ms": 10000,
                "optional": False,
                "highlight": True
            })
            step_idx += 1

        elif a_type == "wait":
            steps.append({
                "id": f"step_{step_idx}",
                "step_number": step_idx,
                "title": "Wait Delay",
                "action_type": "wait",
                "target_description": "Wait Timer",
                "selector": "",
                "fallback_selectors": [],
                "value_mode": "fixed",
                "value": action.get("duration", 1000),
                "variable_name": "",
                "wait_before_ms": 0,
                "wait_after_ms": 0,
                "timeout_ms": 5000,
                "optional": True,
                "highlight": False
            })
            step_idx += 1

    # Detect if this recording actually contains a login form
    has_login = False
    for action in raw_actions:
        target_name = (action.get("target_name") or action.get("placeholder") or action.get("id") or "").lower()
        sel = (action.get("selector") or "").lower()
        inp_type = (action.get("input_type") or "").lower()
        if "password" in target_name or "password" in sel or inp_type == "password" or "passwd" in target_name or "pass" in target_name:
            has_login = True
            break
        if ("login" in target_name or "sign in" in target_name or "signin" in target_name) and any(a.get("type") in ("input", "type") for a in raw_actions):
            has_login = True
            break

    if not has_login and any(v.get("type") == "password" or "pass" in v.get("name", "").lower() for v in variables_found.values()):
        has_login = True

    branching_cfg = {
        "enabled": has_login,
        "check_type": "url_or_element" if has_login else "none",
        "failure_selector": "#error-message" if has_login else "",
        "success_url_contains": "dashboard" if has_login else "",
        "success_selector": "",
        "failure_branch": {
            "title": "Login Failed return error",
            "subtitle": "End of the RPA BOT task",
            "outcome": "error",
            "message": "Invalid authentication credentials.",
            "status_code": 401
        } if has_login else None,
        "success_branch": {
            "title": "Login Successful",
            "subtitle": "End of the RPA BOT task",
            "outcome": "success",
            "message": "Workflow reached target success state.",
            "status_code": 200
        } if has_login else None,
        "terminal_branch": {
            "title": "Workflow Completed",
            "subtitle": "End of the RPA BOT task",
            "outcome": "success"
        }
    }

    # Form new draft bot
    bot_id = f"bot_rec_{int(time.time())}"
    bot_data = {
        "id": bot_id,
        "name": data.get("name") or f"Recorded Bot - {time.strftime('%b %d, %H:%M')}",
        "description": f"Workflow automatically generated from Chrome Extension path trace on {initial_url}",
        "initial_url": initial_url,
        "variables": list(variables_found.values()),
        "steps": steps,
        "branching": branching_cfg
    }

    # Save to storage
    storage.save_bot(bot_data)
    rec_id = storage.save_recording({
        "recording_id": bot_id,
        "raw_actions": raw_actions,
        "bot_data": bot_data
    })

    return jsonify({
        "success": True,
        "message": "Recording processed successfully",
        "bot_id": bot_id,
        "redirect_url": f"/builder?bot_id={bot_id}"
    }), 201
