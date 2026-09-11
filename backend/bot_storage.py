"""
Bot Storage Module - Persistence for GovBridge RPA Bots and Recording Traces
"""
import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
BOTS_FILE = os.path.join(DATA_DIR, "bots.json")
RECORDINGS_DIR = os.path.join(DATA_DIR, "recordings")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(RECORDINGS_DIR, exist_ok=True)


def get_default_sample_bots() -> List[Dict]:
    """Returns initial seed bots, including the exact GovBridge Login flow from the wireframe."""
    return [
        {
            "id": "govbridge_login_bot_01",
            "name": "GovBridge Portal Citizen Login",
            "description": "Automated login and verification workflow matching GovBridge path trace",
            "initial_url": "http://127.0.0.1:5000/demo-target",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "variables": [
                {
                    "name": "username",
                    "default_value": "gov_citizen",
                    "type": "string",
                    "description": "Citizen username or email",
                    "required": True
                },
                {
                    "name": "password",
                    "default_value": "GovPass@2026",
                    "type": "password",
                    "description": "Portal account secret password",
                    "required": True
                }
            ],
            "steps": [
                {
                    "id": "step_1",
                    "step_number": 1,
                    "title": "Extension initiated on www.example.com",
                    "action_type": "navigate",
                    "target_description": "Initial portal webpage",
                    "selector": "",
                    "fallback_selectors": [],
                    "value_mode": "fixed",
                    "value": "http://127.0.0.1:5000/demo-target",
                    "variable_name": "",
                    "wait_before_ms": 200,
                    "wait_after_ms": 500,
                    "timeout_ms": 15000,
                    "optional": False,
                    "highlight": True
                },
                {
                    "id": "step_2",
                    "step_number": 2,
                    "title": "Input in Username field",
                    "action_type": "type",
                    "target_description": "Username field",
                    "selector": "#username",
                    "fallback_selectors": [
                        "input[name='username']",
                        "input[placeholder='Enter Username or Email']",
                        "//input[@id='username']"
                    ],
                    "value_mode": "variable",
                    "value": "gov_citizen",
                    "variable_name": "username",
                    "wait_before_ms": 300,
                    "wait_after_ms": 300,
                    "timeout_ms": 10000,
                    "optional": False,
                    "highlight": True
                },
                {
                    "id": "step_3",
                    "step_number": 3,
                    "title": "Input in Password field",
                    "action_type": "type",
                    "target_description": "Password field",
                    "selector": "#password",
                    "fallback_selectors": [
                        "input[name='password']",
                        "input[type='password']",
                        "//input[@id='password']"
                    ],
                    "value_mode": "variable",
                    "value": "GovPass@2026",
                    "variable_name": "password",
                    "wait_before_ms": 300,
                    "wait_after_ms": 300,
                    "timeout_ms": 10000,
                    "optional": False,
                    "highlight": True
                },
                {
                    "id": "step_4",
                    "step_number": 4,
                    "title": "Submit Button",
                    "action_type": "click",
                    "target_description": "Login Submit Button",
                    "selector": "#submit-btn",
                    "fallback_selectors": [
                        "button[type='submit']",
                        "button:has-text('Sign In')",
                        "//button[@id='submit-btn']"
                    ],
                    "value_mode": "fixed",
                    "value": "",
                    "variable_name": "",
                    "wait_before_ms": 300,
                    "wait_after_ms": 1200,
                    "timeout_ms": 10000,
                    "optional": False,
                    "highlight": True
                }
            ],
            "branching": {
                "enabled": True,
                "check_type": "url_or_element",
                "failure_selector": "#error-message",
                "success_url_contains": "/demo-dashboard",
                "success_selector": "#dashboard-header",
                "failure_branch": {
                    "title": "Login Failed return error",
                    "subtitle": "End of the RPA BOT task",
                    "outcome": "error",
                    "message": "Invalid username or password credentials provided.",
                    "status_code": 401
                },
                "success_branch": {
                    "title": "Login Successful",
                    "subtitle": "End of the RPA BOT task",
                    "outcome": "success",
                    "message": "Citizen logged in successfully. Dashboard session established.",
                    "status_code": 200
                }
            }
        },
        {
            "id": "ecommerce_search_bot_02",
            "name": "E-Commerce Product Search & Price Check",
            "description": "Automated catalog search with dynamic query parameter and price screenshot",
            "initial_url": "http://127.0.0.1:5000/demo-target",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "variables": [
                {
                    "name": "search_query",
                    "default_value": "Passport Renewal Service",
                    "type": "string",
                    "description": "Service name to search",
                    "required": True
                }
            ],
            "steps": [
                {
                    "id": "step_1",
                    "step_number": 1,
                    "title": "Extension initiated on Portal Services",
                    "action_type": "navigate",
                    "target_description": "Initial URL",
                    "selector": "",
                    "fallback_selectors": [],
                    "value_mode": "fixed",
                    "value": "http://127.0.0.1:5000/demo-target",
                    "variable_name": "",
                    "wait_before_ms": 200,
                    "wait_after_ms": 500,
                    "timeout_ms": 15000,
                    "optional": False,
                    "highlight": True
                },
                {
                    "id": "step_2",
                    "step_number": 2,
                    "title": "Search Query Input",
                    "action_type": "type",
                    "target_description": "Search input box",
                    "selector": "#search-input",
                    "fallback_selectors": ["input[type='search']", "#search"],
                    "value_mode": "variable",
                    "value": "Passport Renewal Service",
                    "variable_name": "search_query",
                    "wait_before_ms": 200,
                    "wait_after_ms": 300,
                    "timeout_ms": 10000,
                    "optional": True,
                    "highlight": True
                }
            ],
            "branching": {
                "enabled": False
            }
        }
    ]


class BotStorage:
    def __init__(self, bots_file: str = BOTS_FILE):
        self.bots_file = bots_file
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.bots_file):
            default_bots = get_default_sample_bots()
            self._save_all(default_bots)

    def _load_all(self) -> List[Dict]:
        try:
            with open(self.bots_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return get_default_sample_bots()

    def _save_all(self, bots: List[Dict]):
        with open(self.bots_file, "w", encoding="utf-8") as f:
            json.dump(bots, f, indent=2, ensure_ascii=False)

    def list_bots(self) -> List[Dict]:
        return self._load_all()

    def get_bot(self, bot_id: str) -> Optional[Dict]:
        bots = self._load_all()
        for b in bots:
            if b.get("id") == bot_id:
                return b
        return None

    def save_bot(self, bot_data: Dict) -> Dict:
        bots = self._load_all()
        bot_id = bot_data.get("id")
        now = datetime.now().isoformat()
        
        if not bot_id:
            bot_id = f"bot_{uuid.uuid4().hex[:8]}"
            bot_data["id"] = bot_id
            bot_data["created_at"] = now
            bot_data["updated_at"] = now
            bots.append(bot_data)
        else:
            found = False
            for i, existing in enumerate(bots):
                if existing.get("id") == bot_id:
                    bot_data["updated_at"] = now
                    if "created_at" not in bot_data:
                        bot_data["created_at"] = existing.get("created_at", now)
                    bots[i] = bot_data
                    found = True
                    break
            if not found:
                bot_data["created_at"] = now
                bot_data["updated_at"] = now
                bots.append(bot_data)
                
        self._save_all(bots)
        return bot_data

    def delete_bot(self, bot_id: str) -> bool:
        bots = self._load_all()
        new_bots = [b for b in bots if b.get("id") != bot_id]
        if len(new_bots) != len(bots):
            self._save_all(new_bots)
            return True
        return False

    # Recording sessions
    def save_recording(self, recording_data: Dict) -> str:
        rec_id = recording_data.get("recording_id") or f"rec_{uuid.uuid4().hex[:10]}"
        recording_data["recording_id"] = rec_id
        recording_data["saved_at"] = datetime.now().isoformat()
        filepath = os.path.join(RECORDINGS_DIR, f"{rec_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(recording_data, f, indent=2, ensure_ascii=False)
        return rec_id

    def get_recording(self, rec_id: str) -> Optional[Dict]:
        filepath = os.path.join(RECORDINGS_DIR, f"{rec_id}.json")
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return None


storage = BotStorage()
