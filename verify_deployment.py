"""
MahaSetu RPA Ecosystem - End-to-End Deployment Verification Suite
Validates both Web Dev / Cloud Deployment and Chrome Extension Distribution.
Usage:
  python verify_deployment.py
  python verify_deployment.py --url https://your-deployed-domain.com
"""
import argparse
import io
import json
import sys
import time
import zipfile
import requests

def run_verification(base_url: str):
    print("=" * 65)
    print("  MAHASETU RPA ECOSYSTEM - DEPLOYMENT VERIFICATION SUITE")
    print("=" * 65)
    print(f"  * Target URL: {base_url}")
    print(f"  * Timestamp:  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65 + "\n")

    passed = 0
    total = 0

    def assert_step(name, condition, details=""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  [PASS] {name} {('- ' + details) if details else ''}")
        else:
            print(f"  [FAIL] {name} {('- ' + details) if details else ''}")
            sys.exit(1)

    # --------------------------------------------------------------------------
    # 1. Health API Verification
    # --------------------------------------------------------------------------
    print("[1] Verifying System Health API...")
    try:
        res = requests.get(f"{base_url}/api/health", timeout=10)
        assert_step("HTTP 200 on /api/health", res.status_code == 200, f"Status: {res.status_code}")
        data = res.json()
        assert_step("Status is healthy", data.get("status") == "healthy", f"State: {data.get('status')}")
        assert_step("Version reported", "version" in data, f"Version: {data.get('version')}")
        assert_step("Storage reported ready", data.get("storage_ready") is True)
    except Exception as e:
        assert_step("Health API reachable", False, str(e))

    # --------------------------------------------------------------------------
    # 2. Security Headers Verification
    # --------------------------------------------------------------------------
    print("\n[2] Verifying Security Headers...")
    headers = res.headers
    assert_step("X-Content-Type-Options is nosniff", headers.get("X-Content-Type-Options") == "nosniff")
    assert_step("X-Frame-Options is set", "X-Frame-Options" in headers)

    # --------------------------------------------------------------------------
    # 3. Web Views Routing
    # --------------------------------------------------------------------------
    print("\n[3] Verifying Web Portal Views...")
    for route in ["/", "/builder", "/extension-guide", "/demo-target"]:
        r = requests.get(f"{base_url}{route}", timeout=10)
        assert_step(f"Route '{route}' accessible", r.status_code == 200, f"Code: {r.status_code}")

    # --------------------------------------------------------------------------
    # 4. Chrome Extension Download Bundle Verification
    # --------------------------------------------------------------------------
    print("\n[4] Verifying Chrome Extension Distribution...")
    ext_res = requests.get(f"{base_url}/api/extension/download", timeout=15)
    assert_step("Extension download returns HTTP 200", ext_res.status_code == 200)
    assert_step("Mimetype is application/zip", "zip" in ext_res.headers.get("Content-Type", "").lower())
    
    # Verify downloaded bytes form a valid zip containing manifest.json
    try:
        zip_buf = io.BytesIO(ext_res.content)
        with zipfile.ZipFile(zip_buf, "r") as zf:
            namelist = zf.namelist()
            assert_step("ZIP contains manifest.json", "manifest.json" in namelist)
            assert_step("ZIP contains background.js", "background.js" in namelist)
            assert_step("ZIP contains content.js", "content.js" in namelist)
            manifest_data = json.loads(zf.read("manifest.json").decode("utf-8"))
            assert_step("Manifest name is valid", "MahaSetu" in manifest_data.get("name", ""))
            print(f"       Total packaged extension files: {len(namelist)} ({round(len(ext_res.content)/1024, 1)} KB)")
    except Exception as e:
        assert_step("Valid ZIP archive downloaded", False, str(e))

    # --------------------------------------------------------------------------
    # 5. Bot Catalog API Verification
    # --------------------------------------------------------------------------
    print("\n[5] Verifying Bot Catalog API...")
    bots_res = requests.get(f"{base_url}/api/bots", timeout=10)
    assert_step("Bots catalog returns 200", bots_res.status_code == 200)
    bots_data = bots_res.json()
    assert_step("Bot list is populated", len(bots_data.get("bots", [])) > 0, f"{len(bots_data.get('bots', []))} bots found")

    # --------------------------------------------------------------------------
    # 6. Sample Payloads Generator
    # --------------------------------------------------------------------------
    print("\n[6] Verifying Payload Generator (JSON & XML)...")
    payload_res = requests.get(f"{base_url}/api/bots/govbridge_login_bot_01/payloads", timeout=10)
    assert_step("Payload generator returns 200", payload_res.status_code == 200)
    p_data = payload_res.json()
    assert_step("JSON payload template generated", "json_body" in p_data)
    assert_step("XML payload template generated", "xml_body" in p_data and "<RpaExecutionRequest>" in p_data["xml_body"])

    # --------------------------------------------------------------------------
    # 7. Extension Recording Ingestion Endpoint
    # --------------------------------------------------------------------------
    print("\n[7] Verifying Chrome Extension Recording Ingestion...")
    sample_trace = {
        "initial_url": f"{base_url}/demo-target",
        "name": "Deployment Verification Bot Path",
        "actions": [
            {
                "type": "input",
                "selector": "#username",
                "fallbacks": ["input[name='username']"],
                "target_name": "username",
                "value": "gov_citizen"
            },
            {
                "type": "input",
                "selector": "#password",
                "fallbacks": ["input[name='password']"],
                "target_name": "password",
                "value": "GovPass@2026"
            },
            {
                "type": "click",
                "selector": "#submit-btn",
                "fallbacks": ["button[type='submit']"],
                "target_name": "Sign In",
                "text": "Sign In to Portal"
            }
        ]
    }
    rec_res = requests.post(f"{base_url}/api/recordings", json=sample_trace, timeout=15)
    assert_step("Recording ingestion returns HTTP 201", rec_res.status_code == 201)
    rec_data = rec_res.json()
    created_bot_id = rec_data.get("bot_id")
    assert_step("Draft bot ID created", bool(created_bot_id), f"Bot ID: {created_bot_id}")
    assert_step("Redirect URL provided", bool(rec_data.get("redirect_url")), f"Redirect: {rec_data.get('redirect_url')}")

    # --------------------------------------------------------------------------
    # 8. Headless Execution Engine (JSON)
    # --------------------------------------------------------------------------
    print("\n[8] Verifying Headless Bot Execution (JSON API)...")
    t0 = time.time()
    exec_res = requests.post(
        f"{base_url}/api/bots/govbridge_login_bot_01/execute",
        headers={"Content-Type": "application/json"},
        json={
            "variables": {
                "username": "gov_citizen",
                "password": "GovPass@2026"
            },
            "options": {
                "headless": True
            }
        },
        timeout=35
    )
    assert_step("Execution endpoint returns HTTP 200", exec_res.status_code == 200)
    exec_json = exec_res.json()
    result = exec_json.get("result", {})
    assert_step("Bot status is SUCCESS", result.get("status") == "success", f"Duration: {result.get('total_duration_sec')}s")
    branch = result.get("branch_result", {})
    assert_step("Success outcome evaluated", branch.get("outcome") == "success", f"Branch: {branch.get('branch_name')}")

    # --------------------------------------------------------------------------
    # 9. Headless Execution Engine (XML)
    # --------------------------------------------------------------------------
    print("\n[9] Verifying Headless Bot Execution (XML API)...")
    xml_req = f"""<?xml version="1.0" encoding="UTF-8"?>
<RpaExecutionRequest>
  <BotId>govbridge_login_bot_01</BotId>
  <Variables>
    <Variable name="username">gov_citizen</Variable>
    <Variable name="password">GovPass@2026</Variable>
  </Variables>
  <Options>
    <Headless>true</Headless>
  </Options>
</RpaExecutionRequest>"""

    xml_res = requests.post(
        f"{base_url}/api/bots/govbridge_login_bot_01/execute",
        headers={"Content-Type": "application/xml"},
        data=xml_req,
        timeout=35
    )
    assert_step("XML Execution returns HTTP 200", xml_res.status_code == 200)
    xml_result = xml_res.json().get("result", {})
    assert_step("XML Bot status is SUCCESS", xml_result.get("status") == "success")

    # --------------------------------------------------------------------------
    # Summary
    # --------------------------------------------------------------------------
    print("\n" + "=" * 65)
    print(f"  ALL {passed}/{total} DEPLOYMENT VERIFICATION CHECKS PASSED!")
    print("=" * 65)
    print(f"  MahaSetu RPA Ecosystem is FULLY READY for Production Deployment.")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MahaSetu Deployment Verification Suite")
    parser.add_argument("--url", default="http://127.0.0.1:5000", help="Base URL of MahaSetu server")
    args = parser.parse_args()
    base_url = args.url.rstrip("/")
    run_verification(base_url)
