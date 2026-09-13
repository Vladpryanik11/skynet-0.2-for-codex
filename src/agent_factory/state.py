import json
import os

STATE_DIR = os.environ.get("STATE_DIR", "./.state")


def _path() -> str:
    """Namespaced by PID: main.py, run.py and each Telegram task all run as
    separate OS processes, so a shared filename would let one run's
    before_kickoff clear or overwrite another concurrently running
    process's not-yet-read verdict."""
    return os.path.join(STATE_DIR, f"last_review_verdict.{os.getpid()}.json")


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
