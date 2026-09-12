import os
import json

from institute.local_mode import anthropic_available
from institute.knowledge import lesson_context
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

    if not anthropic_available():
        return os.environ.get("DEFAULT_DEPARTMENT", "coders")

    import anthropic

    client = anthropic.Anthropic()
    options = "\n".join(f"- {name}: {desc}" for name, desc in DEPARTMENTS.items())
    response = client.messages.create(
        model=os.environ.get("ROUTER_MODEL", "claude-haiku-4-5"),
        max_tokens=120,
        system=(
            "Ты диспетчер ИИ-института. По запросу пользователя определи, "
            "какой отдел должен его обработать. Ответь STRICT JSON без markdown: "
            "{\"department\":\"<ключ отдела>\",\"confidence\":0.0,\"reason\":\"коротко\"}. "
            "Ключ отдела выбери только из списка ниже.\n\n" + options
        ),
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


def route_and_run(user_request: str) -> str:
    department = classify_department(user_request)
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
