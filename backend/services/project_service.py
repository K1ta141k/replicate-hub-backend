import os
from typing import Dict, List

from backend.core.settings import WORKSPACES_ROOT


class ProjectService:
    def create(self, name: str) -> Dict[str, str]:
        safe_name = os.path.basename(name)
        project_path = os.path.join(WORKSPACES_ROOT, safe_name)
        os.makedirs(project_path, exist_ok=False)
        return {"success": True, "path": f"/{safe_name}"}

    def list(self) -> List[str]:
        return [d for d in os.listdir(WORKSPACES_ROOT) if os.path.isdir(os.path.join(WORKSPACES_ROOT, d))]
