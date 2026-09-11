"""
Test Suite for Smart Canvas Gesture Mapping & Resilient Bot Execution Engine
Verifies:
1. Volatile ID detection & filter logic
2. Ingestion of canvas_draw and canvas_click actions into bot workflows
3. Live Playwright execution of canvas_draw (rectangle tracing) on HTML5 canvas
4. Live Playwright execution of precision canvas_click
5. Resilient click handling with pointer-interception and dynamic IDs
"""
import json
import os
import sys
import time
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

BASE_URL = "http://127.0.0.1:5000"

def test_recording_ingestion_canvas():
    print("\n[1] Testing Recording Ingestion of Canvas Gestures...")
    sample_trace = {
        "initial_url": f"{BASE_URL}/demo-canvas",
        "name": "Canvas Rectangle Drawing Bot",
        "actions": [
            {
                "type": "canvas_draw",
                "action_type": "canvas_draw",
                "selector": "#drawing-board",
                "fallbacks": ["canvas", "//canvas"],
                "target_name": "Draw on Canvas (20%, 25% → 60%, 70%)",
                "shape_hint": "rectangle",
                "start_x": 136,
                "start_y": 95,
                "end_x": 408,
                "end_y": 266,
                "start_percent_x": 0.2,
                "start_percent_y": 0.25,
                "end_percent_x": 0.6,
                "end_percent_y": 0.7
            },
            {
                "type": "canvas_click",
                "action_type": "canvas_click",
                "selector": "#drawing-board",
                "fallbacks": ["canvas"],
                "target_name": "Canvas Point (80%, 80%)",
                "offset_x": 544,
                "offset_y": 304,
                "percent_x": 0.8,
                "percent_y": 0.8
            },
            {
                "type": "click",
                "selector": "[data-testid=\"smart-export-btn\"]",
                "fallbacks": ["#radix-:r5:", "button:has-text('Export Canvas Drawing')"],
                "target_name": "Export Canvas Drawing",
                "text": "Export Canvas Drawing\nCtrl+E"
            }
        ]
    }

    res = requests.post(f"{BASE_URL}/api/recordings", json=sample_trace)
    assert res.status_code == 201, f"Failed ingestion: {res.text}"
    data = res.json()
    bot_id = data["bot_id"]
    print(f"  + Recording successfully transformed into Bot ID: {bot_id}")

    # Fetch created bot
    bot_res = requests.get(f"{BASE_URL}/api/bots/{bot_id}")
    assert bot_res.status_code == 200
    bot = bot_res.json()["bot"]
    steps = bot["steps"]
    
    assert len(steps) == 4, f"Expected 4 steps, got {len(steps)}"
    assert steps[0]["action_type"] == "navigate"
    assert steps[1]["action_type"] == "canvas_draw"
    assert steps[1]["start_percent_x"] == 0.2
    assert steps[1]["end_percent_x"] == 0.6
    assert steps[2]["action_type"] == "canvas_click"
    assert steps[2]["percent_x"] == 0.8
    assert steps[3]["action_type"] == "click"
    assert "Ctrl" not in steps[3]["title"], "Hotkey text should be stripped from title"
    print("  + Workflow steps validated: navigate -> canvas_draw -> canvas_click -> click")
    return bot_id


def test_smart_execution_live(bot_id):
    print("\n[2] Testing Live Bot Execution of Canvas Drawing & Resilient Click...")
    exec_res = requests.post(
        f"{BASE_URL}/api/bots/{bot_id}/execute",
        json={
            "options": {
                "headless": True,
                "take_screenshots": True
            }
        },
        timeout=30
    )
    assert exec_res.status_code == 200, f"Execution request failed: {exec_res.text}"
    exec_data = exec_res.json()["result"]
    assert exec_data["status"] == "success", f"Bot execution failed: {exec_data}"
    
    step_results = exec_data["step_results"]
    for r in step_results:
        print(f"  + Step {r['step_number']} ({r['title']}): {r['status'].upper()} in {r['duration_ms']}ms -> {r['details']}")
        assert r["status"] == "success", f"Step {r['step_number']} failed: {r}"

    print(f"  + Total Execution Duration: {exec_data['total_duration_sec']}s")


def test_canvas_interaction_browser_validation():
    print("\n[3] Validating Canvas & Overlay Resilience Directly in Playwright...")
    from bot_engine import BotExecutionEngine

    test_bot_data = {
        "id": "bot_test_canvas_direct",
        "name": "Direct Canvas Verification",
        "steps": [
            {
                "step_number": 1,
                "title": "Open Canvas Testbed",
                "action_type": "navigate",
                "value": f"{BASE_URL}/demo-canvas",
                "timeout_ms": 10000
            },
            {
                "step_number": 2,
                "title": "Draw Rectangle on Canvas",
                "action_type": "canvas_draw",
                "selector": "#drawing-board",
                "fallback_selectors": ["canvas"],
                "start_percent_x": 0.15,
                "start_percent_y": 0.2,
                "end_percent_x": 0.7,
                "end_percent_y": 0.75,
                "timeout_ms": 10000
            },
            {
                "step_number": 3,
                "title": "Click Canvas Point",
                "action_type": "canvas_click",
                "selector": "#drawing-board",
                "fallback_selectors": ["canvas"],
                "percent_x": 0.85,
                "percent_y": 0.85,
                "timeout_ms": 10000
            },
            {
                "step_number": 4,
                "title": "Click Obscured Export Button",
                "action_type": "click",
                # Pass only the volatile ID as primary, and text as fallback, with intercepting banner overlaying it
                "selector": "#radix-:r5:",
                "fallback_selectors": ["[data-testid='smart-export-btn']"],
                "target_description": "Export Canvas Drawing Button",
                "text": "Export Canvas Drawing",
                "timeout_ms": 10000
            }
        ]
    }

    engine = BotExecutionEngine(bot_data=test_bot_data, options={"headless": True})
    result = engine.execute()
    assert result["status"] == "success", f"Engine failed: {result}"
    print("  + Engine successfully traced rectangle, clicked canvas point, and bypassed overlay interception!")


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING SMART CANVAS & RESILIENT BOT ENGINE TESTS")
    print("=" * 60)
    bot_id = test_recording_ingestion_canvas()
    test_smart_execution_live(bot_id)
    test_canvas_interaction_browser_validation()
    print("\n" + "=" * 60)
    print("ALL SMART ENGINE TESTS PASSED!")
    print("=" * 60)
