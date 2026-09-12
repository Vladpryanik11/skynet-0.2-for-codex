from typing import Literal

from pydantic import BaseModel, Field


class ReviewVerdict(BaseModel):
    """Структурированный вердикт Ревьюера — то, что реально проверяет Python
    перед деплоем, а не текст, который DevOps-агент интерпретирует сам."""

    verdict: Literal["APPROVED", "CHANGES_REQUESTED"]
    issues: list[str] = Field(default_factory=list)
