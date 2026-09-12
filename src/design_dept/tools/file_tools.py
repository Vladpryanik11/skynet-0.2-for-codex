import os

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

OUTPUT_DIR = os.environ.get("DESIGN_OUTPUT_DIR", "./generated_designs")


class SaveDesignFileInput(BaseModel):
    project_name: str = Field(
        ..., description="Короткое имя проекта латиницей, например 'fitness-landing'"
    )
    filename: str = Field(
        ..., description="Имя файла, например design-system.md или index.html"
    )
    content: str = Field(..., description="Полное содержимое файла")


class SaveDesignFileTool(BaseTool):
    name: str = "save_design_file"
    description: str = (
        "Сохраняет файл (дизайн-систему или готовую HTML/CSS-страницу) в "
        "generated_designs/<project_name>/."
    )
    args_schema: type[BaseModel] = SaveDesignFileInput

    def _run(self, project_name: str, filename: str, content: str) -> str:
        safe_project = "".join(
            c if c.isalnum() or c in "-_" else "-" for c in project_name.lower()
        )
        project_dir = os.path.join(OUTPUT_DIR, safe_project)
        os.makedirs(project_dir, exist_ok=True)
        path = os.path.join(project_dir, os.path.basename(filename))
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Сохранено: {path}"
