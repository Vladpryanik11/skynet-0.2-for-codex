#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/skynet}"
REPO_URL="${REPO_URL:-https://github.com/Vladpryanik11/skynet-0.2-for-codex.git}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "[1/8] Updating system packages"
apt-get update
apt-get install -y git curl ca-certificates python3 python3-venv python3-pip

echo "[2/8] Installing Docker if missing"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
fi

echo "[3/8] Installing Ollama if missing"
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi
systemctl enable ollama || true
systemctl start ollama || true

echo "[4/8] Pulling local models"
ollama pull llama3.1:8b || true
ollama pull qwen2.5-coder:7b || true

echo "[5/8] Cloning or updating SKYNET"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull --ff-only
else
  rm -rf "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
fi

echo "[6/8] Creating Python virtualenv"
cd "$APP_DIR"
$PYTHON_BIN -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .

echo "[7/8] Writing local/hybrid .env"
if [ -f .env ]; then
  cp .env ".env.backup.$(date +%Y%m%d%H%M%S)"
else
  cat > .env <<'ENV'
SKYNET_MODE=local
LOCAL_DEFAULT_MODEL=ollama/llama3.1:8b
DEFAULT_DEPARTMENT=design
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

CODERS_CODER_MODEL=ollama/qwen2.5-coder:7b
CODERS_REVIEWER_MODEL=ollama/qwen2.5-coder:7b
FRONTEND_CODER_MODEL=ollama/qwen2.5-coder:7b
DESIGN_SYSTEM_MODEL=ollama/llama3.1:8b

ENABLE_QUALITY_GATE=0
KNOWLEDGE_DIR=./knowledge
REFERENCES_DIR=./references
DESIGN_OUTPUT_DIR=./generated_designs
OUTPUT_DIR=./generated_agents
TRACES_DIR=./traces
RUNS_DIR=./runs
STATE_DIR=./.state

TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USER_IDS=
TELEGRAM_TASK_QUEUE_SIZE=20

GENERATED_AGENT_ENV_ALLOWLIST=ANTHROPIC_API_KEY,OPENAI_API_KEY,SERPER_API_KEY
GENERATED_AGENT_MEMORY=512m
GENERATED_AGENT_CPUS=1.0
GENERATED_AGENT_NETWORK=bridge
ENV
fi

echo "[8/8] Done"
echo "Run:"
echo "  cd $APP_DIR"
echo "  source .venv/bin/activate"
echo "  python run.py \"создай лендинг для ИИ-агентства\""
echo "  python telegram_bot.py"
