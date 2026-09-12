import json
import os

STATE_DIR = os.environ.get("STATE_DIR", "./.state")
REVIEW_STATE_FILE = "last_review_verdict.json"


def _path() -> str:
    return os.path.join(STATE_DIR, REVIEW_STATE_FILE)


def write_review_verdict(verdict: str, issues: list[str]) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(_path(), "w", encoding="utf-8") as f:
        json.dump({"verdict": verdict, "issues": issues}, f, ensure_ascii=False, indent=2)


def read_review_verdict() -> dict | None:
    path = _path()
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def clear_review_verdict() -> None:
    path = _path()
    if os.path.isfile(path):
        os.remove(path)
