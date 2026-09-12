import os

from crewai import Agent, Crew, LLM, Process, Task
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from crewai.project import CrewBase, agent, crew, task

from institute.learning_tools import RecordLessonTool


def _llm(env_var: str, default: str) -> LLM:
    return LLM(model=os.environ.get(env_var, default))


@CrewBase
class MarketingCrew:
    """Отдел маркетинга: превращает запрос в бриф, пишет текст,
    при необходимости добавляет SEO и финально вычитывает."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def department_orchestrator_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["department_orchestrator"],
            llm=_llm("MARKETING_ORCHESTRATOR_MODEL", "anthropic/claude-sonnet-5"),
            allow_delegation=True,
            verbose=True,
        )

    @agent
    def strategist(self) -> Agent:
        return Agent(
            config=self.agents_config["strategist"],
            llm=_llm("STRATEGIST_MODEL", "anthropic/claude-sonnet-5"),
            verbose=True,
        )

    @agent
    def copywriter(self) -> Agent:
        return Agent(
            config=self.agents_config["copywriter"],
            llm=_llm("COPYWRITER_MODEL", "anthropic/claude-opus-5"),
            verbose=True,
        )

    @agent
    def seo_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config["seo_specialist"],
            llm=_llm("SEO_MODEL", "anthropic/claude-sonnet-5"),
            verbose=True,
        )

    @agent
    def editor(self) -> Agent:
        return Agent(
            config=self.agents_config["editor"],
            llm=_llm("EDITOR_MODEL", "anthropic/claude-sonnet-5"),
            verbose=True,
        )

    @agent
    def learner(self) -> Agent:
        return Agent(
            config=self.agents_config["learner"],
            llm=_llm("MARKETING_LEARNER_MODEL", "anthropic/claude-haiku-4-5"),
            tools=[RecordLessonTool(department="marketing")],
            verbose=True,
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
        return Task(config=self.tasks_config["reflect_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # strategist, copywriter, seo_specialist, editor, learner
            tasks=self.tasks,
            process=Process.hierarchical,
            manager_agent=self.department_orchestrator_agent(),
            memory=True,
            knowledge_sources=[TextFileKnowledgeSource(file_paths=["marketing_lessons.md"])],
            verbose=True,
        )
