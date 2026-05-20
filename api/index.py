"""
Vercel serverless entry — wraps FastAPI app from backend/main.py.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import app  # noqa: E402
