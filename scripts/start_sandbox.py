import argparse
import os
import pathlib
import json
import requests
from dotenv import load_dotenv

EXCLUDED_PATTERNS = [
    "node_modules",
    ".git",
    "dist",
    "build",
    "__pycache__",
]


def should_exclude(path: pathlib.Path):
    parts = path.parts
    for p in parts:
        if p in EXCLUDED_PATTERNS:
            return True
    return False


def gather_files(root: pathlib.Path):
    files = []
    for file in root.rglob("*"):
        if file.is_file() and not should_exclude(file) and file.stat().st_size < 100 * 1024:
            rel = str(file.relative_to(root)).replace("\\", "/")
            files.append({"path": rel, "content": file.read_text(errors="ignore")})
    return files


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Start sandbox and upload project files")
    parser.add_argument("project", help="Path to project directory")
    parser.add_argument("--api", default="http://localhost:8000", help="Backend API base URL")
    args = parser.parse_args()

    project_dir = pathlib.Path(args.project).resolve()
    if not project_dir.is_dir():
        raise SystemExit(f"Project dir {project_dir} not found")

    api_key = os.getenv("E2B_API_KEY")
    print("Creating sandbox ...")
    resp = requests.post(f"{args.api}/api/sandbox/create", json={"apiKey": api_key})
    if resp.status_code != 200:
        raise SystemExit(f"Failed to create sandbox: {resp.text}")
    meta = resp.json()
    print("Sandbox URL:", meta.get("url"))

    files = gather_files(project_dir)
    print(f"Uploading {len(files)} files ...")
    batch = {"files": files}
    resp = requests.post(f"{args.api}/api/sandbox/apply-code", json=batch)
    if resp.status_code != 200:
        raise SystemExit(f"Failed to upload files: {resp.text}")
    result = resp.json()
    print("Sync complete:", json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
