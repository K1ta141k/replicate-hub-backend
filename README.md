# Shellles – Developer Workspace Backend

> Self-hosted service that lets you browse & edit project files, spin up an on-demand sandbox (Vite dev-server), and talk to an AI agent that can refactor code via function-calling.

---

## Features

1. **File-Manager API** – secure CRUD over project files/folders (path-sanitised so users can’t escape their sandbox).
2. **Sandbox Workspace** – each project gets its own directory; on first init we scaffold a minimal React/Vite app **and auto-create a Python virtual-env** (`python -m venv venv`).
3. **Terminal API** – interactive pane in the UI powered by `POST /api/sandbox/exec`, commands run inside the workspace with the venv on `PATH` (prompt shown as `(venv)user@<project>$`).
4. **Dev-Server launcher** – one-click `npm install && npm run dev` on port 5173.
5. **AI Chat** – `/api/ai/chat` endpoint with tool-calling so the model can read/write files or start/stop the dev-server.
6. **Demo Frontend** (Flask + vanilla JS + Monaco + xterm-like panes).

---

## Quick Start (local)
```bash
# 1. Clone & install
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Environment
cp .env.example .env   # then edit values

# 3. Run backend (FastAPI)
uvicorn backend.app:app --reload --port 8000  # new entry-point

# 4. Run demo frontend (Flask)
python frontend/app.py  # serves http://localhost:5000
```

### .env example
```dotenv
SECRET_KEY=dev-secret
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gk-...
ANTHROPIC_API_KEY=sk-ant-...
E2B_API_KEY=optional
```

---

## Core Endpoints (summary)
See `BACKEND_API.md` for full spec.

| Category | Main endpoints |
|----------|----------------|
| Projects | `POST /api/projects`, `GET /api/projects` |
| Files    | `GET /api/list`, `GET /api/read`, `POST /api/save`, `upload`, `rename`, `delete`, `create-file` |
| Sandbox  | `sandbox/init`, `start`, `kill`, **`exec`** (terminal) |
| AI Chat  | `POST /api/ai/chat` |
| Auth     | `login`, `logout`, `check-auth` (PIN – can be disabled) |

---

## Folder Layout
```
backend/           FastAPI app
frontend/          Flask demo UI (file-manager + IDE + chat + terminal)
workspaces/        All sandbox workspaces live here (one per project)
BACKEND_API.md     Complete REST + tool documentation
scripts/           Helper CLI scripts (e.g. start_sandbox.py)
```

---

## Roadmap
* Implement SSE streaming for AI chat
* Add more tools: run_tests, git_commit
* Remote sandboxes on E2B
* Docker image for easy deploy

---

## License
MIT © 2025 Shellles 
