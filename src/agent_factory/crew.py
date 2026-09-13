import os

from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, before_kickoff, crew, task

from agent_factory.models import ReviewVerdict
from agent_factory.state import clear_review_verdict, write_review_verdict
from agent_factory.tools import (
    DangerousPatternScanTool,
    DeployGeneratedAgentTool,
    PythonSyntaxCheckTool,
    SaveGeneratedAgentTool,
)
from institute.crew_output import REFLECTION_TASK_NAME
from institute.eval_tools import JudgeOutputTool
from institute.learning_tools import RecordLessonTool
from institute.knowledge import knowledge_sources_for
from institute.local_mode import model_from_env
from institute.runtime import agent_runtime_kwargs, crew_memory_enabled
from institute.tracing import make_task_tracer


def _llm(env_var: str, default: str) -> LLM:
    model = model_from_env(env_var, default)
    if model.startswith(("ollama/", "ollama_chat/")):
        return LLM(
            model=model,
            is_litellm=True,
            base_url=os.environ.get("OLLAMA_API_BASE", "http://127.0.0.1:11434"),
        )
    return LLM(model=model)


def _researcher_tools() -> list:
    """SerperDevTool needs SERPER_API_KEY; without it the researcher falls
    back to the model's own knowledge instead of failing outright."""
    if not os.environ.get("SERPER_API_KEY", "").strip():
        return []
    from crewai_tools import SerperDevTool

    return [SerperDevTool()]


def _record_review_verdict(task_output) -> None:
    """callback на review_code_task: пишет структурированный вердикт в
    .state/, откуда его без доверия к агенту читает DeployGeneratedAgentTool."""
    verdict_obj = getattr(task_output, "pydantic", None)
    if verdict_obj is None:
        write_review_verdict(
            "CHANGES_REQUESTED",
            ["Ревьюер не вернул структурированный вердикт — деплой заблокирован для безопасности."],
        )
        return
    write_review_verdict(verdict_obj.verdict, verdict_obj.issues)


@CrewBase
class AgentFactoryCrew:
    """Команда, которая по текстовому запросу проектирует, пишет,
    проверяет и готовит к деплою нового CrewAI-агента."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @before_kickoff
    def _reset_state(self, inputs):
        clear_review_verdict()
        return inputs

    # --- Рабочие агенты ---
    @agent
    def architect(self) -> Agent:
        return Agent(
            config=self.agents_config["architect"],
            llm=_llm("CODERS_ARCHITECT_MODEL", "anthropic/claude-opus-5"),
            verbose=True,
            **agent_runtime_kwargs(),
        )

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["researcher"],
            llm=_llm("CODERS_RESEARCHER_MODEL", "openai/gpt-5"),
            tools=_researcher_tools(),
            verbose=True,
            **agent_runtime_kwargs(),
        )

    @agent
    def coder(self) -> Agent:
        return Agent(
            config=self.agents_config["coder"],
            llm=_llm("CODERS_CODER_MODEL", "anthropic/claude-sonnet-5"),
            tools=[SaveGeneratedAgentTool()],
            verbose=True,
            **agent_runtime_kwargs(),
        )

    @agent
    def reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["reviewer"],
            llm=_llm("CODERS_REVIEWER_MODEL", "anthropic/claude-sonnet-5"),
            tools=[PythonSyntaxCheckTool(), DangerousPatternScanTool()],
            verbose=True,
            **agent_runtime_kwargs(),
        )

    @agent
    def devops(self) -> Agent:
        return Agent(
            config=self.agents_config["devops"],
            llm=_llm("CODERS_DEVOPS_MODEL", "openai/gpt-5-mini"),
            tools=[DeployGeneratedAgentTool()],
            verbose=True,
            **agent_runtime_kwargs(),
        )

    @agent
    def learner(self) -> Agent:
        return Agent(
            config=self.agents_config["learner"],
            llm=_llm("CODERS_LEARNER_MODEL", "anthropic/claude-haiku-4-5"),
            tools=[JudgeOutputTool(), RecordLessonTool(department="coders")],
            verbose=True,
            **agent_runtime_kwargs(),
        )

    # --- Задачи ---
    @task
    def design_spec_task(self) -> Task:
        return Task(config=self.tasks_config["design_spec_task"])

    @task
    def research_task(self) -> Task:
        return Task(config=self.tasks_config["research_task"])

    @task
    def generate_agent_code_task(self) -> Task:
        return Task(config=self.tasks_config["generate_agent_code_task"])

    @task
    def review_code_task(self) -> Task:
        return Task(
            config=self.tasks_config["review_code_task"],
            output_pydantic=ReviewVerdict,
            callback=_record_review_verdict,
        )

    @task
    def prepare_deploy_task(self) -> Task:
        return Task(config=self.tasks_config["prepare_deploy_task"])

    @task
    def reflect_task(self) -> Task:
        return Task(config=self.tasks_config["reflect_task"], name=REFLECTION_TASK_NAME)

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # architect, researcher, coder, reviewer, devops, learner
            tasks=self.tasks,
            process=Process.sequential,
            memory=crew_memory_enabled(),
            knowledge_sources=knowledge_sources_for("coders"),
            task_callback=make_task_tracer("coders"),
            verbose=True,
        )
