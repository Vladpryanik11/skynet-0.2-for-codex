import os

import anthropic

# Реестр отделов института: ключ -> описание для диспетчера.
# Добавляя новый отдел, впиши его сюда и в _load_department_crew ниже.
DEPARTMENTS = {
    "coders": (
        "Создание новых ИИ-агентов: проектирование, генерация Python/CrewAI-кода, "
        "ревью, деплой агентов в Docker."
    ),
    "marketing": (
        "Маркетинговые и рекламные тексты: посты, email-рассылки, лендинги, "
        "рекламные объявления, копирайтинг, SEO для текста."
    ),
    "design": (
        "Дизайн сайтов/лендингов по референсам: анализ картинок-примеров, "
        "дизайн-система, готовая HTML/CSS-страница."
    ),
}


def _load_department_crew(name: str):
    if name == "coders":
        from agent_factory.crew import AgentFactoryCrew

        return AgentFactoryCrew().crew()
    if name == "marketing":
        from marketing_dept.crew import MarketingCrew

        return MarketingCrew().crew()
    if name == "design":
        from design_dept.crew import DesignCrew

        return DesignCrew().crew()
    raise ValueError(f"Неизвестный отдел: {name}")


def classify_department(user_request: str) -> str:
    client = anthropic.Anthropic()
    options = "\n".join(f"- {name}: {desc}" for name, desc in DEPARTMENTS.items())
    response = client.messages.create(
        model=os.environ.get("ROUTER_MODEL", "claude-haiku-4-5"),
        max_tokens=16,
        system=(
            "Ты диспетчер ИИ-института. По запросу пользователя определи, "
            "какой отдел должен его обработать. Ответь ТОЛЬКО ключом отдела "
            "из списка ниже, без пояснений и знаков препинания.\n\n" + options
        ),
        messages=[{"role": "user", "content": user_request}],
    )
    text = next(b.text for b in response.content if b.type == "text").strip().lower()
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
    crew = _load_department_crew(department)
    result = crew.kickoff(inputs={"user_request": user_request})
    return result.raw
