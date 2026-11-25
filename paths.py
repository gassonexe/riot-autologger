
import os
import sys
from pathlib import Path

APP_NAME = "RiotAutoLogger"
ACCOUNTS_FILENAME = "accounts.json"


def app_data_dir() -> Path:
    base = os.environ.get("APPDATA")
    root = Path(base) if base else Path.home() / ".config"
    folder = root / APP_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def accounts_file() -> Path:
    return app_data_dir() / ACCOUNTS_FILENAME


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def resource_path(relative_path: str) -> str:
    return str(_base_dir() / relative_path)


def legacy_accounts_files() -> list:
    """Places the old version may have written accounts.json (it used the working directory)."""
    candidates = [Path.cwd(), Path(__file__).resolve().parent]
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent)

    found, seen = [], set()
    for folder in candidates:
        path = folder / ACCOUNTS_FILENAME
        key = str(path.resolve()) if path.exists() else str(path)
        if key not in seen and path.is_file():
            seen.add(key)
            found.append(path)
    return found
