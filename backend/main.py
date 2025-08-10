"""Legacy entrypoint kept for backward compatibility.

This module now simply exposes the application defined in `backend.app`.
Run with:  uvicorn backend.app:app --reload
"""

from backend.app import app  # noqa: F401
