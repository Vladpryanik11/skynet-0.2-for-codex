# Настройка сервера для SKYNET

## Почему Codex не вошёл сам

Из текущего Work-окружения сеть до сервера недоступна:

```text
Network is unreachable
```

Поэтому настройку нужно запустить с твоего компьютера по SSH.

## 1. Подключиться к серверу

В PowerShell:

```powershell
ssh root@144.31.192.91
```

Введи пароль от сервера.

## 2. Запустить базовую установку

На сервере:

```bash
curl -fsSL https://raw.githubusercontent.com/Vladpryanik11/skynet-0.2-for-codex/main/scripts/server_bootstrap.sh -o /tmp/server_bootstrap.sh
REPO_URL=https://github.com/Vladpryanik11/skynet-0.2-for-codex.git bash /tmp/server_bootstrap.sh
```

Если файла ещё нет в GitHub, загрузи локальную версию:

```powershell
scp scripts/server_bootstrap.sh root@144.31.192.91:/tmp/server_bootstrap.sh
ssh root@144.31.192.91 "bash /tmp/server_bootstrap.sh"
```

## Telegram-бот

После базовой установки добавь токен в `/opt/skynet/.env`:

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_ALLOWED_USER_IDS=
```

Запуск вручную:

```bash
cd /opt/skynet
source .venv/bin/activate
python telegram_bot.py
```

Автозапуск через systemd:

```bash
cd /opt/skynet
bash scripts/install_telegram_bot_service.sh
```

## 3. Запустить SKYNET

На сервере:

```bash
cd /opt/skynet
source .venv/bin/activate
python run.py "создай лендинг для ИИ-агентства: белый фон, голубые акценты, стеклянные карточки, услуги SMM, маркетинг, видеопродакшн, IT"
```

## 4. Где будет сайт

Дизайн-отдел сохраняет результат в:

```text
/opt/skynet/generated_designs/<project>/index.html
```

## 5. Режим без платного API

Сервер будет настроен в local-режиме:

```env
SKYNET_MODE=local
LOCAL_DEFAULT_MODEL=ollama/llama3.1:8b
```

Claude Pro не используется как API. Его можно применять отдельно через Claude Web/Claude Code для ручного усиления сложных задач.

## 6. После настройки

Сразу поменяй root-пароль:

```bash
passwd
```

Затем лучше перейти на SSH-ключи и отключить вход по паролю.
