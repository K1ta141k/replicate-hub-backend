import os
import json
import uuid
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


class SandboxManager:
    """Manages a single live sandbox that runs inside a dedicated directory.
    For now we support one sandbox at a time. Later we could extend to multiple IDs.
    Persist minimal metadata to a JSON file so that the state survives backend restarts.
    """

    CACHE_FILENAME = "sandbox_cache.json"
    META_FILENAME = "sandbox_meta.json"

    EXCLUDED_PATTERNS = [
        "node_modules/**",
        ".git/**",
        "dist/**",
        "build/**",
        "__pycache__/**",
    ]

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root  # e.g. backend/projects/sandbox
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.workspace_root / self.CACHE_FILENAME
        self.meta_path = self.workspace_root / self.META_FILENAME
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.meta: Dict[str, Any] = {}
        self.process: subprocess.Popen | None = None
        self._load_state()

    # ---------- Persistence helpers ---------- #
    def _load_state(self):
        if self.cache_path.exists():
            try:
                self.cache = json.loads(self.cache_path.read_text())
            except Exception:
                self.cache = {}
        if self.meta_path.exists():
            try:
                self.meta = json.loads(self.meta_path.read_text())
            except Exception:
                self.meta = {}

    def _save_state(self):
        self.cache_path.write_text(json.dumps(self.cache, indent=2))
        self.meta_path.write_text(json.dumps(self.meta, indent=2))

    # ---------- Sandbox lifecycle ---------- #
    def is_active(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def init(self, project_name: str, api_key: str | None = None, timeout_ms: int = 5 * 60_000):
        """Ensure workspace directory for project exists; scaffold if empty."""
        api_key = api_key or os.getenv("E2B_API_KEY")
        sandbox_id = project_name
        sandbox_dir = self.workspace_root / sandbox_id
        if not sandbox_dir.exists():
            sandbox_dir.mkdir(parents=True, exist_ok=True)
            self._write_scaffold(sandbox_dir)

        # Ensure Python virtual environment exists for this sandbox
        venv_dir = sandbox_dir / "venv"
        if not venv_dir.exists():
            import sys, subprocess
            subprocess.run([sys.executable, "-m", "venv", "venv"], cwd=sandbox_dir, check=False)

        host = "http://localhost:5173"
        now = datetime.utcnow().isoformat()
        self.meta = {
            "sandboxId": sandbox_id,
            "url": host,
            "startedAt": now,
            "timeoutMs": timeout_ms,
            "apiKey": api_key,
        }
        self.cache = {}
        self._save_state()
        return self.meta

    def start_dev(self):
        if self.process and self.is_active():
            return self.meta  # already running
        sandbox_dir = self._sandbox_dir()
        subprocess.run(["npm", "install"], cwd=sandbox_dir, check=False)
        self.process = subprocess.Popen(["npm", "run", "dev", "--", "--port", "5173"], cwd=sandbox_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return self.meta

    # keep old create for backward compatibility
    def create(self, project_name: str, api_key: str | None = None, timeout_ms: int = 5 * 60_000):
        self.init(project_name=project_name, api_key=api_key, timeout_ms=timeout_ms)
        self.start_dev()
        return self.meta

    def kill(self):
        if self.process and self.is_active():
            self.process.terminate()
            try:
                self.process.wait(10)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None
        # Remove workspace directory
        if self.meta.get("sandboxId"):
            sandbox_dir = self.workspace_root / self.meta["sandboxId"]
            if sandbox_dir.exists():
                shutil.rmtree(sandbox_dir, ignore_errors=True)
        self.cache = {}
        self.meta = {}
        self._save_state()

    # ---------- File helpers ---------- #
    def _should_exclude(self, rel_path: str) -> bool:
        for pattern in self.EXCLUDED_PATTERNS:
            if Path(rel_path).match(pattern):
                return True
        return False

    def write_file_and_cache(self, rel_path: str, content: str):
        if self._should_exclude(rel_path):
            return
        sandbox_dir = self._sandbox_dir()
        full_path = sandbox_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        self.cache[rel_path] = {"content": content, "lastModified": datetime.utcnow().isoformat()}
        self._save_state()

    def read_files(self) -> Dict[str, str]:
        """Return cached files (<10 KB) or walk filesystem first time."""
        if self.cache:
            return self.cache
        sandbox_dir = self._sandbox_dir()
        files: Dict[str, str] = {}
        for path in sandbox_dir.rglob("*"):
            if path.is_file() and path.stat().st_size < 10 * 1024:
                rel = str(path.relative_to(sandbox_dir))
                if self._should_exclude(rel):
                    continue
                files[rel] = {"content": path.read_text(errors="ignore"), "lastModified": datetime.utcnow().isoformat()}
        self.cache = files
        self._save_state()
        return files

    # ---------- Command execution ---------- #
    def run_command(self, cmd: str, timeout: int = 60) -> Dict[str, Any]:
        """Execute a shell command inside the sandbox directory, using the venv if present."""
        sandbox_dir = self._sandbox_dir()
        venv_bin = sandbox_dir / "venv" / "bin"
        env = os.environ.copy()
        if venv_bin.exists():
            # Prepend venv executables to PATH so `python`, `pip`, etc. use the venv
            env["PATH"] = str(venv_bin) + os.pathsep + env.get("PATH", "")
        try:
            proc = subprocess.run(cmd, cwd=sandbox_dir, shell=True, capture_output=True, text=True, timeout=timeout, env=env)
            return {
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "code": proc.returncode,
            }
        except subprocess.TimeoutExpired as ex:
            return {
                "error": f"Command timed out after {timeout}s",
                "stdout": ex.stdout,
                "stderr": ex.stderr,
            }

    # ---------- Internal ---------- #
    def _sandbox_dir(self) -> Path:
        sandbox_id = self.meta.get("sandboxId")
        if not sandbox_id:
            raise RuntimeError("Sandbox not created yet")
        return self.workspace_root / sandbox_id

    def _write_scaffold(self, dir: Path):
        # Minimal Vite + React scaffold (placeholder)
        (dir / "package.json").write_text(json.dumps({
            "name": "sandbox-app",
            "version": "0.1.0",
            "scripts": {"dev": "vite"},
            "dependencies": {"react": "^18.2.0", "react-dom": "^18.2.0"},
            "devDependencies": {"vite": "^5.0.0"}
        }, indent=2))
        (dir / "index.html").write_text("""<!DOCTYPE html><html><head><title>Sandbox</title></head><body><div id='root'></div><script type='module' src='/src/main.jsx'></script></body></html>""")
        src = dir / "src"
        src.mkdir(exist_ok=True)
        (src / "main.jsx").write_text("import React from 'react'; import ReactDOM from 'react-dom/client'; import App from './App';\nReactDOM.createRoot(document.getElementById('root')).render(<App/>);")
        (src / "App.jsx").write_text("export default function App() { return <h1>Hello Sandbox</h1>; }")

# Singleton instance used by API
sandbox_root = Path(__file__).resolve().parent.parent / "sandbox_workspace"
manager = SandboxManager(sandbox_root)
