import sys

from dotenv import load_dotenv

load_dotenv()

from agent_factory.crew import AgentFactoryCrew  # noqa: E402
from institute.crew_output import deliverable_output  # noqa: E402
from institute.knowledge import lesson_context  # noqa: E402


def main() -> None:
    if len(sys.argv) > 1:
        user_request = " ".join(sys.argv[1:])
    else:
        user_request = input("Опишите, какого агента нужно создать: ").strip()

    result = AgentFactoryCrew().crew().kickoff(
        inputs={
            "user_request": user_request,
            "department_knowledge": lesson_context("coders"),
        }
    )
    print("\n=== ИТОГ ===\n")
    print(deliverable_output(result))


if __name__ == "__main__":
    main()
