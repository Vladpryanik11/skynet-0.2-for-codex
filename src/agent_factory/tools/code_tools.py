import os

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class SyntaxCheckInput(BaseModel):
    code: str = Field(..., description="Python-код для проверки синтаксиса")


class PythonSyntaxCheckTool(BaseTool):
    name: str = "python_syntax_check"
    description: str = (
        "Проверяет, что переданная строка кода — валидный Python. "
        "Возвращает 'OK' или сообщение об ошибке с номером строки."
    )
    args_schema: type[BaseModel] = SyntaxCheckInput

    def _run(self, code: str) -> str:
        try:
            compile(code, "<generated_agent>", "exec")
        except SyntaxError as exc:
            return f"SYNTAX_ERROR: строка {exc.lineno}: {exc.msg}"
        return "OK: синтаксис валиден"


class SaveAgentInput(BaseModel):
    filename: str = Field(..., description="Имя файла, например my_agent.py")
    code: str = Field(..., description="Полное содержимое файла с кодом агента")


class SaveGeneratedAgentTool(BaseTool):
    name: str = "save_generated_agent"
    description: str = (
        "Сохраняет финальный код сгенерированного агента на диск в "
        "OUTPUT_DIR (по умолчанию ./generated_agents)."
    )
    args_schema: type[BaseModel] = SaveAgentInput

    def _run(self, filename: str, code: str) -> str:
        output_dir = os.environ.get("OUTPUT_DIR", "./generated_agents")
        os.makedirs(output_dir, exist_ok=True)
        safe_name = os.path.basename(filename)
        path = os.path.join(output_dir, safe_name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        return f"Сохранено: {path}"
