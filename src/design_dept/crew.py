import os

from crewai import Agent, Crew, LLM, Process, Task
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from crewai.project import CrewBase, agent, crew, task

from design_dept.tools import AnalyzeReferencesTool, SaveDesignFileTool
from institute.learning_tools import RecordLessonTool


def _llm(env_var: str, default: str) -> LLM:
    return LLM(model=os.environ.get(env_var, default))


@CrewBase
class DesignCrew:
    """Отдел дизайна: разбирает референсы (vision), собирает дизайн-систему,
    вёрстает готовую HTML/CSS-страницу и проверяет её перед сдачей."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def department_orchestrator_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["department_orchestrator"],
            llm=_llm("DESIGN_ORCHESTRATOR_MODEL", "anthropic/claude-sonnet-5"),
            allow_delegation=True,
            verbose=True,
        )

    @agent
    def reference_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["reference_analyst"],
            llm=_llm("REFERENCE_ANALYST_MODEL", "anthropic/claude-sonnet-5"),
            tools=[AnalyzeReferencesTool()],
            verbose=True,
        )

    @agent
    def design_system_architect(self) -> Agent:
        return Agent(
            config=self.agents_config["design_system_architect"],
            llm=_llm("DESIGN_SYSTEM_MODEL", "anthropic/claude-opus-5"),
            tools=[SaveDesignFileTool()],
            verbose=True,
        )

    @agent
    def frontend_coder(self) -> Agent:
        return Agent(
            config=self.agents_config["frontend_coder"],
            llm=_llm("FRONTEND_CODER_MODEL", "anthropic/claude-opus-5"),
            tools=[SaveDesignFileTool()],
            verbose=True,
        )

    @agent
    def design_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["design_reviewer"],
            llm=_llm("DESIGN_REVIEWER_MODEL", "anthropic/claude-sonnet-5"),
            verbose=True,
        )

    @agent
    def learner(self) -> Agent:
        return Agent(
            config=self.agents_config["learner"],
            llm=_llm("DESIGN_LEARNER_MODEL", "anthropic/claude-haiku-4-5"),
            tools=[RecordLessonTool(department="design")],
            verbose=True,
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
            process=Process.hierarchical,
            manager_agent=self.department_orchestrator_agent(),
            memory=True,
            knowledge_sources=[TextFileKnowledgeSource(file_paths=["design_lessons.md"])],
            verbose=True,
        )
