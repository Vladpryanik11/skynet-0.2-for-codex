# Режимы работы SKYNET

SKYNET 0.2 поддерживает три режима через переменную `SKYNET_MODE`.

## 1. Local

Без API-ключей и без платных моделей.

```env
SKYNET_MODE=local
LOCAL_DEFAULT_MODEL=ollama/llama3.1:8b
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
```

Что нужно установить один раз:

```bash
ollama pull llama3.1:8b
```

Запуск:

```bash
python run.py "напиши пост для соцсетей"
```

Ограничения local-режима:

- качество ниже, чем у Claude/GPT;
- vision-анализ изображений отключён без облачного ключа;
- сложный код лучше проверять вручную;
- скорость зависит от железа.

## 2. Cloud

Работает через Claude/GPT API.

```env
SKYNET_MODE=cloud
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
```

Подходит для сложного кода, дизайна, анализа референсов и строгого QA.

## 3. Hybrid

Лучший рабочий режим для развития проекта:

```env
SKYNET_MODE=hybrid
LOCAL_DEFAULT_MODEL=ollama/llama3.1:8b
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
```

Логика:

- если ключи есть — используются облачные модели;
- если ключей нет — система автоматически падает в локальный режим;
- отдельные роли можно переключать вручную:

```env
CODERS_CODER_MODEL=ollama/deepseek-coder:6.7b
COPYWRITER_MODEL=ollama/llama3.1:8b
DESIGN_SYSTEM_MODEL=anthropic/claude-sonnet-5
```

## Claude Pro без API

Если есть Claude Pro, но нет платного Anthropic API, используй `SKYNET_MODE=local`.
Claude Pro в этой схеме — не автоматический LLM-провайдер внутри CrewAI, а внешний
усилитель через Claude Web или Claude Code.

Подробнее: `docs/CLAUDE_PRO_NO_API.md`.

## Рекомендуемые бесплатные локальные модели

```bash
ollama pull llama3.1:8b
ollama pull qwen2.5-coder:7b
ollama pull deepseek-coder:6.7b
```

Для слабого ПК:

```bash
ollama pull llama3.2:3b
```
