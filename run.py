"""Точка входа в ИИ-институт целиком: определяет отдел под запрос и
запускает соответствующую команду (крю). Для прямого запуска только
отдела Кодеров без диспетчера — см. main.py.
"""
import sys

from dotenv import load_dotenv

load_dotenv()

from institute.router import route_and_run  # noqa: E402


def main() -> None:
    if len(sys.argv) > 1:
        user_request = " ".join(sys.argv[1:])
    else:
        user_request = input("Опишите задачу для института: ").strip()

    result = route_and_run(user_request)
    print("\n=== ИТОГ ===\n")
    print(result)


if __name__ == "__main__":
    main()
