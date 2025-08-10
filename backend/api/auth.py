import logging

from fastapi import APIRouter, Body, HTTPException, Request

from backend.core.settings import settings

logger = logging.getLogger("backend")

router = APIRouter()


@router.post("/api/login")
async def login(request: Request, data: dict = Body(...)):
    pin = data.get("pin")
    if pin == settings.file_manager_pin:
        request.session["authenticated"] = True
        return {"success": True}
    raise HTTPException(status_code=401, detail="Invalid PIN")


@router.post("/api/logout")
async def logout(request: Request):
    request.session.clear()
    return {"success": True}


@router.get("/api/check-auth")
async def check_auth(request: Request):
    # Always authenticated for now
    return {"authenticated": True}
