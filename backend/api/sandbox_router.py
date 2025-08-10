import logging
from typing import List, Dict

from fastapi import APIRouter, Body, HTTPException

from backend.sandbox import manager as sandbox_manager

logger = logging.getLogger("backend")

router = APIRouter()


@router.post("/api/sandbox/init")
async def sandbox_init(data: dict = Body(...)):
    project = data.get("project")
    if not project:
        raise HTTPException(status_code=400, detail="Missing project name")
    timeout_ms = data.get("timeoutMs", 5 * 60_000)
    api_key = data.get("apiKey")
    meta = sandbox_manager.init(project_name=project, api_key=api_key, timeout_ms=timeout_ms)
    return meta


@router.post("/api/sandbox/start")
async def sandbox_start(data: dict = Body(...)):
    project = data.get("project")
    if not project:
        raise HTTPException(status_code=400, detail="Missing project name")
    if not sandbox_manager.meta or sandbox_manager.meta.get("sandboxId") != project:
        raise HTTPException(status_code=400, detail="Sandbox not initialised for this project")
    meta = sandbox_manager.start_dev()
    return meta


@router.post("/api/sandbox/create")
async def sandbox_create(data: dict = Body(...)):
    project = data.get("project")
    if not project:
        raise HTTPException(status_code=400, detail="Missing project name")
    timeout_ms = data.get("timeoutMs", 5 * 60_000)
    api_key = data.get("apiKey")
    meta = sandbox_manager.create(project_name=project, api_key=api_key, timeout_ms=timeout_ms)
    return meta


@router.post("/api/sandbox/apply-code")
async def sandbox_apply_code(data: dict = Body(...)):
    if not sandbox_manager.is_active():
        raise HTTPException(status_code=400, detail="No active sandbox. Create first.")
    response_text = data.get("response")  # noqa: F841 – kept for future use
    files: List[Dict[str, str]] = data.get("files", [])
    logger.info("apply-code received %s files", len(files))
    try:
        import json as _json
        logger.debug("files payload:\n%s", _json.dumps(files, indent=2)[:2000])
    except Exception:
        pass
    files_created, files_updated = 0, 0
    for f in files:
        rel = f.get("path")
        content = f.get("content", "")
        if rel in sandbox_manager.cache:
            files_updated += 1
        else:
            files_created += 1
        sandbox_manager.write_file_and_cache(rel, content)
    return {"filesCreated": files_created, "filesUpdated": files_updated}


@router.get("/api/sandbox/files")
async def sandbox_files():
    if not sandbox_manager.is_active():
        raise HTTPException(status_code=400, detail="No active sandbox")
    return sandbox_manager.read_files()


@router.post("/api/sandbox/kill")
async def sandbox_kill():
    if sandbox_manager.is_active():
        sandbox_manager.kill()
    return {"success": True}


# ---------- Command Exec ---------- #


@router.post("/api/sandbox/exec")
async def sandbox_exec(data: dict = Body(...)):
    cmd = data.get("cmd")
    if not cmd:
        raise HTTPException(status_code=400, detail="Missing cmd")
    if not sandbox_manager.meta:
        raise HTTPException(status_code=400, detail="Sandbox not initialised")
    result = sandbox_manager.run_command(cmd)
    return result
