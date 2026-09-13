# Настройка сервера для SKYNET

Рекомендуемый режим для маленького VPS — `cloud`: Telegram-бот живёт на
сервере, а генерация ответов идёт через OpenAI API. Так сервер не тратит CPU и
RAM на локальную Ollama-модель.

## 1. Подключиться к серверу

В PowerShell:

```powershell
ssh root@<server-ip>
```

## 2. Запустить базовую установку

На сервере:

```bash
curl -fsSL https://raw.githubusercontent.com/Vladpryanik11/skynet-0.2-for-codex/main/scripts/server_bootstrap.sh -o /tmp/server_bootstrap.sh
REPO_URL=https://github.com/Vladpryanik11/skynet-0.2-for-codex.git bash /tmp/server_bootstrap.sh
```

По умолчанию скрипт не ставит Ollama. Если нужен полностью локальный режим:

```bash
INSTALL_OLLAMA=1 SKYNET_MODE=local bash /tmp/server_bootstrap.sh
```

## 3. Настроить `.env`

После установки добавь в `/opt/skynet/.env` ключи:

```env
OPENAI_API_KEY=...
TELEGRAM_BOT_TOKEN=...
```

Рекомендуемые настройки для Telegram:

```env
SKYNET_MODE=cloud
CLOUD_DEFAULT_MODEL=openai/gpt-4o-mini
OPENAI_DEFAULT_MODEL=gpt-4o-mini
DEFAULT_DEPARTMENT=marketing

TELEGRAM_TASK_QUEUE_SIZE=10
TELEGRAM_DEFAULT_MODE=fast
FAST_MODE_PROVIDER=auto
OPENAI_FAST_MODEL=gpt-4o-mini
OPENAI_MODEL_FALLBACKS=gpt-4.1-mini,gpt-4o-mini
TELEGRAM_TASK_TIMEOUT=300
TELEGRAM_PROGRESS_INTERVAL=5
FAST_MODE_TIMEOUT=90
FAST_MODE_NUM_PREDICT=384
```

## 4. Запустить Telegram-бота

Автозапуск через systemd:

```bash
cd /opt/skynet
bash scripts/install_telegram_bot_service.sh
systemctl restart skynet-telegram-bot
systemctl status skynet-telegram-bot
```

В Telegram доступны `/mode` с кнопками режимов Быстрый, Авто, Кодеры,
Маркетинг и Дизайн, а также `/status`.

- Быстрый режим отвечает одним прямым вызовом OpenAI API.
- Авто/Кодеры/Маркетинг/Дизайн запускают полный агентный конвейер.
- Бот обновляет сообщение с процентом готовности и присылает длинные ответы
  частями.

## 5. Проверка

```bash
cd /opt/skynet
source .venv/bin/activate
printf 'Ответь одним коротким предложением: тест скорости.' | python telegram_task_runner.py --mode fast
```

## 6. Режим без API

Если принципиально нужен запуск без OpenAI API, включи локальный режим:

```env
SKYNET_MODE=local
LOCAL_DEFAULT_MODEL=ollama/llama3.2:1b
FAST_MODE_PROVIDER=ollama
```

Для него серверу нужны заметно большие ресурсы, чем 1 GB RAM.
