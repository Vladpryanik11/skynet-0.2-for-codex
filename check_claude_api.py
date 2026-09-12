"""Быстрая проверка, что ANTHROPIC_API_KEY из .env валиден.
Не гоняет всю команду агентов — один минимальный запрос к Claude.
"""
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()  # берёт ключ из ANTHROPIC_API_KEY автоматически

try:
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=32,
        messages=[{"role": "user", "content": "Ответь одним словом: работаешь?"}],
    )
    text = next(b.text for b in response.content if b.type == "text")
    print(f"OK: ключ рабочий, ответ модели: {text!r}")
except anthropic.AuthenticationError:
    print("ОШИБКА: ключ недействителен — проверьте ANTHROPIC_API_KEY в .env")
except anthropic.APIConnectionError:
    print("ОШИБКА: нет сети / не удалось достучаться до api.anthropic.com")
