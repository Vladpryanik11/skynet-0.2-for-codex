import os

from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, crew, task

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


@CrewBase
class MarketingCrew:
    """Отдел маркетинга: превращает запрос в бриф, пишет текст,
    при необходимости добавляет SEO и финально вычитывает."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def strategist(self) -> Agent:
        return Agent(
            config=self.agents_config["strategist"],
            llm=_llm("STRATEGIST_MODEL", "anthropic/claude-sonnet-5"),
            verbose=True,
            **agent_runtime_kwargs(),
        )

    @agent
    def copywriter(self) -> Agent:
        return Agent(
            config=self.agents_config["copywriter"],
            llm=_llm("COPYWRITER_MODEL", "anthropic/claude-opus-5"),
            verbose=True,
            **agent_runtime_kwargs(),
        )

    @agent
    def seo_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config["seo_specialist"],
            llm=_llm("SEO_MODEL", "anthropic/claude-sonnet-5"),
            verbose=True,
            **agent_runtime_kwargs(),
        )

    @agent
    def editor(self) -> Agent:
        return Agent(
            config=self.agents_config["editor"],
            llm=_llm("EDITOR_MODEL", "anthropic/claude-sonnet-5"),
            verbose=True,
            **agent_runtime_kwargs(),
        )

    @agent
    def learner(self) -> Agent:
        return Agent(
            config=self.agents_config["learner"],
            llm=_llm("MARKETING_LEARNER_MODEL", "anthropic/claude-haiku-4-5"),
            tools=[JudgeOutputTool(), RecordLessonTool(department="marketing")],
            verbose=True,
            **agent_runtime_kwargs(),
        )

    @task
    def brief_task(self) -> Task:
        return Task(config=self.tasks_config["brief_task"])

    @task
    def draft_copy_task(self) -> Task:
        return Task(config=self.tasks_config["draft_copy_task"])

    @task
    def seo_task(self) -> Task:
        return Task(config=self.tasks_config["seo_task"])

    @task
    def edit_task(self) -> Task:
        return Task(config=self.tasks_config["edit_task"])

    @task
    def reflect_task(self) -> Task:
        return Task(config=self.tasks_config["reflect_task"], name=REFLECTION_TASK_NAME)

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # strategist, copywriter, seo_specialist, editor, learner
            tasks=self.tasks,
            process=Process.sequential,
            memory=crew_memory_enabled(),
            knowledge_sources=knowledge_sources_for("marketing"),
            task_callback=make_task_tracer("marketing"),
            verbose=True,
        )
