#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/skynet}"
SERVICE_NAME="${SERVICE_NAME:-skynet-telegram-bot}"
SERVICE_USER="${SERVICE_USER:-}"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if [ -z "$SERVICE_USER" ]; then
  echo "SERVICE_USER is not set." >&2
  echo "This bot's Coders department can trigger real 'docker build'/'docker run'" >&2
  echo "on this host, so it should not default to running as root silently." >&2
  echo "Set SERVICE_USER to a dedicated non-root user (must be in the 'docker'" >&2
  echo "group), or export SERVICE_USER=root explicitly if you accept that risk." >&2
  exit 1
fi

if [ ! -d "$APP_DIR" ]; then
  echo "APP_DIR does not exist: $APP_DIR"
  exit 1
fi

if [ ! -x "$APP_DIR/.venv/bin/python" ]; then
  echo "Virtualenv python not found: $APP_DIR/.venv/bin/python"
  exit 1
fi

if [ ! -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
fi

if ! grep -q "^TELEGRAM_BOT_TOKEN=" "$APP_DIR/.env"; then
  printf "\nTELEGRAM_BOT_TOKEN=\n" >> "$APP_DIR/.env"
fi

if ! grep -Eq "^TELEGRAM_BOT_TOKEN=.+$" "$APP_DIR/.env"; then
  echo "Set TELEGRAM_BOT_TOKEN in $APP_DIR/.env before enabling the service."
  exit 1
fi

cat > "$SERVICE_FILE" <<SERVICE
[Unit]
Description=SKYNET Telegram Bot
After=network-online.target ollama.service
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/.venv/bin/python ${APP_DIR}/telegram_bot.py
Restart=always
RestartSec=10
User=${SERVICE_USER}

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"
systemctl --no-pager status "$SERVICE_NAME"
