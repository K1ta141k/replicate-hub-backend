import logging
import os
import zipfile
from typing import List, Dict

from fastapi import APIRouter, Body, File as UploadFileType, UploadFile, Form, HTTPException, Request
from fastapi.responses import FileResponse

from backend.api.deps import (
    require_auth,
    get_abs_path,
    get_file_info,
    is_text_file,
)

logger = logging.getLogger("backend")

router = APIRouter()

# ---------- File Manager Endpoints ---------- #


@router.get("/api/list")
async def list_files(request: Request, path: str = "/"):
    require_auth(request)
    abs_path = get_abs_path(path)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Path does not exist")
    files: List[Dict[str, str]] = []
    folders: List[Dict[str, str]] = []
    for entry in os.listdir(abs_path):
        full_entry = os.path.join(abs_path, entry)
        if os.path.isdir(full_entry):
            folders.append({"name": entry, "path": os.path.join(path, entry).replace("\\", "/")})
        else:
            files.append(get_file_info(abs_path, entry))
    return {"files": files, "folders": folders}


@router.post("/api/upload")
async def upload_file(
    request: Request,
    file: UploadFile = UploadFileType(...),
    path: str = Form("/"),
):
    require_auth(request)
    abs_path = get_abs_path(path)
    os.makedirs(abs_path, exist_ok=True)
    filename = os.path.basename(file.filename)
    dest = os.path.join(abs_path, filename)
    with open(dest, "wb") as f:
        f.write(await file.read())
    return {"success": True}


@router.get("/api/download")
async def download_file(request: Request, path: str):
    require_auth(request)
    abs_path = get_abs_path(path)
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(abs_path, filename=os.path.basename(abs_path))


@router.post("/api/rename")
async def rename_file(request: Request, data: dict = Body(...)):
    require_auth(request)
    rel_path = data.get("path")
    new_name = data.get("newName")
    abs_path = get_abs_path(rel_path)
    new_abs_path = os.path.join(os.path.dirname(abs_path), os.path.basename(new_name))
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="File/folder not found")
    os.rename(abs_path, new_abs_path)
    return {"success": True}


@router.post("/api/delete")
async def delete_file_route(request: Request, data: dict = Body(...)):
    require_auth(request)
    rel_path = data.get("path")
    abs_path = get_abs_path(rel_path)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="File/folder not found")
    if os.path.isdir(abs_path):
        try:
            os.rmdir(abs_path)
        except OSError:
            raise HTTPException(status_code=400, detail="Directory not empty")
    else:
        os.remove(abs_path)
    return {"success": True}


@router.get("/api/read")
async def read_file_route(request: Request, path: str):
    require_auth(request)
    abs_path = get_abs_path(path)
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="File not found")
    if not is_text_file(abs_path):
        raise HTTPException(status_code=400, detail="Not a text file")
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/save")
async def save_file_route(request: Request, data: dict = Body(...)):
    require_auth(request)
    rel_path = data.get("path")
    content = data.get("content")
    abs_path = get_abs_path(rel_path)
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="File not found")
    if not is_text_file(abs_path):
        raise HTTPException(status_code=400, detail="Not a text file")
    try:
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/unzip")
async def unzip_file_route(request: Request, data: dict = Body(...)):
    require_auth(request)
    rel_path = data.get("path")
    abs_path = get_abs_path(rel_path)
    if not os.path.isfile(abs_path) or not abs_path.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Not a zip file")
    try:
        extract_dir = abs_path + "_unzipped"
        with zipfile.ZipFile(abs_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)
        return {"success": True, "extracted_to": extract_dir}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Create New File ---------- #


@router.post("/api/create-file")
async def create_file_route(request: Request, data: dict = Body(...)):
    """Create a new empty text file (or with provided content)."""
    require_auth(request)
    rel_path = data.get("path")
    content = data.get("content", "")
    if not rel_path or rel_path.endswith("/"):
        raise HTTPException(status_code=400, detail="Invalid file path")
    abs_path = get_abs_path(rel_path)
    if os.path.exists(abs_path):
        raise HTTPException(status_code=400, detail="File already exists")
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    try:
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))
