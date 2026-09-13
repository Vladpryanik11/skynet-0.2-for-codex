import os
import json

from institute.local_mode import anthropic_available, openai_available
from institute.knowledge import lesson_context
from institute.openai_client import chat_completion, text_message
from institute.registry import DEPARTMENT_REGISTRY, keyword_route, load_department_crew
from institute.run_store import RunStore
from institute.runtime import quality_gate_enabled

DEPARTMENTS = {name: spec.description for name, spec in DEPARTMENT_REGISTRY.items()}
KEYWORD_RULES = {name: spec.keywords for name, spec in DEPARTMENT_REGISTRY.items()}


def _load_department_crew(name: str):
    return load_department_crew(name)


def keyword_fallback(user_request: str) -> str | None:
    return keyword_route(user_request)


def classify_department(user_request: str) -> str:
    fallback = keyword_fallback(user_request)
    if fallback:
        return fallback

    options = "\n".join(f"- {name}: {desc}" for name, desc in DEPARTMENTS.items())
    system_prompt = (
        "Ты диспетчер ИИ-института. По запросу пользователя определи, "
        "какой отдел должен его обработать. Ответь STRICT JSON без markdown: "
        "{\"department\":\"<ключ отдела>\",\"confidence\":0.0,\"reason\":\"коротко\"}. "
        "Ключ отдела выбери только из списка ниже.\n\n" + options
    )

    if openai_available() and not anthropic_available():
        text = chat_completion(
            [text_message("system", system_prompt), text_message("user", user_request)],
            model=os.environ.get("OPENAI_ROUTER_MODEL") or os.environ.get("OPENAI_FAST_MODEL"),
            fallback_models=os.environ.get("OPENAI_MODEL_FALLBACKS", "gpt-4.1-mini,gpt-4o-mini"),
            max_tokens=120,
            temperature=0.1,
            timeout=60,
        ).strip().lower()
        try:
            payload = json.loads(text)
            department = str(payload.get("department", "")).strip().lower()
            if department in DEPARTMENTS:
                return department
        except json.JSONDecodeError:
            pass

        for name in DEPARTMENTS:
            if name in text:
                return name

    if not anthropic_available():
        return os.environ.get("DEFAULT_DEPARTMENT", "coders")

    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=os.environ.get("ROUTER_MODEL", "claude-haiku-4-5"),
        max_tokens=120,
        system=system_prompt,
        messages=[{"role": "user", "content": user_request}],
    )
    text = next(b.text for b in response.content if b.type == "text").strip().lower()
    try:
        payload = json.loads(text)
        department = str(payload.get("department", "")).strip().lower()
        if department in DEPARTMENTS:
            return department
    except json.JSONDecodeError:
        pass

    for name in DEPARTMENTS:
        if name in text:
            return name
    raise ValueError(
        f"Не удалось определить отдел по ответу диспетчера: {text!r}. "
        f"Известные отделы: {list(DEPARTMENTS)}"
    )


def normalize_department_override(department_override: str | None) -> str | None:
    if not department_override:
        return None
    department = department_override.strip().lower()
    if department not in DEPARTMENTS:
        raise ValueError(f"Неизвестный отдел: {department_override}. Известные отделы: {list(DEPARTMENTS)}")
    return department


def route_and_run(user_request: str, department_override: str | None = None) -> str:
    department = normalize_department_override(department_override) or classify_department(user_request)
    print(f"[Институт] Запрос направлен в отдел: {department}")
    store = RunStore()
    manifest = store.start(user_request, department)
    try:
        crew = _load_department_crew(department)
        result = crew.kickoff(
            inputs={
                "user_request": user_request,
                "department_knowledge": lesson_context(department),
            }
        )
        final_output = result.raw

        if quality_gate_enabled() and department != "quality_control":
            print("[Институт] Финальный результат направлен в отдел: quality_control")
            quality_crew = _load_department_crew("quality_control")
            quality_result = quality_crew.kickoff(
                inputs={
                    "user_request": user_request,
                    "final_output": final_output,
                    "department_knowledge": lesson_context("quality_control"),
                }
            )
            final_output = quality_result.raw

        store.complete(manifest, final_output)
        return final_output
    except Exception as exc:
        store.fail(manifest, exc)
        raise
