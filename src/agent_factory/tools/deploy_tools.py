import os
import subprocess
import textwrap

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from agent_factory.state import read_review_verdict

DOCKERFILE_TEMPLATE = textwrap.dedent(
    """\
    FROM python:3.12-slim
    WORKDIR /app
    COPY {agent_filename} ./{agent_filename}
    COPY requirements.txt ./requirements.txt
    RUN pip install --no-cache-dir -r requirements.txt
    ENTRYPOINT ["python", "{agent_filename}"]
    """
)


class DeployAgentInput(BaseModel):
    agent_filename: str = Field(
        ..., description="Имя файла сгенерированного агента в OUTPUT_DIR, например my_agent.py"
    )
    image_tag: str = Field(..., description="Тег для docker-образа, например agent-rss-monitor")
    extra_requirements: str = Field(
        "", description="Доп. pip-зависимости через пробел сверх crewai/python-dotenv"
    )


class DeployGeneratedAgentTool(BaseTool):
    name: str = "deploy_generated_agent"
    description: str = (
        "Собирает Docker-образ для сгенерированного агента (docker build) и "
        "запускает контейнер (docker run -d) с переменными окружения из .env "
        "фабрики (если файл .env есть в текущей директории). Требует "
        "установленный и запущенный Docker на хосте. Инструмент САМ проверяет "
        "реальный вердикт ревью (не доверяет тому, что скажет вызывающий агент) "
        "и физически откажется деплоить, если ревью не APPROVED."
    )
    args_schema: type[BaseModel] = DeployAgentInput

    def _run(self, agent_filename: str, image_tag: str, extra_requirements: str = "") -> str:
        verdict = read_review_verdict()
        if verdict is None:
            return "ОШИБКА: деплой заблокирован — вердикт ревью ещё не зафиксирован в этом прогоне."
        if verdict["verdict"] != "APPROVED":
            issues = "; ".join(verdict.get("issues") or []) or "без деталей"
            return f"ОШИБКА: деплой заблокирован — ревью вернуло CHANGES_REQUESTED ({issues})."

        output_dir = os.path.abspath(os.environ.get("OUTPUT_DIR", "./generated_agents"))
        agent_path = os.path.join(output_dir, os.path.basename(agent_filename))
        if not os.path.isfile(agent_path):
            return (
                f"ОШИБКА: файл агента не найден: {agent_path}. "
                "Сначала сохрани код инструментом save_generated_agent."
            )

        bundle_name = "_bundle_" + os.path.splitext(os.path.basename(agent_filename))[0]
        bundle_dir = os.path.join(output_dir, bundle_name)
        os.makedirs(bundle_dir, exist_ok=True)

        with open(agent_path, "r", encoding="utf-8") as src:
            code = src.read()
        with open(os.path.join(bundle_dir, os.path.basename(agent_filename)), "w", encoding="utf-8") as dst:
            dst.write(code)

        requirements = ["crewai", "python-dotenv"]
        if extra_requirements.strip():
            requirements.extend(extra_requirements.split())
        with open(os.path.join(bundle_dir, "requirements.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(requirements) + "\n")

        dockerfile = DOCKERFILE_TEMPLATE.format(agent_filename=os.path.basename(agent_filename))
        with open(os.path.join(bundle_dir, "Dockerfile"), "w", encoding="utf-8") as f:
            f.write(dockerfile)

        safe_tag = "".join(c if c.isalnum() or c in "-_." else "-" for c in image_tag.lower())

        try:
            build = subprocess.run(
                ["docker", "build", "-t", safe_tag, bundle_dir],
                capture_output=True,
                text=True,
                timeout=600,
            )
        except FileNotFoundError:
            return "ОШИБКА: команда docker не найдена на хосте. Установите Docker и повторите."
        except subprocess.TimeoutExpired:
            return "ОШИБКА: docker build превысил таймаут (600с)."

        if build.returncode != 0:
            return f"ОШИБКА docker build:\n{build.stderr[-2000:]}"

        env_file_arg = ["--env-file", ".env"] if os.path.isfile(".env") else []

        try:
            run = subprocess.run(
                ["docker", "run", "-d", "--rm", "--name", safe_tag, *env_file_arg, safe_tag],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            return f"Образ {safe_tag} собран, но docker run превысил таймаут (60с)."

        if run.returncode != 0:
            return f"Образ собран ({safe_tag}), но docker run упал:\n{run.stderr[-2000:]}"

        return f"OK: образ {safe_tag} собран и запущен, container_id={run.stdout.strip()}"
