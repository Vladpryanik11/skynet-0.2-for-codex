"""Local lesson loading with an optional cloud knowledge index."""

import os

from institute.local_mode import skynet_mode


def lesson_context(department: str, limit: int = 6000) -> str:
    path = os.path.join(os.environ.get("KNOWLEDGE_DIR", "./knowledge"), f"{department}_lessons.md")
    if not os.path.isfile(path):
        return "Накопленных уроков пока нет."
    with open(path, encoding="utf-8") as file:
        content = file.read().strip()
    return content[-limit:] if content else "Накопленных уроков пока нет."


def knowledge_sources_for(department: str):
    """Use CrewAI embeddings only when the user explicitly has a cloud key."""
    if skynet_mode() == "local" or not os.environ.get("OPENAI_API_KEY"):
        return []

    from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource

    path = os.path.abspath(
        os.path.join(os.environ.get("KNOWLEDGE_DIR", "./knowledge"), f"{department}_lessons.md")
    )
    if not os.path.isfile(path):
        return []
    return [TextFileKnowledgeSource(file_paths=[path])]
