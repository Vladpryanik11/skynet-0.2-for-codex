#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/skynet}"
REPO_URL="${REPO_URL:-https://github.com/Vladpryanik11/skynet-0.2-for-codex.git}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_DOCKER="${INSTALL_DOCKER:-1}"
INSTALL_OLLAMA="${INSTALL_OLLAMA:-0}"
LOCAL_MODEL="${LOCAL_MODEL:-llama3.2:1b}"

echo "[1/8] Updating system packages"
apt-get update
apt-get install -y git curl ca-certificates python3 python3-venv python3-pip
apt-get clean || true

echo "[2/8] Installing Docker if enabled"
if [ "$INSTALL_DOCKER" = "1" ] && ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
fi

echo "[3/8] Installing Ollama only if requested"
if [ "$INSTALL_OLLAMA" = "1" ]; then
  if ! command -v ollama >/dev/null 2>&1; then
    curl -fsSL https://ollama.com/install.sh | sh
  fi
  mkdir -p /etc/systemd/system/ollama.service.d
  cat > /etc/systemd/system/ollama.service.d/skynet-small-vps.conf <<'CONF'
[Service]
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_KEEP_ALIVE=30s"
CONF
  systemctl daemon-reload
  systemctl enable ollama || true
  systemctl restart ollama || systemctl start ollama || true
  ollama pull "$LOCAL_MODEL" || true
else
  systemctl stop ollama >/dev/null 2>&1 || true
  systemctl disable ollama >/dev/null 2>&1 || true
fi

echo "[4/8] Cloning or updating SKYNET"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull --ff-only
else
  rm -rf "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
fi

echo "[5/8] Creating Python virtualenv"
cd "$APP_DIR"
$PYTHON_BIN -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade --no-cache-dir pip
pip install --no-cache-dir -e .

echo "[6/8] Writing cloud-first .env"
if [ -f .env ]; then
  cp .env ".env.backup.$(date +%Y%m%d%H%M%S)"
else
  cat > .env <<'ENV'
SKYNET_MODE=cloud
CLOUD_DEFAULT_MODEL=openai/gpt-4o-mini
OPENAI_DEFAULT_MODEL=gpt-4o-mini
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
DEFAULT_DEPARTMENT=marketing

ROUTER_MODEL=claude-haiku-4-5
OPENAI_ROUTER_MODEL=gpt-4o-mini

CODERS_ARCHITECT_MODEL=openai/gpt-4o-mini
CODERS_CODER_MODEL=openai/gpt-4o-mini
CODERS_RESEARCHER_MODEL=openai/gpt-4o-mini
CODERS_REVIEWER_MODEL=openai/gpt-4o-mini
CODERS_DEVOPS_MODEL=openai/gpt-4o-mini
CODERS_LEARNER_MODEL=openai/gpt-4o-mini

STRATEGIST_MODEL=openai/gpt-4o-mini
COPYWRITER_MODEL=openai/gpt-4o-mini
SEO_MODEL=openai/gpt-4o-mini
EDITOR_MODEL=openai/gpt-4o-mini
MARKETING_LEARNER_MODEL=openai/gpt-4o-mini

REFERENCE_ANALYST_MODEL=openai/gpt-4o-mini
DESIGN_SYSTEM_MODEL=openai/gpt-4o-mini
FRONTEND_CODER_MODEL=openai/gpt-4o-mini
DESIGN_REVIEWER_MODEL=openai/gpt-4o-mini
DESIGN_LEARNER_MODEL=openai/gpt-4o-mini
OPENAI_VISION_MODEL=gpt-4o-mini

ENABLE_QUALITY_GATE=0
QC_REQUIREMENTS_MODEL=openai/gpt-4o-mini
QC_RISK_MODEL=openai/gpt-4o-mini
QC_FINAL_EDITOR_MODEL=openai/gpt-4o-mini
QC_LEARNER_MODEL=openai/gpt-4o-mini

OPENAI_JUDGE_MODEL=gpt-4o-mini
ENABLE_CREW_MEMORY=0
AGENT_MAX_ITER=3
AGENT_MAX_RETRY_LIMIT=1
AGENT_MAX_RPM=30
AGENT_MAX_EXECUTION_TIME=300

KNOWLEDGE_DIR=./knowledge
REFERENCES_DIR=./references
DESIGN_OUTPUT_DIR=./generated_designs
OUTPUT_DIR=./generated_agents
TRACES_DIR=./traces
RUNS_DIR=./runs
STATE_DIR=./.state

TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USER_IDS=
TELEGRAM_TASK_QUEUE_SIZE=10
TELEGRAM_DEFAULT_MODE=fast
FAST_MODE_PROVIDER=auto
OPENAI_FAST_MODEL=gpt-4o-mini
OPENAI_MODEL_FALLBACKS=gpt-4.1-mini,gpt-4o-mini
TELEGRAM_TASK_TIMEOUT=300
TELEGRAM_PROGRESS_INTERVAL=5
FAST_MODE_TIMEOUT=90
FAST_MODE_NUM_CTX=2048
FAST_MODE_NUM_PREDICT=384
FAST_MODE_TEMPERATURE=0.3

LOCAL_DEFAULT_MODEL=ollama/llama3.2:1b
OLLAMA_API_BASE=http://127.0.0.1:11434

GENERATED_AGENT_ENV_ALLOWLIST=ANTHROPIC_API_KEY,OPENAI_API_KEY,SERPER_API_KEY
GENERATED_AGENT_MEMORY=256m
GENERATED_AGENT_CPUS=0.5
GENERATED_AGENT_NETWORK=bridge
ENV
fi

echo "[7/8] Verifying code"
python -m py_compile telegram_bot.py telegram_task_runner.py src/institute/router.py

echo "[8/8] Done"
echo "Run:"
echo "  cd $APP_DIR"
echo "  source .venv/bin/activate"
echo "  python telegram_bot.py"
echo "  bash scripts/install_telegram_bot_service.sh"
