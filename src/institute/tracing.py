import datetime
import json
import os

TRACES_DIR = os.environ.get("TRACES_DIR", "./traces")


def make_task_tracer(department: str):
    """Возвращает task_callback для Crew(...) — пишет одну JSON-строку в
    traces/<department>_<дата>.jsonl после КАЖДОЙ задачи в crew. Это и есть
    вся трассировка: локально, без внешних сервисов, можно грепать/читать
    как обычный текстовый лог."""

    os.makedirs(TRACES_DIR, exist_ok=True)
    trace_file = os.path.join(TRACES_DIR, f"{department}_{datetime.date.today()}.jsonl")

    def _tracer(task_output) -> None:
        record = {
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
            "department": department,
            "agent": getattr(task_output, "agent", None),
            "task_summary": (task_output.summary or "")[:120] if hasattr(task_output, "summary") else None,
            "output_preview": (task_output.raw or "")[:300] if hasattr(task_output, "raw") else str(task_output)[:300],
        }
        with open(trace_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return _tracer
