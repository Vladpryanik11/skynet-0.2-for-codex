import os
import re

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from institute.safety import resolve_inside_dir


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


DANGEROUS_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bos\.system\s*\(", "os.system(...) — произвольное выполнение shell-команд"),
    (r"\bsubprocess\.(run|Popen|call|check_output|check_call)\s*\(", "subprocess.* — запуск внешних процессов"),
    (r"\beval\s*\(", "eval(...) — выполнение произвольного кода из строки"),
    (r"\bexec\s*\(", "exec(...) — выполнение произвольного кода из строки"),
    (r"\b__import__\s*\(", "__import__(...) — динамический импорт в обход обычных проверок"),
    (r"\bpickle\.loads?\s*\(", "pickle.load(s)(...) — небезопасная десериализация"),
    (r"shell\s*=\s*True", "shell=True — риск shell-инъекции"),
    (
        r"(?:api[_-]?key|secret|token|password)\s*=\s*[\"'][^\"'{}]{8,}[\"']",
        "похоже на захардкоженный ключ/токен/пароль вместо чтения из окружения",
    ),
)


class DangerousPatternScanInput(BaseModel):
    code: str = Field(..., description="Python-код для проверки на опасные операции")


class DangerousPatternScanTool(BaseTool):
    name: str = "scan_dangerous_patterns"
    description: str = (
        "Статически сканирует Python-код построчно на опасные операции: "
        "произвольное выполнение shell-команд/eval/exec, небезопасная "
        "десериализация, захардкоженные секреты. Это единственная реальная "
        "проверка безопасности перед деплоем — вердикт APPROVED не должен "
        "выноситься без вызова этого инструмента. Возвращает 'OK: ...' или "
        "список находок с номером строки."
    )
    args_schema: type[BaseModel] = DangerousPatternScanInput

    def _run(self, code: str) -> str:
        findings: list[str] = []
        for lineno, line in enumerate(code.splitlines(), start=1):
            for pattern, description in DANGEROUS_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(f"строка {lineno}: {description} — {line.strip()[:120]}")
        if not findings:
            return "OK: опасных паттернов не найдено (статическая проверка не заменяет ручной аудит)."
        return "НАЙДЕНЫ ОПАСНЫЕ ПАТТЕРНЫ:\n" + "\n".join(findings)


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
        output_dir = os.path.abspath(os.environ.get("OUTPUT_DIR", "./generated_agents"))
        os.makedirs(output_dir, exist_ok=True)
        try:
            path = resolve_inside_dir(output_dir, filename)
        except ValueError as exc:
            return f"ОШИБКА: небезопасный путь к файлу: {exc}"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        return f"Сохранено: {path}"
