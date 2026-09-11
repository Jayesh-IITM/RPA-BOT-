"""
Demo Target Routes - A realistic target portal for testing Chrome Extension recording and Playwright Bot runs
"""
from flask import Blueprint, redirect, render_template, request, url_for

demo_bp = Blueprint("demo", __name__)


@demo_bp.route("/demo-target", methods=["GET", "POST"])
def demo_login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        
        # Accepted demo credentials
        if username == "gov_citizen" and password == "GovPass@2026":
            return redirect(url_for("demo.demo_dashboard", user=username))
        else:
            error = "Invalid username or password credentials provided. Please check your citizen ID."

    return render_template("demo_target.html", error=error)


@demo_bp.route("/demo-dashboard")
def demo_dashboard():
    user = request.args.get("user", "Citizen")
    return render_template("demo_dashboard.html", user=user)


@demo_bp.route("/demo-canvas")
def demo_canvas():
    return render_template("demo_canvas.html")

