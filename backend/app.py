"""
Main Flask Application Server for MahaSetu RPA Ecosystem
Provides production-ready configuration, security headers, health checks,
and web view routing.
"""
import os
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for, send_from_directory, jsonify
from flask_cors import CORS

# Load environment variables from .env if present
load_dotenv()

from api_routes import api_bp
from demo_routes import demo_bp
from bot_storage import storage

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

# App secret key for session / CSRF security
app.secret_key = os.getenv("SECRET_KEY", "mahasetu-rpa-secret-key-production-2026")

# Configure CORS for Chrome Extension requests and external webhook calls
cors_origins_env = os.getenv("CORS_ORIGINS", "*")
if cors_origins_env == "*":
    cors_origins = "*"
else:
    cors_origins = [orig.strip() for orig in cors_origins_env.split(",") if orig.strip()]

CORS(app, resources={r"/*": {"origins": cors_origins}})

# Register blueprints
app.register_blueprint(api_bp, url_prefix="/api")
app.register_blueprint(demo_bp)


# --------------------------------------------------------------------------
# Production Security Headers Middleware
# --------------------------------------------------------------------------

@app.after_request
def apply_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Allow embedding only for demo target / testing iframe contexts
    if not request.path.startswith("/demo-"):
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
    return response


# --------------------------------------------------------------------------
# Root Health Route (For load balancers / cloud health probes)
# --------------------------------------------------------------------------

@app.route("/health")
def root_health():
    """Direct root health check alias for cloud platforms (Render, Railway, Kubernetes)"""
    return redirect(url_for("api.health_check"))


# --------------------------------------------------------------------------
# Web Portal Views
# --------------------------------------------------------------------------

@app.route("/")
def index():
    """Redirect home route directly to Visual Workflow Builder"""
    return redirect(url_for("builder"))


@app.route("/builder")
def builder():
    """Visual Workflow Canvas matching the wireframe"""
    bot_id = request.args.get("bot_id")
    bot = None
    if bot_id:
        bot = storage.get_bot(bot_id)
    if not bot:
        # Default to the seed login bot
        bots = storage.list_bots()
        bot = bots[0] if bots else None

    return render_template("builder.html", bot=bot)


@app.route("/extension-guide")
def extension_guide():
    """Chrome Extension installation and distribution guide"""
    return render_template("extension_guide.html")


@app.route("/extension/<path:filename>")
def serve_extension_file(filename):
    """Serve extension assets for testing or in-browser preview"""
    ext_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "extension"))
    return send_from_directory(ext_dir, filename)


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    print("=" * 60)
    print(f" MahaSetu RPA Bot Server Starting on http://{host}:{port}")
    print(f" * Visual Builder:     http://{host}:{port}/builder")
    print(f" * Health Check:       http://{host}:{port}/api/health")
    print(f" * Demo Target Portal: http://{host}:{port}/demo-target")
    print("=" * 60)
    app.run(host=host, port=port, debug=debug)
