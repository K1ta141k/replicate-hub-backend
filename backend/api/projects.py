import logging

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
    return {"projects": svc.list()}
