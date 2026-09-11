"""
Comprehensive Ecosystem Test Suite
Verifies web views, API endpoints, JSON & XML payload execution, and Playwright automation.
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def test_pages():
    print("[1] Testing Web Pages...")
    for route in ["/", "/builder", "/extension-guide", "/demo-target"]:
        res = requests.get(f"{BASE_URL}{route}")
        assert res.status_code == 200, f"Route {route} failed with status {res.status_code}"
        print(f"  + Route '{route}' responded with 200 OK")

def test_api_bots():
    print("\n[2] Testing Bot Catalog API...")
    res = requests.get(f"{BASE_URL}/api/bots")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["bots"]) > 0
    print(f"  + Retrieved {len(data['bots'])} saved bots")

def test_payloads():
    print("\n[3] Testing Generated Payloads (JSON and XML)...")
    res = requests.get(f"{BASE_URL}/api/bots/govbridge_login_bot_01/payloads")
    assert res.status_code == 200
    data = res.json()
    assert "json_body" in data
    assert "xml_body" in data
    assert "<RpaExecutionRequest>" in data["xml_body"]
    print("  + JSON Body validated:", list(data["json_body"].keys()))
    print("  + XML Body validated:\n" + "\n".join("    " + line for line in data["xml_body"].splitlines()[:6]) + "\n    ...")

def test_extension_recording_upload():
    print("\n[4] Testing Chrome Extension Recording Ingestion...")
    sample_recording = {
        "initial_url": "http://127.0.0.1:5000/demo-target",
        "name": "Extension Recorded Test Journey",
        "actions": [
            {
                "type": "input",
                "selector": "#username",
                "fallbacks": ["input[name='username']"],
                "target_name": "username",
                "input_type": "text",
                "value": "gov_citizen"
            },
            {
                "type": "input",
                "selector": "#password",
                "fallbacks": ["input[name='password']"],
                "target_name": "password",
                "input_type": "password",
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
    res = requests.post(f"{BASE_URL}/api/recordings", json=sample_recording)
    assert res.status_code == 201, f"Recording upload failed: {res.text}"
    data = res.json()
    assert "redirect_url" in data
    assert "bot_id" in data
    print(f"  + Extension trace converted to Bot ID: {data['bot_id']}")
    print(f"  + Redirect URL: {data['redirect_url']}")

def test_bot_execution_json():
    print("\n[5] Testing Bot Execution via JSON Payload...")
    payload = {
        "variables": {
            "username": "gov_citizen",
            "password": "GovPass@2026"
        },
        "options": {
            "headless": True
        }
    }
    start = time.time()
    res = requests.post(
        f"{BASE_URL}/api/bots/govbridge_login_bot_01/execute",
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=30
    )
    assert res.status_code == 200, f"Execution failed: {res.text}"
    data = res.json()
    result = data["result"]
    print(f"  + Bot Status: {result['status'].upper()} in {result['total_duration_sec']}s")
    assert result["status"] == "success"
    assert result["branch_result"]["outcome"] == "success"
    print(f"  + Branch Outcome: {result['branch_result']['branch_name']} ({result['branch_result']['subtitle']})")

def test_bot_execution_xml():
    print("\n[6] Testing Bot Execution via XML Payload...")
    xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
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

    res = requests.post(
        f"{BASE_URL}/api/bots/govbridge_login_bot_01/execute",
        headers={"Content-Type": "application/xml"},
        data=xml_payload,
        timeout=30
    )
    assert res.status_code == 200, f"XML Execution failed: {res.text}"
    data = res.json()
    result = data["result"]
    assert result["status"] == "success"
    print(f"  + Bot XML Execution Status: {result['status'].upper()}")
    print(f"  + Branch Evaluated: {result['branch_result']['branch_name']}")

def test_bot_execution_failure_branch():
    print("\n[7] Testing Failure Branch Outcome with invalid credentials...")
    payload = {
        "variables": {
            "username": "wrong_user",
            "password": "WrongPassword!"
        },
        "options": {
            "headless": True
        }
    }
    res = requests.post(
        f"{BASE_URL}/api/bots/govbridge_login_bot_01/execute",
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=30
    )
    data = res.json()
    result = data["result"]
    branch = result.get("branch_result", {})
    assert branch.get("outcome") == "failure"
    print(f"  + Failure Branch Correctly Detected: {branch['branch_name']} ({branch['subtitle']})")
    print(f"  + Failure Message: {branch['message']}")

if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING GOVBRIDGE RPA ECOSYSTEM VERIFICATION SUITE")
    print("=" * 60)
    test_pages()
    test_api_bots()
    test_payloads()
    test_extension_recording_upload()
    test_bot_execution_json()
    test_bot_execution_xml()
    test_bot_execution_failure_branch()
    print("\n" + "=" * 60)
    print("ALL 7 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)
