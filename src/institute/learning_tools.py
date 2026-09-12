import datetime
import os

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

KNOWLEDGE_DIR = os.environ.get("KNOWLEDGE_DIR", "./knowledge")


class RecordLessonInput(BaseModel):
    lesson: str = Field(
        ..., description="Один короткий, конкретный и переиспользуемый урок (1-2 предложения)"
    )


class RecordLessonTool(BaseTool):
    """Сохраняет урок в локальную базу знаний отдела (knowledge/<department>_lessons.md).
    Файл переиспользуется как knowledge source в будущих запусках того же отдела —
    так команда «учится» на предыдущих запросах без дообучения модели."""

    name: str = "record_lesson"
    description: str = (
        "Сохраняет один переиспользуемый урок в базу знаний отдела, чтобы "
        "будущие запуски его учитывали. Вызывай отдельно для каждого урока."
    )
    args_schema: type[BaseModel] = RecordLessonInput
    department: str = ""

    def _run(self, lesson: str) -> str:
        os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
        path = os.path.join(KNOWLEDGE_DIR, f"{self.department}_lessons.md")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"- [{timestamp}] {lesson.strip()}\n")
        return f"Урок сохранён в {path}"
