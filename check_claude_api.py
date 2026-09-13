"""Быстрая проверка, что ANTHROPIC_API_KEY из .env валиден.
Не гоняет всю команду агентов — один минимальный запрос к Claude.
"""
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()  # берёт ключ из ANTHROPIC_API_KEY автоматически
model = os.environ.get("ROUTER_MODEL", "claude-haiku-4-5")

try:
    response = client.messages.create(
        model=model,
        max_tokens=32,
        messages=[{"role": "user", "content": "Ответь одним словом: работаешь?"}],
    )
    text = next((b.text for b in response.content if b.type == "text"), None)
    if text is None:
        print(f"ОШИБКА: модель {model} не вернула текстовый ответ: {response.content!r}")
    else:
        print(f"OK: ключ рабочий, ответ модели: {text!r}")
except anthropic.AuthenticationError:
    print("ОШИБКА: ключ недействителен — проверьте ANTHROPIC_API_KEY в .env")
except anthropic.APIConnectionError:
    print("ОШИБКА: нет сети / не удалось достучаться до api.anthropic.com")
except anthropic.AnthropicError as exc:
    print(f"ОШИБКА: Anthropic API вернул ошибку ({type(exc).__name__}): {exc}")
