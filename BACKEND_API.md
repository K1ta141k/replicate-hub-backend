# Shellles Backend ‑ API & Services Documentation

_Last updated: 2025-08-10_

---

## Overview
The backend is a **FastAPI** service that provides three functional pillars:

1. **File-manager API** – CRUD operations on project/workspace files and folders.
2. **Sandbox Service** – spins up a self-contained Vite/React dev-server (or any future runtime) inside each project’s workspace.
3. **AI Chat Service** – exposes a Chat-GPT-style endpoint that allows large-language-models to call backend “tools” (functions) such as `write_file`, `start_dev`, etc.

All data for a project is stored in a single folder:
```
<repo-root>/workspaces/<projectName>/
```
No duplicate copies are kept; the dev-server, AI tools, and manual edits all operate on the same files.

---

## Environment variables
| Key | Purpose |
|-----|---------|
| `SECRET_KEY` | FastAPI session middleware secret (any random string) |
| `OPENAI_API_KEY` | API key for OpenAI (GPT-5 etc.) |
| `GROQ_API_KEY` | API key for Groq (Kimi-2 / Llama-3) |
| `ANTHROPIC_API_KEY` | API key for Anthropic (Claude-3) |
| `E2B_API_KEY` | Optional: key for E2B cloud sandboxes (future) |

Place them in `.env`; `python-dotenv` loads them on startup.

---

## REST Endpoints

### 1. Project Management
| Method | Path | Body | Description |
|--------|------|------|-------------|
| `POST` | `/api/projects` | `{ "name": "myProject" }` | Create a new workspace folder `workspaces/myProject`. |
| `GET`  | `/api/projects` | – | List all workspace directories. |

### 2. File Manager (relative paths are within current project workspace)
| Method | Path | Body / Query | Notes |
|--------|------|-------------|-------|
| `GET`  | `/api/list?path=/subdir` | – | Returns `{ files: [...], folders: [...] }` |
| `GET`  | `/api/read?path=README.md` | – | Get text file content. |
| `POST` | `/api/save` | `{ path, content }` | Overwrite text file. |
| `POST` | `/api/upload` | multipart `file`, `path` | Upload binary or text file. |
| `GET`  | `/api/download?path=file.zip` | – | Download file. |
| `POST` | `/api/rename` | `{ path, newName }` | Rename file/folder. |
| `POST` | `/api/delete` | `{ path }` | Delete file/folder. |
| `POST` | `/api/create-file` | `{ path, content? }` | Create new text file. |

### 3. Sandbox Service
All requests include `{ "project": "myProject" }` to identify workspace (except `exec`, which runs in the *currently active* sandbox).
| Method | Path | Body | Result |
|--------|------|------|--------|
| `POST` | `/api/sandbox/init` | `{ project, timeoutMs?, apiKey? }` | Ensure workspace exists. Creates React/Vite scaffold **and a Python virtual-env** (`venv/`) if directory is empty. |
| `POST` | `/api/sandbox/start` | `{ project }` | Runs `npm install && npm run dev -- --port 5173` in background. Returns `{ url:"http://localhost:5173" }`. |
| `POST` | `/api/sandbox/kill`  | – | Terminates dev-server & clears state. |
| `POST` | `/api/sandbox/exec` | `{ cmd: "pip list" }` | Execute shell command inside sandbox directory with `venv/bin` prepended to `PATH`. Returns `{ stdout, stderr, code }`. |

Legacy `POST /api/sandbox/create` does **init + start** in one call.

The virtual-env name is always `venv`. A typical prompt in the front-end terminal looks like:
```
(venv)user@myProject$ python --version
Python 3.13.5
```

### 4. AI Chat Service
```
POST /api/ai/chat
{
  "project": "myProject",
  "model": "kimi2" | "gpt5" | "claude",
  "messages": [ { "role": "user", "content": "…" }, ... ]
}
```
• Backend attaches function/tool schemas so compatible models can invoke tools.
• Loop executes up to 5 (quick) or 15 (auto-dev) tool calls and returns final assistant response.
```
{
  "assistant": "Here is your updated App.jsx…",
  "messages": [ full conversation array ]
}
```

#### Models
GET `/api/ai/models`

Returns the configured model choices the frontend can present:
```json
{
  "models": [
    { "label": "kimi2", "provider": "groq",   "model_id": "llama3-70b-8192" },
    { "label": "gpt5",  "provider": "openai", "model_id": "gpt-5" },
    { "label": "claude","provider": "anthropic", "model_id": "claude-3-opus-20240229" }
  ]
}
```
Select a model by passing `model` in the chat request body.

---

## Tool Registry (used by AI)
Name → Signature → Description
```
write_file(path, content)      Overwrite or create a text file.
append_file(path, content)     Append text to a file.
read_file(path)                Return file content.
delete_file(path)              Delete a file.
rename_file(path, new_name)    Rename a file.
list_files(dir="")             List filenames in directory.
start_dev()                    Start dev-server (same as /sandbox/start).
stop_dev()                     Stop dev-server (same as /sandbox/kill).
```
Schemas are generated dynamically for OpenAI-style function-calling.

Tool registry also includes an implicit `exec` when called via `/sandbox/exec`. This is **not exposed to AI** for safety.

---

## Runtime folders
```
workspaces/           # All projects live here
  └── myProject/
        package.json
        index.html
        src/

sandbox_workspace/    # Deprecated; now identical to workspaces/ but kept for backward-compat
```

---

## Typical Flow
1. **Create Project** – `POST /api/projects { name }` → workspace folder.
2. **Edit Files** – File-manager endpoints operate directly in workspace.
3. **Start App** – `POST /api/sandbox/start { project }` → opens http://localhost:5173.
4. **AI Assistance** – front-end sends chat to `/api/ai/chat`; AI can call tools to refactor code automatically.
5. **Stop App** – `POST /api/sandbox/kill` when done (optional – autoreload dev-server dies on backend restart).

---

## Error Codes
| Code | Reason |
|------|--------|
| 400  | Bad request / missing param / sandbox not initialised |
| 404  | File or project not found |
| 500  | Unhandled server exception |

---

## Future Extensions (roadmap)
* SSE streaming for `/api/ai/chat`.
* More tools: run_tests, git_commit, docker_build, etc.
* Provider-specific settings (temperature, max_tokens) via request body.
* E2B remote sandbox integration (if `E2B_API_KEY` set).

---

## 5. Terminal / CLI Endpoint

`POST /api/sandbox/exec`

Executes arbitrary shell command **inside the active sandbox workspace**.

Body
```json
{
  "cmd": "pip install requests",
  "timeout": 60   // optional, seconds (default 60)
}
```

Response
```json
{
  "stdout": "…",
  "stderr": "…",
  "code": 0
}
```

Rules & behaviour
* Command runs with working directory = project root (`workspaces/<project>/`).
* If `venv/` exists its `bin` directory is prepended to `PATH` – so `python`, `pip` etc. use the sandbox’s virtual-env.
* The endpoint returns only after the process exits or after the timeout.
* Not exposed to AI tool-calling (only for human users via the terminal pane).

Error responses
| Code | Reason |
|------|--------|
| 400  | Missing `cmd` or sandbox not initialised |
| 500  | Subprocess error (rare) |

---

> Maintainer: Shellles Backend Team
