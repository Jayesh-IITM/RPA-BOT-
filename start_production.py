"""
MahaSetu RPA Ecosystem - Production Server Launcher
Auto-detects environment and launches with production-grade WSGI server:
- Waitress on Windows Server / cross-platform
- Gunicorn or Waitress on Linux / Cloud / Docker
"""
import os
import sys

# Ensure backend directory is in path
backend_dir = os.path.join(os.path.dirname(__file__), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv()

from app import app

def run_production():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    threads = int(os.getenv("WSGI_THREADS", 8))
    is_windows = sys.platform.startswith("win")

    print("\n" + "=" * 65)
    print("  [+] MAHASETU RPA ECOSYSTEM - PRODUCTION SERVER")
    print("=" * 65)
    print(f"  * Mode:                Production WSGI")
    print(f"  * Host / Port:         http://{host}:{port}")
    print(f"  * Visual Builder:      http://{host}:{port}/builder")
    print(f"  * Health API:          http://{host}:{port}/api/health")
    print(f"  * Extension Guide:     http://{host}:{port}/extension-guide")
    print(f"  * Extension Download:  http://{host}:{port}/api/extension/download")
    print(f"  * Demo Target Portal:  http://{host}:{port}/demo-target")
    print("=" * 65)

    if is_windows:
        print(f"  -> Serving via Waitress WSGI Server ({threads} worker threads)...\n")
        try:
            from waitress import serve
            serve(app, host=host, port=port, threads=threads)
        except ImportError:
            print("[!] Waitress not found. Falling back to default server.")
            app.run(host=host, port=port, debug=False)
    else:
        # On Linux / Cloud
        try:
            print(f"  -> Serving via Waitress WSGI Server ({threads} worker threads)...\n")
            from waitress import serve
            serve(app, host=host, port=port, threads=threads)
        except ImportError:
            print(f"  -> Serving via standard app runner...\n")
            app.run(host=host, port=port, debug=False)

if __name__ == "__main__":
    run_production()
