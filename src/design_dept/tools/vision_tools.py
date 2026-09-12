import base64
import mimetypes
import os

import anthropic
from crewai.tools import BaseTool
from pydantic import BaseModel

REFERENCES_DIR = os.environ.get("REFERENCES_DIR", "./references")
SUPPORTED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


class AnalyzeReferencesInput(BaseModel):
    """Инструмент не принимает параметров — сам находит картинки в REFERENCES_DIR."""


class AnalyzeReferencesTool(BaseTool):
    """Смотрит на референсы дизайна (скриншоты с Pinterest/Dribbble/Awwwards и т.п.)
    через vision-запрос к Claude и возвращает разбор: типографика, сетка,
    палитра, ритм блоков, работа с пространством — по каждому + общие черты."""

    name: str = "analyze_reference_images"
    description: str = (
        "Анализирует все изображения-референсы из папки references/ (типографика, "
        "сетка, палитра, ритм блоков, работа с пространством) и возвращает разбор "
        "по каждому изображению плюс общие черты для единой дизайн-системы."
    )
    args_schema: type[BaseModel] = AnalyzeReferencesInput

    def _run(self) -> str:
        if not os.path.isdir(REFERENCES_DIR):
            return f"Папка {REFERENCES_DIR} не найдена. Добавьте туда картинки-референсы (скриншоты сайтов) и повтори."

        files = sorted(
            f
            for f in os.listdir(REFERENCES_DIR)
            if os.path.splitext(f)[1].lower() in SUPPORTED_EXT
        )
        if not files:
            return (
                f"В папке {REFERENCES_DIR} нет изображений (.png/.jpg/.jpeg/.webp/.gif). "
                "Сохраните туда скриншоты референсов и повтори."
            )

        content = [
            {
                "type": "text",
                "text": (
                    "Ниже идут референсы дизайна сайтов, пронумерованные по порядку "
                    "(№1, №2, ...). Для каждого опиши: типографику, сетку/грид, "
                    "цветовую палитру (с примерными hex, если можешь предположить), "
                    "ритм блоков, работу с пространством. В конце — общие черты между "
                    "всеми референсами, на основе которых можно собрать одну "
                    "согласованную дизайн-систему."
                ),
            }
        ]
        for i, filename in enumerate(files, start=1):
            path = os.path.join(REFERENCES_DIR, filename)
            media_type = mimetypes.guess_type(path)[0] or "image/png"
            with open(path, "rb") as f:
                data = base64.standard_b64encode(f.read()).decode("utf-8")
            content.append({"type": "text", "text": f"№{i} ({filename}):"})
            content.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": data},
                }
            )

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=os.environ.get("DESIGN_VISION_MODEL", "claude-opus-5"),
            max_tokens=4096,
            messages=[{"role": "user", "content": content}],
        )
        return next(b.text for b in response.content if b.type == "text")
