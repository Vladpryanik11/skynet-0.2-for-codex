import os

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from institute.local_mode import anthropic_available, openai_available
from institute.openai_client import chat_completion, text_message


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
        system_prompt = (
            "Ты независимый судья качества. Оцени результат работы команды "
            "по шкале 1-5 (5 — отлично соответствует запросу, без ошибок; "
            "1 — не соответствует запросу или содержит явные ошибки/выдумки). "
            "Будь строг и конкретен. Формат ответа STRICTLY:\n"
            "Оценка: <1-5>\nПричина: <одно предложение>"
        )
        user_prompt = f"Запрос пользователя:\n{user_request}\n\nРезультат:\n{final_output[:6000]}"

        if openai_available() and not anthropic_available():
            return chat_completion(
                [text_message("system", system_prompt), text_message("user", user_prompt)],
                model=os.environ.get("OPENAI_JUDGE_MODEL") or os.environ.get("OPENAI_FAST_MODEL"),
                fallback_models=os.environ.get("OPENAI_MODEL_FALLBACKS", "gpt-4.1-mini,gpt-4o-mini"),
                max_tokens=300,
                temperature=0.2,
                timeout=90,
            )

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
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return next(b.text for b in response.content if b.type == "text")
