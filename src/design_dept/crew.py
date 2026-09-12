import os

from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, crew, task

from design_dept.tools import AnalyzeReferencesTool, SaveDesignFileTool
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
class DesignCrew:
    """Отдел дизайна: разбирает референсы (vision), собирает дизайн-систему,
    вёрстает готовую HTML/CSS-страницу и проверяет её перед сдачей."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def reference_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["reference_analyst"],
            llm=_llm("REFERENCE_ANALYST_MODEL", "anthropic/claude-sonnet-5"),
            tools=[AnalyzeReferencesTool()],
            verbose=True,
            **agent_runtime_kwargs(),
        )

    @agent
    def design_system_architect(self) -> Agent:
        return Agent(
            config=self.agents_config["design_system_architect"],
            llm=_llm("DESIGN_SYSTEM_MODEL", "anthropic/claude-opus-5"),
            tools=[SaveDesignFileTool()],
            verbose=True,
            **agent_runtime_kwargs(),
        )

    @agent
    def frontend_coder(self) -> Agent:
        return Agent(
            config=self.agents_config["frontend_coder"],
            llm=_llm("FRONTEND_CODER_MODEL", "anthropic/claude-opus-5"),
            tools=[SaveDesignFileTool()],
            verbose=True,
            **agent_runtime_kwargs(),
        )

    @agent
    def design_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["design_reviewer"],
            llm=_llm("DESIGN_REVIEWER_MODEL", "anthropic/claude-sonnet-5"),
            verbose=True,
            **agent_runtime_kwargs(),
        )

    @agent
    def learner(self) -> Agent:
        return Agent(
            config=self.agents_config["learner"],
            llm=_llm("DESIGN_LEARNER_MODEL", "anthropic/claude-haiku-4-5"),
            tools=[JudgeOutputTool(), RecordLessonTool(department="design")],
            verbose=True,
            **agent_runtime_kwargs(),
        )

    @task
    def analyze_references_task(self) -> Task:
        return Task(config=self.tasks_config["analyze_references_task"])

    @task
    def design_system_task(self) -> Task:
        return Task(config=self.tasks_config["design_system_task"])

    @task
    def build_page_task(self) -> Task:
        return Task(config=self.tasks_config["build_page_task"])

    @task
    def review_design_task(self) -> Task:
        return Task(config=self.tasks_config["review_design_task"])

    @task
    def reflect_task(self) -> Task:
        return Task(config=self.tasks_config["reflect_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # reference_analyst, design_system_architect,
            # frontend_coder, design_reviewer, learner
            tasks=self.tasks,
            process=Process.sequential,
            memory=crew_memory_enabled(),
            knowledge_sources=knowledge_sources_for("design"),
            task_callback=make_task_tracer("design"),
            verbose=True,
        )
