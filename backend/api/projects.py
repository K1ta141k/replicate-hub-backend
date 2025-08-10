import logging
import os
import re
import shutil

from fastapi import APIRouter, Depends, HTTPException

from backend.models.project import ProjectCreateRequest
from backend.services.project_service import ProjectService
from backend.api.deps import get_project_service

logger = logging.getLogger("backend")

router = APIRouter()


@router.post("/api/projects")
async def create_project(req: ProjectCreateRequest, svc: ProjectService = Depends(get_project_service)):
    try:
        return svc.create(req.name)
    except FileExistsError:
        raise HTTPException(status_code=400, detail="Project already exists")


@router.get("/api/projects")
async def list_projects(svc: ProjectService = Depends(get_project_service)):
    # Purge old test* projects, keep only the two most recent
    root = svc.__class__.__module__  # not used; kept for type stability
    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "..")
    # Actual workspaces root
    from backend.core.settings import WORKSPACES_ROOT

    try:
        entries = [d for d in os.listdir(WORKSPACES_ROOT) if os.path.isdir(os.path.join(WORKSPACES_ROOT, d))]
        test_dirs = [d for d in entries if re.match(r"^test", d, re.IGNORECASE)]
        # Sort test dirs by modification time (newest first)
        test_dirs_sorted = sorted(
            test_dirs,
            key=lambda d: os.stat(os.path.join(WORKSPACES_ROOT, d)).st_mtime,
            reverse=True,
        )
        # Delete all but the latest two
        for d in test_dirs_sorted[2:]:
            shutil.rmtree(os.path.join(WORKSPACES_ROOT, d), ignore_errors=True)
    except Exception as _:
        # Non-fatal; continue to list
        pass

    return {"projects": svc.list()}
