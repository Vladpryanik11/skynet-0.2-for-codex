"""Single registry for department metadata and lazy crew loading."""

from dataclasses import dataclass
from importlib import import_module
@dataclass(frozen=True)
class DepartmentSpec:
    name: str
    description: str
    keywords: tuple[str, ...]
    loader: str


DEPARTMENT_REGISTRY: dict[str, DepartmentSpec] = {
    "coders": DepartmentSpec(
        name="coders",
        description="Проектирование, генерация, ревью и деплой ИИ-агентов.",
        keywords=("агент", "код", "python", "api", "docker", "github", "бот", "скрипт", "интеграция"),
        loader="agent_factory.crew:AgentFactoryCrew",
    ),
    "marketing": DepartmentSpec(
        name="marketing",
        description="Стратегия, рекламные тексты, email, SEO и редактура.",
        keywords=("пост", "текст", "рассылка", "лендинг текст", "реклама", "оффер", "seo", "копирайт"),
        loader="marketing_dept.crew:MarketingCrew",
    ),
    "design": DepartmentSpec(
        name="design",
        description="Разбор референсов, дизайн-система и готовая HTML/CSS-страница.",
        keywords=("дизайн", "референс", "макет", "сайт", "html", "css", "ui", "лендинг"),
        loader="design_dept.crew:DesignCrew",
    ),
    "quality_control": DepartmentSpec(
        name="quality_control",
        description="Независимая проверка требований, рисков и финального результата.",
        keywords=("проверь", "ревью", "контроль качества", "аудит", "оценка"),
        loader="quality_control_dept.crew:QualityControlCrew",
    ),
}


def keyword_route(user_request: str) -> str | None:
    """Return the strongest keyword match without loading any LLM or crew."""
    text = user_request.lower()
    scores = {
        name: sum(1 for keyword in spec.keywords if keyword in text)
        for name, spec in DEPARTMENT_REGISTRY.items()
    }
    winner, score = max(scores.items(), key=lambda item: item[1])
    return winner if score else None


def load_department_crew(name: str):
    try:
        module_name, class_name = DEPARTMENT_REGISTRY[name].loader.split(":", 1)
    except KeyError as exc:
        raise ValueError(f"Неизвестный отдел: {name}") from exc
    module = import_module(module_name)
    crew_class = getattr(module, class_name)
    return crew_class().crew()
