# Режимы работы SKYNET

SKYNET 0.2 поддерживает три режима через переменную `SKYNET_MODE`.

## 1. Cloud

Рекомендуемый режим для Telegram-бота и VPS. Сервер принимает сообщения,
обновляет прогресс и хранит состояние, а генерация идёт через API.

```env
SKYNET_MODE=cloud
OPENAI_API_KEY=...
CLOUD_DEFAULT_MODEL=openai/gpt-4o-mini
OPENAI_FAST_MODEL=gpt-4o-mini
FAST_MODE_PROVIDER=auto
```

Если роль была настроена на Anthropic, но `ANTHROPIC_API_KEY` пустой и есть
`OPENAI_API_KEY`, SKYNET автоматически берёт `CLOUD_DEFAULT_MODEL`.

## 2. Local

Без API-ключей и без платных моделей. Нужна локальная Ollama-модель.

```env
SKYNET_MODE=local
LOCAL_DEFAULT_MODEL=ollama/llama3.2:1b
FAST_MODE_PROVIDER=ollama
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
```

Что нужно установить один раз:

```bash
ollama pull llama3.2:1b
```

Ограничения local-режима:

- качество ниже, чем у Claude/GPT;
- скорость зависит от CPU/RAM;
- 1 GB RAM для Ollama и CrewAI недостаточно для стабильной работы;
- vision-анализ изображений отключён без облачного ключа.

## 3. Hybrid

Режим для разработческой машины: если ключи есть, используются облачные модели,
если ключей нет, система падает в локальный режим.

```env
SKYNET_MODE=hybrid
OPENAI_API_KEY=
LOCAL_DEFAULT_MODEL=ollama/llama3.2:1b
```

Отдельные роли можно переключать вручную:

```env
CODERS_CODER_MODEL=openai/gpt-4o-mini
COPYWRITER_MODEL=openai/gpt-4o-mini
DESIGN_SYSTEM_MODEL=ollama/llama3.2:1b
```

## Telegram

Для быстрых сообщений:

```env
TELEGRAM_DEFAULT_MODE=fast
FAST_MODE_PROVIDER=auto
OPENAI_FAST_MODEL=gpt-4o-mini
FAST_MODE_NUM_PREDICT=384
```

Режим `fast` делает один прямой вызов модели. Режимы `auto`, `coders`,
`marketing` и `design` запускают полный многоагентный конвейер и поэтому
работают дольше.

## Claude Pro без API

Claude Pro не является API-ключом и не может автоматически питать CrewAI.
Его можно применять отдельно через Claude Web или Claude Code.

Подробнее: `docs/CLAUDE_PRO_NO_API.md`.
