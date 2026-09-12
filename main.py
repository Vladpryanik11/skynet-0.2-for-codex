import sys

from dotenv import load_dotenv

load_dotenv()

from agent_factory.crew import AgentFactoryCrew  # noqa: E402


def main() -> None:
    if len(sys.argv) > 1:
        user_request = " ".join(sys.argv[1:])
    else:
        user_request = input("Опишите, какого агента нужно создать: ").strip()

    result = AgentFactoryCrew().crew().kickoff(inputs={"user_request": user_request})
    print("\n=== ИТОГ ===\n")
    print(result.raw)


if __name__ == "__main__":
    main()
