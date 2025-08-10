"""Common helpers and dependencies for API routers."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from fastapi import HTTPException, Request

from backend.core.settings import WORKSPACES_ROOT
from backend.services.ai_service import AIService
from backend.services.project_service import ProjectService
from backend.sandbox import manager as sandbox_manager

# ---- Service providers ----

def get_ai_service() -> AIService:
    return AIService()


def get_project_service() -> ProjectService:
    return ProjectService()


# ---- Authentication ----

def require_auth(request: Request) -> None:  # noqa: D401
    """Dummy auth check – extend later."""
    # Authentication disabled – always allow for now.
    return None


# ---- Paths & file helpers ----

# Determine current root directory: sandbox workspace if active, else global workspaces.
def _root_dir() -> Path:
    if sandbox_manager.meta:
        try:
            return sandbox_manager._sandbox_dir()
        except Exception:
            # Fallback to workspaces if sandbox not ready
            pass
    return WORKSPACES_ROOT


def get_abs_path(rel_path: str) -> str:
    """Convert a client provided path (relative) into absolute path under WORKSPACES_ROOT.
    Raises 400 if path tries to escape workspace.
    """
    safe_path = os.path.normpath(os.path.join(_root_dir(), rel_path.strip("/")))
    root = str(_root_dir())
    if not os.path.commonpath([safe_path, root]) == root:  # prevent path traversal
        raise HTTPException(status_code=400, detail="Invalid path")
    return safe_path


def sizeof_fmt(num: float, suffix: str = "B") -> str:
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f} Y{suffix}"


def get_file_info(path: str, name: str) -> Dict[str, Any]:
    full_path = os.path.join(path, name)
    stat = os.stat(full_path)
    size = stat.st_size
    ext = os.path.splitext(name)[1].lower()
    if ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
        ftype = "image"
    elif ext in [".pdf", ".doc", ".docx", ".txt", ".ppt", ".pptx", ".xls", ".xlsx"]:
        ftype = "document"
    elif ext in [".mp4", ".avi", ".mov", ".wmv", ".mkv"]:
        ftype = "video"
    elif ext in [".mp3", ".wav", ".ogg", ".flac"]:
        ftype = "audio"
    elif ext in [".zip", ".rar", ".tar", ".gz", ".7z"]:
        ftype = "archive"
    else:
        ftype = "default"
    return {
        "name": name,
        "size": sizeof_fmt(size),
        "type": ftype,
        "modified": str(stat.st_mtime),
    }


_TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".js",
    ".json",
    ".html",
    ".css",
    ".csv",
    ".log",
    ".xml",
    ".yml",
    ".yaml",
    ".ini",
    ".conf",
}

def is_text_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in _TEXT_EXTENSIONS
