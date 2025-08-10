import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import shutil
from .sandbox import manager as sandbox_manager

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACES_ROOT = REPO_ROOT / "workspaces"
WORKSPACES_ROOT.mkdir(exist_ok=True)

# ------------- helpers -------------

def _workspace_path(rel: str) -> Path:
    rel = rel.lstrip("/\\")
    base = sandbox_manager._sandbox_dir() if sandbox_manager.meta else WORKSPACES_ROOT / "_unspecified"
    return base / rel

# ------------- tool implementations -------------

def write_file(path: str, content: str) -> Dict[str, Any]:
    p = _workspace_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    if sandbox_manager.meta:
        sandbox_manager.write_file_and_cache(path, content)
    return {"result": "written", "path": path}


def append_file(path: str, content: str) -> Dict[str, Any]:
    p = _workspace_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(content)
    sandbox_manager.write_file_and_cache(path, p.read_text())
    return {"result": "appended", "path": path}


def read_file(path: str) -> Dict[str, Any]:
    p = _workspace_path(path)
    if not p.exists():
        return {"error": "not found"}
    return {"content": p.read_text(errors="ignore")}


def delete_file(path: str) -> Dict[str, Any]:
    p = _workspace_path(path)
    if not p.exists():
        return {"error": "not found"}
    p.unlink()
    if sandbox_manager.meta and path in sandbox_manager.cache:
        del sandbox_manager.cache[path]
    return {"result": "deleted", "path": path}


def rename_file(path: str, new_name: str) -> Dict[str, Any]:
    p = _workspace_path(path)
    if not p.exists():
        return {"error": "not found"}
    new_path = p.parent / new_name
    p.rename(new_path)
    if sandbox_manager.meta and path in sandbox_manager.cache:
        sandbox_manager.cache[new_name] = sandbox_manager.cache.pop(path)
    return {"result": "renamed", "old": path, "new": str(new_path)}


def list_files(dir: str = "") -> Dict[str, Any]:
    d = _workspace_path(dir)
    if not d.is_dir():
        return {"error": "dir not found"}
    return {"files": [f.name for f in d.iterdir() if f.is_file()]}


def start_dev() -> Dict[str, Any]:
    sandbox_manager.start_dev()
    return {"result": "started", "url": sandbox_manager.meta.get("url")}


def stop_dev() -> Dict[str, Any]:
    sandbox_manager.kill()
    return {"result": "stopped"}

# ------------- registry -------------

TOOLS_REGISTRY = {
    "write_file": write_file,
    "append_file": append_file,
    "read_file": read_file,
    "delete_file": delete_file,
    "rename_file": rename_file,
    "list_files": list_files,
    "start_dev": start_dev,
    "stop_dev": stop_dev,
}

_TOOL_DESCRIPTIONS = {
    "write_file": "Create or overwrite a text file at given path.",
    "append_file": "Append content to the end of a text file.",
    "read_file": "Read a text file and return its content.",
    "delete_file": "Delete a file at given path.",
    "rename_file": "Rename a file.",
    "list_files": "List files in a directory.",
    "start_dev": "Start the dev server for current project.",
    "stop_dev": "Stop the dev server.",
}


def build_function_schemas() -> List[Dict[str, Any]]:
    schemas = []
    for name in TOOLS_REGISTRY.keys():
        if name in ["write_file", "append_file"]:
            params = {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            }
        elif name in ["read_file", "delete_file", "start_dev", "stop_dev"]:
            params = {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": [],
            }
        elif name == "rename_file":
            params = {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "new_name": {"type": "string"},
                },
                "required": ["path", "new_name"],
            }
        elif name == "list_files":
            params = {
                "type": "object",
                "properties": {"dir": {"type": "string"}},
                "required": [],
            }
        else:
            params = {"type": "object", "properties": {}}
        schemas.append({
            "name": name,
            "description": _TOOL_DESCRIPTIONS.get(name, ""),
            "parameters": params,
        })
    return schemas
