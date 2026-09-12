import os

from crewai import Agent, Crew, LLM, Process, Task
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from crewai.project import CrewBase, agent, crew, task

from agent_factory.tools import (
    DeployGeneratedAgentTool,
    PythonSyntaxCheckTool,
    SaveGeneratedAgentTool,
)
from institute.learning_tools import RecordLessonTool


def _llm(env_var: str, default: str) -> LLM:
    return LLM(model=os.environ.get(env_var, default))


@CrewBase
class AgentFactoryCrew:
    """Команда, которая по текстовому запросу проектирует, пишет,
    проверяет и готовит к деплою нового CrewAI-агента."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # --- Менеджер (НЕ входит в agents крю, используется как manager_agent) ---
    def orchestrator_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["orchestrator"],
            llm=_llm("CODERS_ORCHESTRATOR_MODEL", "anthropic/claude-sonnet-5"),
            allow_delegation=True,
            verbose=True,
        )

    # --- Рабочие агенты ---
    @agent
    def architect(self) -> Agent:
        return Agent(
            config=self.agents_config["architect"],
            llm=_llm("CODERS_ARCHITECT_MODEL", "anthropic/claude-opus-5"),
            verbose=True,
        )

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["researcher"],
            llm=_llm("CODERS_RESEARCHER_MODEL", "openai/gpt-5"),
            verbose=True,
        )

    @agent
    def coder(self) -> Agent:
        return Agent(
            config=self.agents_config["coder"],
            llm=_llm("CODERS_CODER_MODEL", "anthropic/claude-sonnet-5"),
            tools=[SaveGeneratedAgentTool()],
            verbose=True,
        )

    @agent
    def reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["reviewer"],
            llm=_llm("CODERS_REVIEWER_MODEL", "anthropic/claude-sonnet-5"),
            tools=[PythonSyntaxCheckTool()],
            verbose=True,
        )

    @agent
    def devops(self) -> Agent:
        return Agent(
            config=self.agents_config["devops"],
            llm=_llm("CODERS_DEVOPS_MODEL", "openai/gpt-5-mini"),
            tools=[DeployGeneratedAgentTool()],
            verbose=True,
        )

    @agent
    def learner(self) -> Agent:
        return Agent(
            config=self.agents_config["learner"],
            llm=_llm("CODERS_LEARNER_MODEL", "anthropic/claude-haiku-4-5"),
            tools=[RecordLessonTool(department="coders")],
            verbose=True,
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
        return Task(config=self.tasks_config["review_code_task"])

    @task
    def prepare_deploy_task(self) -> Task:
        return Task(config=self.tasks_config["prepare_deploy_task"])

    @task
    def reflect_task(self) -> Task:
        return Task(config=self.tasks_config["reflect_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # architect, researcher, coder, reviewer, devops, learner
            tasks=self.tasks,
            process=Process.hierarchical,
            manager_agent=self.orchestrator_agent(),
            memory=True,
            knowledge_sources=[TextFileKnowledgeSource(file_paths=["coders_lessons.md"])],
            verbose=True,
        )
