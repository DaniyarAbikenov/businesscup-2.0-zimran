"""Vercel entry point: the FastAPI app of backend/, served as one Python function at /api/*."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app import migrate  # noqa: E402
from app.main import app  # noqa: E402,F401

migrate.run()  # only does something when AUTO_MIGRATE=true; once per cold start, never raises
