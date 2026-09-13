"""Helpers for reading a CrewOutput once a crew has finished running."""

REFLECTION_TASK_NAME = "reflect_task"


def deliverable_output(result) -> str:
    """Return the crew's real deliverable, not the trailing self-learning reflection.

    Every department appends a reflect_task (LLM-as-judge score + saved
    lessons) after its actual output so agents keep learning between runs.
    CrewOutput.raw is simply the *last* task's raw text, which hands back
    the judge's verdict instead of the finished website/post/code/review.
    Skip the reflection task and return the last task that isn't it.
    """
    for task_output in reversed(result.tasks_output):
        if task_output.name != REFLECTION_TASK_NAME:
            return task_output.raw
    return result.raw
