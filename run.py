"""Application entry point.

Usage:
    python run.py                  # development server
    FLASK_ENV=production python run.py
"""
import os
from app import create_app

env = os.getenv("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1000, debug=(env == "development"))
