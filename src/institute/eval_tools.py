import os

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from institute.local_mode import anthropic_available


class JudgeOutputInput(BaseModel):
    user_request: str = Field(..., description="Исходный запрос пользователя")
    final_output: str = Field(..., description="Итоговый результат отдела, который нужно оценить")


class JudgeOutputTool(BaseTool):
    """LLM-as-Judge: независимая оценка результата ДРУГИМ вызовом модели,
    а не самим агентом-рефлексией задним числом. Нужна, чтобы уроки
    самообучения основывались на реальной оценке, а не на самомнении
    того же агента, который делал работу."""

    name: str = "judge_final_output"
    description: str = (
        "Оценивает итоговый результат отдела по шкале 1-5: насколько он "
        "соответствует запросу пользователя, нет ли явных ошибок/выдумок. "
        "Вызывай ДО того, как формулировать уроки самообучения."
    )
    args_schema: type[BaseModel] = JudgeOutputInput

    def _run(self, user_request: str, final_output: str) -> str:
        if not anthropic_available():
            score = 4 if len(final_output.strip()) > 400 else 3
            return (
                f"Оценка: {score}\n"
                "Причина: локальный/гибридный режим без Anthropic API; "
                "выдана базовая эвристическая оценка по полноте результата."
            )

        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=os.environ.get("JUDGE_MODEL", "claude-haiku-4-5"),
            max_tokens=300,
            system=(
                "Ты независимый судья качества. Оцени результат работы команды "
                "по шкале 1-5 (5 — отлично соответствует запросу, без ошибок; "
                "1 — не соответствует запросу или содержит явные ошибки/выдумки). "
                "Будь строг и конкретен. Формат ответа STRICTLY:\n"
                "Оценка: <1-5>\nПричина: <одно предложение>"
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"Запрос пользователя:\n{user_request}\n\nРезультат:\n{final_output[:6000]}",
                }
            ],
        )
        return next(b.text for b in response.content if b.type == "text")
