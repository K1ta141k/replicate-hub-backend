from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException, Depends, Body
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from dotenv import load_dotenv
import os
import zipfile
import logging
from typing import Optional
from .ai_providers import call_llm, AIProviderError
from .tools import TOOLS_REGISTRY
import json

load_dotenv()  # Load variables from .env file

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("backend")

app = FastAPI()

# Logging middleware (after app is defined)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"{request.method} {request.url.path}")
    try:
        response = await call_next(request)
        logger.info(f"Completed with status {response.status_code}")
        return response
    except Exception as exc:
        logger.exception("Unhandled error:")
        raise exc

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session support
SECRET_KEY = os.environ.get("SECRET_KEY", "piskachort")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Root dir for projects & file manager
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, os.pardir))
WORKSPACES_ROOT = os.path.join(REPO_ROOT, "workspaces")
ROOT_DIR = WORKSPACES_ROOT  # File-manager root
os.makedirs(ROOT_DIR, exist_ok=True)

PIN_CODE = os.environ.get("FILE_MANAGER_PIN", "1234")

# ---------- Helper functions ---------- #

def require_auth(request: Request):
    # Authentication disabled – always allow
    return


def get_abs_path(rel_path: str) -> str:
    safe_path = os.path.normpath(os.path.join(ROOT_DIR, rel_path.strip("/")))
    if not safe_path.startswith(ROOT_DIR):
        raise HTTPException(status_code=400, detail="Invalid path")
    return safe_path


def sizeof_fmt(num, suffix="B"):
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f} Y{suffix}"


def get_file_info(path: str, name: str):
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


def is_text_file(filename: str):
    ext = os.path.splitext(filename)[1].lower()
    return ext in [
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
    ]

# ---------- Auth Endpoints ---------- #

@app.post("/api/login")
async def login(request: Request, data: dict):
    pin = data.get("pin")
    if pin == PIN_CODE:
        request.session["authenticated"] = True
        return {"success": True}
    raise HTTPException(status_code=401, detail="Invalid PIN")

@app.post("/api/logout")
async def logout(request: Request):
    request.session.clear()
    return {"success": True}

@app.get("/api/check-auth")
async def check_auth(request: Request):
    # Always authenticated
    return {"authenticated": True}

# ---------- Project Management ---------- #

@app.post("/api/projects")
async def create_project(
    data: dict = Body(...)  # Accept any JSON body
):
    project_name = data.get("name")
    if not project_name:
        raise HTTPException(status_code=400, detail="Missing project name")
    safe_name = os.path.basename(project_name)
    project_path = os.path.join(WORKSPACES_ROOT, safe_name)
    logger.info(f"Creating project: {project_name}")
    try:
        os.makedirs(project_path, exist_ok=False)
    except FileExistsError:
        raise HTTPException(status_code=400, detail="Project already exists")
    return JSONResponse({"success": True, "path": f"/{safe_name}"}, status_code=201)

@app.get("/api/projects")
async def list_projects():
    projects = [d for d in os.listdir(WORKSPACES_ROOT) if os.path.isdir(os.path.join(WORKSPACES_ROOT, d))]
    return {"projects": projects}

# ---------- File Manager Endpoints ---------- #

@app.get("/api/list")
async def list_files(request: Request, path: str = "/"):
    require_auth(request)
    abs_path = get_abs_path(path)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Path does not exist")
    files, folders = [], []
    for entry in os.listdir(abs_path):
        full_entry = os.path.join(abs_path, entry)
        if os.path.isdir(full_entry):
            folders.append({"name": entry, "path": os.path.join(path, entry).replace("\\", "/")})
        else:
            files.append(get_file_info(abs_path, entry))
    return {"files": files, "folders": folders}

@app.post("/api/upload")
async def upload_file(request: Request, file: UploadFile = File(...), path: str = Form("/")):
    require_auth(request)
    abs_path = get_abs_path(path)
    os.makedirs(abs_path, exist_ok=True)
    filename = os.path.basename(file.filename)
    dest = os.path.join(abs_path, filename)
    with open(dest, "wb") as f:
        f.write(await file.read())
    return {"success": True}

@app.get("/api/download")
async def download_file(request: Request, path: str):
    require_auth(request)
    abs_path = get_abs_path(path)
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(abs_path, filename=os.path.basename(abs_path))

@app.post("/api/rename")
async def rename_file(request: Request, data: dict):
    require_auth(request)
    rel_path = data.get("path")
    new_name = data.get("newName")
    abs_path = get_abs_path(rel_path)
    new_abs_path = os.path.join(os.path.dirname(abs_path), os.path.basename(new_name))
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="File/folder not found")
    os.rename(abs_path, new_abs_path)
    return {"success": True}

@app.post("/api/delete")
async def delete_file(request: Request, data: dict):
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

@app.get("/api/read")
async def read_file(request: Request, path: str):
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/save")
async def save_file(request: Request, data: dict):
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/unzip")
async def unzip_file(request: Request, data: dict):
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Create New File ---------- #

@app.post("/api/create-file")
async def create_file(request: Request, data: dict):
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Sandbox Endpoints ---------- #

from .sandbox import manager as sandbox_manager

@app.post("/api/sandbox/init")
async def sandbox_init(data: dict = Body(...)):
    project = data.get("project")
    if not project:
        raise HTTPException(status_code=400, detail="Missing project name")
    timeout_ms = data.get("timeoutMs", 5 * 60_000)
    api_key = data.get("apiKey")
    meta = sandbox_manager.init(project_name=project, api_key=api_key, timeout_ms=timeout_ms)
    return meta

@app.post("/api/sandbox/start")
async def sandbox_start(data: dict = Body(...)):
    project = data.get("project")
    if not project:
        raise HTTPException(status_code=400, detail="Missing project name")
    if not sandbox_manager.meta or sandbox_manager.meta.get("sandboxId") != project:
        raise HTTPException(status_code=400, detail="Sandbox not initialised for this project")
    meta = sandbox_manager.start_dev()
    return meta

@app.post("/api/sandbox/create")
async def sandbox_create(data: dict = Body(...)):
    project = data.get("project")
    if not project:
        raise HTTPException(status_code=400, detail="Missing project name")
    timeout_ms = data.get("timeoutMs", 5 * 60_000)
    api_key = data.get("apiKey")
    meta = sandbox_manager.create(project_name=project, api_key=api_key, timeout_ms=timeout_ms)
    return meta

# removed obsolete sync-project endpoint


@app.post("/api/sandbox/apply-code")
async def sandbox_apply_code(data: dict = Body(...)):
    if not sandbox_manager.is_active():
        raise HTTPException(status_code=400, detail="No active sandbox. Create first.")
    response_text = data.get("response")
    files: list[dict[str, str]] = data.get("files", [])
    # For now assume 'files' is list of { path, content }
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


@app.get("/api/sandbox/files")
async def sandbox_files():
    if not sandbox_manager.is_active():
        raise HTTPException(status_code=400, detail="No active sandbox")
    return sandbox_manager.read_files()


@app.post("/api/sandbox/kill")
async def sandbox_kill():
    if sandbox_manager.is_active():
        sandbox_manager.kill()
    return {"success": True}


# ---------- AI Chat Endpoint ---------- #

@app.post("/api/ai/chat")
async def ai_chat(data: dict = Body(...)):
    messages = data.get("messages", [])
    model_choice = data.get("model", "kimi2")
    project = data.get("project") or "scratch"

    provider_map = {
        "kimi2": ("groq", "llama3-70b-8192"),
        "gpt5": ("openai", "gpt-5"),
        "claude": ("anthropic", "claude-3-opus-20240229"),
    }
    provider, model_id = provider_map.get(model_choice, provider_map["kimi2"])

    # ensure workspace exists for project
    sandbox_manager.init(project_name=project)

    function_schemas = sandbox_manager.build_function_schemas()

    try:
        resp = call_llm(provider, model_id, messages, function_schemas)
    except AIProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # handle potential tool call loop
    iterations = 0
    while True:
        iterations += 1
        if iterations > 5:
            break
        choice = resp["choices"][0]
        if choice.get("finish_reason") == "stop":
            break
        if "message" in choice and choice["message"].get("function_call"):
            fn_call = choice["message"]["function_call"]
            fn_name = fn_call["name"]
            try:
                args = json.loads(fn_call.get("arguments", "{}"))
            except Exception:
                args = {}
            tool_fn = TOOLS_REGISTRY.get(fn_name)
            if not tool_fn:
                tool_result = {"error": f"unknown tool {fn_name}"}
            else:
                try:
                    tool_result = tool_fn(**args)
                except Exception as exc:
                    tool_result = {"error": str(exc)}

            # add messages and continue loop
            messages.append(choice["message"])  # assistant invoking tool
            messages.append({"role": "function", "name": fn_name, "content": json.dumps(tool_result)})
            resp = call_llm(provider, model_id, messages)
            continue
        else:
            break

    assistant_msg = resp["choices"][0]["message"]["content"]
    return {"assistant": assistant_msg, "messages": messages}


# ---------- Root ---------- #

@app.get("/")
async def root():
    return {"message": "FastAPI backend is running"}

# For local development: uvicorn backend.main:app --reload
