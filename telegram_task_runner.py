"""Run one SKYNET Telegram task in a separate process."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from institute.local_mode import openai_available  # noqa: E402
from institute.openai_client import chat_completion, openai_model_name, text_message  # noqa: E402

RUNNER_RESULT_START = "<<<SKYNET_RESULT_START>>>"
RUNNER_RESULT_END = "<<<SKYNET_RESULT_END>>>"

FAST_SYSTEM_PROMPT = (
    "Ты быстрый Telegram-режим SKYNET. Отвечай по-русски, практично и по делу. "
    "Не запускай воображаемые инструменты и не утверждай, что сделал работу на сервере, "
    "если в запросе нужен полный агентный конвейер. В таком случае дай краткий полезный "
    "ответ и предложи выбрать режим Кодеры, Маркетинг, Дизайн или Авто."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one SKYNET task for telegram_bot.py")
    parser.add_argument(
        "--mode",
        choices=("fast", "auto", "coders", "marketing", "design"),
        default="fast",
        help="Work mode selected in Telegram.",
    )
    return parser.parse_args()


def int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, default)))
    except ValueError:
        return default


def float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


def ollama_model_name(raw_model: str | None = None) -> str:
    model = (raw_model or os.environ.get("LOCAL_DEFAULT_MODEL") or "ollama/llama3.2:1b").strip()
    for prefix in ("ollama_chat/", "ollama/"):
        if model.startswith(prefix):
            return model[len(prefix) :]
    return model or "llama3.2:1b"


def ollama_base_url() -> str:
    return os.environ.get("OLLAMA_API_BASE", "http://127.0.0.1:11434").strip().rstrip("/")


def build_fast_payload(user_request: str) -> dict[str, object]:
    return {
        "model": ollama_model_name(),
        "stream": False,
        "messages": [
            {"role": "system", "content": FAST_SYSTEM_PROMPT},
            {"role": "user", "content": user_request},
        ],
        "options": {
            "temperature": float_env("FAST_MODE_TEMPERATURE", 0.3),
            "num_ctx": int_env("FAST_MODE_NUM_CTX", 2048),
            "num_predict": int_env("FAST_MODE_NUM_PREDICT", 384),
        },
    }


def fast_provider() -> str:
    provider = os.environ.get("FAST_MODE_PROVIDER", "auto").strip().lower()
    if provider not in {"auto", "openai", "ollama"}:
        provider = "auto"
    if provider == "auto":
        return "openai" if openai_available() else "ollama"
    return provider


def run_openai_fast_response(user_request: str) -> str:
    model = openai_model_name(
        os.environ.get("OPENAI_FAST_MODEL")
        or os.environ.get("OPENAI_DEFAULT_MODEL")
        or os.environ.get("CLOUD_DEFAULT_MODEL")
    )
    return chat_completion(
        [
            text_message("system", FAST_SYSTEM_PROMPT),
            text_message("user", user_request),
        ],
        model=model,
        fallback_models=os.environ.get("OPENAI_MODEL_FALLBACKS", "gpt-4.1-mini,gpt-4o-mini"),
        max_tokens=int_env("FAST_MODE_NUM_PREDICT", 384),
        temperature=float_env("FAST_MODE_TEMPERATURE", 0.3),
        timeout=int_env("FAST_MODE_TIMEOUT", 90),
    )


def run_fast_response(user_request: str) -> str:
    if fast_provider() == "openai":
        return run_openai_fast_response(user_request)

    payload = build_fast_payload(user_request)
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{ollama_base_url()}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    timeout = int_env("FAST_MODE_TIMEOUT", 90)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except (TimeoutError, urllib.error.URLError) as exc:
        raise RuntimeError(f"быстрый режим не смог подключиться к Ollama: {exc}") from exc

    content = response_payload.get("message", {}).get("content", "")
    return str(content).strip() or "(пустой ответ)"


def run_agent_pipeline(user_request: str, mode: str) -> str:
    from institute.router import route_and_run

    department_override = None if mode == "auto" else mode
    return route_and_run(user_request, department_override=department_override)


def main() -> None:
    args = parse_args()
    user_request = sys.stdin.read().strip()
    if not user_request:
        raise SystemExit("Empty SKYNET request.")

    if args.mode == "fast":
        result = run_fast_response(user_request)
    else:
        result = run_agent_pipeline(user_request, args.mode)

    print(RUNNER_RESULT_START, flush=True)
    print(result, flush=True)
    print(RUNNER_RESULT_END, flush=True)


if __name__ == "__main__":
    main()
