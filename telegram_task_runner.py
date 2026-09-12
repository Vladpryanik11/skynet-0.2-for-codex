"""Run one SKYNET Telegram task in a separate process."""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

load_dotenv()

from institute.router import route_and_run  # noqa: E402

RUNNER_RESULT_START = "<<<SKYNET_RESULT_START>>>"
RUNNER_RESULT_END = "<<<SKYNET_RESULT_END>>>"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one SKYNET task for telegram_bot.py")
    parser.add_argument(
        "--mode",
        choices=("auto", "coders", "marketing", "design"),
        default="auto",
        help="Work mode selected in Telegram.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    user_request = sys.stdin.read().strip()
    if not user_request:
        raise SystemExit("Empty SKYNET request.")

    department_override = None if args.mode == "auto" else args.mode
    result = route_and_run(user_request, department_override=department_override)

    print(RUNNER_RESULT_START, flush=True)
    print(result, flush=True)
    print(RUNNER_RESULT_END, flush=True)


if __name__ == "__main__":
    main()
