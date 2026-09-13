"""Small OpenAI HTTP helpers used outside CrewAI."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


class OpenAIRequestError(RuntimeError):
    pass


def openai_api_base() -> str:
    return os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1").strip().rstrip("/")


def openai_model_name(raw_model: str | None = None, default: str = DEFAULT_OPENAI_MODEL) -> str:
    model = (raw_model or default).strip()
    if model.startswith("openai/"):
        return model[len("openai/") :]
    return model or default


def candidate_models(primary: str | None, fallback_models: str | None = None) -> list[str]:
    raw_models = [primary or os.environ.get("OPENAI_DEFAULT_MODEL") or DEFAULT_OPENAI_MODEL]
    raw_models.extend((fallback_models or os.environ.get("OPENAI_MODEL_FALLBACKS", "")).split(","))

    models: list[str] = []
    for raw_model in raw_models:
        model = openai_model_name(raw_model)
        if model and model not in models:
            models.append(model)
    return models


def _error_text(exc: urllib.error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8", errors="replace")
    except Exception:
        body = ""
    body = body.strip()
    if len(body) > 800:
        body = body[:800] + "..."
    return f"OpenAI API error {exc.code}: {body or exc.reason}"


def _post_json(path: str, payload: Mapping[str, Any], timeout: int) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise OpenAIRequestError("OPENAI_API_KEY is empty.")

    request = urllib.request.Request(
        f"{openai_api_base()}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise OpenAIRequestError(_error_text(exc)) from exc
    except (TimeoutError, urllib.error.URLError) as exc:
        raise OpenAIRequestError(f"OpenAI API connection failed: {exc}") from exc


def chat_completion(
    messages: Sequence[Mapping[str, Any]],
    *,
    model: str | None = None,
    fallback_models: str | None = None,
    max_tokens: int = 512,
    temperature: float | None = 0.3,
    timeout: int = 90,
) -> str:
    errors: list[str] = []
    for candidate in candidate_models(model, fallback_models):
        payload: dict[str, Any] = {
            "model": candidate,
            "messages": list(messages),
            "max_tokens": max_tokens,
        }
        if temperature is not None:
            payload["temperature"] = temperature

        try:
            response = _post_json("/chat/completions", payload, timeout)
        except OpenAIRequestError as exc:
            errors.append(f"{candidate}: {exc}")
            continue

        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise OpenAIRequestError(f"Unexpected OpenAI response shape: {response!r}") from exc
        if isinstance(content, list):
            return "".join(str(item.get("text", item)) for item in content).strip()
        return str(content).strip()

    raise OpenAIRequestError("; ".join(errors) or "No OpenAI models were available.")


def text_message(role: str, content: str) -> dict[str, str]:
    return {"role": role, "content": content}


def vision_user_message(text: str, images: Iterable[tuple[str, str]]) -> dict[str, Any]:
    content: list[dict[str, Any]] = [{"type": "text", "text": text}]
    for label, data_url in images:
        content.append({"type": "text", "text": label})
        content.append({"type": "image_url", "image_url": {"url": data_url}})
    return {"role": "user", "content": content}
