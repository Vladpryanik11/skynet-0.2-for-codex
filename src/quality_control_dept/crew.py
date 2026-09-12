import os

from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, crew, task

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
class QualityControlCrew:
    """Отдел контроля качества: проверяет итог другого отдела перед выдачей."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def requirements_auditor(self) -> Agent:
        return Agent(
            config=self.agents_config["requirements_auditor"],
            llm=_llm("QC_REQUIREMENTS_MODEL", "anthropic/claude-sonnet-5"),
            verbose=True,
            **agent_runtime_kwargs(),
        )

    @agent
    def risk_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["risk_reviewer"],
            llm=_llm("QC_RISK_MODEL", "anthropic/claude-sonnet-5"),
            verbose=True,
            **agent_runtime_kwargs(),
        )

    @agent
    def final_editor(self) -> Agent:
        return Agent(
            config=self.agents_config["final_editor"],
            llm=_llm("QC_FINAL_EDITOR_MODEL", "anthropic/claude-sonnet-5"),
            tools=[JudgeOutputTool()],
            verbose=True,
            **agent_runtime_kwargs(),
        )

    @agent
    def learner(self) -> Agent:
        return Agent(
            config=self.agents_config["learner"],
            llm=_llm("QC_LEARNER_MODEL", "anthropic/claude-haiku-4-5"),
            tools=[RecordLessonTool(department="quality_control")],
            verbose=True,
            **agent_runtime_kwargs(),
        )

    @task
    def requirements_check_task(self) -> Task:
        return Task(config=self.tasks_config["requirements_check_task"])

    @task
    def risk_check_task(self) -> Task:
        return Task(config=self.tasks_config["risk_check_task"])

    @task
    def final_verdict_task(self) -> Task:
        return Task(config=self.tasks_config["final_verdict_task"])

    @task
    def reflect_task(self) -> Task:
        return Task(config=self.tasks_config["reflect_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            memory=crew_memory_enabled(),
            knowledge_sources=knowledge_sources_for("quality_control"),
            task_callback=make_task_tracer("quality_control"),
            verbose=True,
        )
