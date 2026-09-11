"""
WSGI Application Entry Point
Used by production WSGI servers: Gunicorn, Waitress, uWSGI, AWS Elastic Beanstalk, etc.
"""
import os
import sys

# Add backend directory to sys.path
backend_dir = os.path.join(os.path.dirname(__file__), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import app

# Export application for WSGI servers
application = app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")
    app.run(host=host, port=port)
