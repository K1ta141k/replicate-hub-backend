# Shellles – Developer Workspace Backend

> Self-hosted service that lets you browse & edit project files, spin up an on-demand sandbox (Vite dev-server), and talk to an AI agent that can refactor code via function-calling.

---

## Features

1. **File-Manager API** – CRUD endpoints for files/folders inside `workspaces/<project>/`.
2. **Sandbox Manager** – creates one workspace per project and can launch `npm install && npm run dev` on port 5173.
3. **AI Chat** – `/api/ai/chat` exposes ChatGPT-style interface; the model can call backend tools (`write_file`, `start_dev`, …).
4. **Minimal Frontend** (Flask + vanilla JS) – demo UI for browsing files, editing with Monaco, running sandbox, and chatting.

---

## Quick Start (local)
```bash
# 1. Clone & install
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Environment
cp .env.example .env   # then edit values

# 3. Run backend (FastAPI)
uvicorn backend.main:app --reload --port 8000

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

## API Summary
See `BACKEND_API.md` for the full spec.

* `/api/projects` – create & list projects
* `/api/list`, `/api/read`, `/api/save`, … – file operations
* `/api/sandbox/init`, `/start`, `/kill` – sandbox lifecycle
* `/api/ai/chat` – AI endpoint with function-calling

---

## Folder Layout
```
backend/           FastAPI app
frontend/          Flask demo UI
workspaces/        <created at runtime>
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
