"""
GovBridge RPA Ecosystem Launcher
Starts the Flask server hosting the visual builder, REST/XML API endpoints,
and Playwright Bot Execution Engine.
"""
import sys
import os

# Ensure backend folder is in python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app import app

if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  [+] GOVBRIDGE RPA ECOSYSTEM (Flask + Playwright)")
    print("=" * 65)
    print("  * Visual Flowchart Builder: http://127.0.0.1:5000/builder")
    print("  * Demo Target Portal:       http://127.0.0.1:5000/demo-target")
    print("  * Chrome Extension Guide:   http://127.0.0.1:5000/extension-guide")
    print("=" * 65 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=False)
