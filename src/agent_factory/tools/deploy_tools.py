import os
import subprocess
import textwrap

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from agent_factory.state import read_review_verdict
from institute.safety import build_env_args, resolve_inside_dir, safe_docker_tag

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


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name, "1" if default else "0").strip().lower()
    return value in {"1", "true", "yes", "on"}


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
        if not _bool_env("ENABLE_AGENT_DEPLOY"):
            return (
                "ОШИБКА: автодеплой выключен на этом хосте (ENABLE_AGENT_DEPLOY не "
                "включён в .env). Это осознанный барьер: без него любой вход в "
                "отдел Кодеров (в т.ч. через открытый Telegram-бот) мог бы дойти "
                "до реального docker build/run на сервере. Включите переменную "
                "явно, если вы понимаете последствия."
            )

        verdict = read_review_verdict()
        if verdict is None:
            return "ОШИБКА: деплой заблокирован — вердикт ревью ещё не зафиксирован в этом прогоне."
        if verdict["verdict"] != "APPROVED":
            issues = "; ".join(verdict.get("issues") or []) or "без деталей"
            return f"ОШИБКА: деплой заблокирован — ревью вернуло CHANGES_REQUESTED ({issues})."

        output_dir = os.path.abspath(os.environ.get("OUTPUT_DIR", "./generated_agents"))
        try:
            agent_path = resolve_inside_dir(output_dir, agent_filename)
        except ValueError as exc:
            return f"ОШИБКА: небезопасный путь к агенту: {exc}"
        if not os.path.isfile(agent_path):
            return (
                f"ОШИБКА: файл агента не найден: {agent_path}. "
                "Сначала сохрани код инструментом save_generated_agent."
            )

        bundle_name = "_bundle_" + os.path.splitext(os.path.basename(agent_path))[0]
        bundle_dir = os.path.join(output_dir, bundle_name)
        os.makedirs(bundle_dir, exist_ok=True)

        with open(agent_path, "r", encoding="utf-8") as src:
            code = src.read()
        agent_basename = os.path.basename(agent_path)
        with open(os.path.join(bundle_dir, agent_basename), "w", encoding="utf-8") as dst:
            dst.write(code)

        requirements = ["crewai", "python-dotenv"]
        if extra_requirements.strip():
            requirements.extend(extra_requirements.split())
        with open(os.path.join(bundle_dir, "requirements.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(requirements) + "\n")

        dockerfile = DOCKERFILE_TEMPLATE.format(agent_filename=agent_basename)
        with open(os.path.join(bundle_dir, "Dockerfile"), "w", encoding="utf-8") as f:
            f.write(dockerfile)

        safe_tag = safe_docker_tag(image_tag)

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

        env_args = build_env_args()
        memory_limit = os.environ.get("GENERATED_AGENT_MEMORY", "512m")
        cpu_limit = os.environ.get("GENERATED_AGENT_CPUS", "1.0")
        network_mode = os.environ.get("GENERATED_AGENT_NETWORK", "bridge")

        # Re-deploying the same image_tag while the previous container is
        # still alive would otherwise fail docker run with "name already
        # in use"; clear it first (best-effort, ignores "not found").
        subprocess.run(
            ["docker", "rm", "-f", safe_tag],
            capture_output=True,
            text=True,
            timeout=30,
        )

        try:
            run = subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--rm",
                    "--name",
                    safe_tag,
                    "--memory",
                    memory_limit,
                    "--cpus",
                    cpu_limit,
                    "--network",
                    network_mode,
                    *env_args,
                    safe_tag,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            return f"Образ {safe_tag} собран, но docker run превысил таймаут (60с)."

        if run.returncode != 0:
            return f"Образ собран ({safe_tag}), но docker run упал:\n{run.stderr[-2000:]}"

        return f"OK: образ {safe_tag} собран и запущен, container_id={run.stdout.strip()}"
