from pathlib import Path
from typing import List

from dotenv import load_dotenv

# Load .env from repository root before reading env vars
load_dotenv()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration loaded from environment variables (.env)."""

    secret_key: str = "piskachort"
    file_manager_pin: str = "1234"
    cors_origins: List[str] = ["*"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

# Paths
BACKEND_DIR: Path = Path(__file__).resolve().parent.parent
REPO_ROOT: Path = BACKEND_DIR.parent
WORKSPACES_ROOT: Path = REPO_ROOT / "workspaces"
WORKSPACES_ROOT.mkdir(parents=True, exist_ok=True)
