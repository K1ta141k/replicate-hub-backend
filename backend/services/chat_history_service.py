from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.sandbox import manager as sandbox_manager
from backend.core.settings import REPO_ROOT


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: str


class ChatHistoryService:
    """Persists chat history outside the sandbox tree for durability/backups.

    New location (preferred):
      <repo_root>/chat_histories/<project>/<session>.jsonl

    Backward compatibility:
      If no file is found in the new location, `load()` will also
      look under the legacy sandbox path: <sandbox>/.ai/<session>.jsonl
    """

    DEFAULT_SESSION = "history"
    BASE_DIR: Path = REPO_ROOT / "chat_histories"

    # --------- helpers ---------
    def _project_id(self) -> str:
        sandbox_id = sandbox_manager.meta.get("sandboxId") if sandbox_manager.meta else None
        if not sandbox_id:
            raise RuntimeError("Sandbox not created yet")
        return sandbox_id

    def _folder(self) -> Path:
        folder = self.BASE_DIR / self._project_id()
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def _path(self, session: Optional[str]) -> Path:
        name = (session or self.DEFAULT_SESSION).strip() or self.DEFAULT_SESSION
        safe = "".join(ch for ch in name if ch.isalnum() or ch in ("-", "_"))
        if not safe:
            safe = self.DEFAULT_SESSION
        return self._folder() / f"{safe}.jsonl"

    def _legacy_path(self, session: Optional[str]) -> Path:
        # <sandbox>/.ai/<session>.jsonl
        sandbox_dir = sandbox_manager._sandbox_dir()
        legacy_folder = sandbox_dir / ".ai"
        return legacy_folder / f"{(session or self.DEFAULT_SESSION)}.jsonl"

    # --------- API ---------
    def list_sessions(self) -> List[str]:
        folder = self._folder()
        sessions = [p.stem for p in folder.glob("*.jsonl")]
        # include legacy-only sessions (best-effort)
        try:
            legacy = self._legacy_path(None).parent
            if legacy.exists():
                sessions = sorted(set(sessions) | {p.stem for p in legacy.glob('*.jsonl')})
        except Exception:
            pass
        return sorted(sessions)

    def load(self, session: Optional[str] = None, limit: int | None = None) -> List[Dict[str, Any]]:
        p = self._path(session)
        messages: List[Dict[str, Any]] = []
        # prefer new location
        if p.exists():
            with p.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        messages.append(json.loads(line))
                    except Exception:
                        continue
        else:
            # fallback to legacy
            legacy = self._legacy_path(session)
            if legacy.exists():
                with legacy.open("r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            messages.append(json.loads(line))
                        except Exception:
                            continue
        if limit is not None:
            return messages[-limit:]
        return messages

    def append(self, role: str, content: str, session: Optional[str] = None) -> None:
        p = self._path(session)
        p.parent.mkdir(parents=True, exist_ok=True)
        entry = ChatMessage(role=role, content=content, timestamp=datetime.utcnow().isoformat())
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry.__dict__, ensure_ascii=False) + "\n")

    def clear(self, session: Optional[str] = None) -> None:
        p = self._path(session)
        if p.exists():
            p.unlink()

    def delete_session(self, session: str) -> None:
        self.clear(session=session)

    def create_session(self, session: str) -> None:
        self._path(session).touch(exist_ok=True)
