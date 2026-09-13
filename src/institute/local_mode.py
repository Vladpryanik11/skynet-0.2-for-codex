import os

OPENAI_DEFAULT_MODEL = "openai/gpt-4o-mini"


def skynet_mode() -> str:
    mode = os.environ.get("SKYNET_MODE", "").strip().lower()
    if not mode:
        mode = "local" if os.environ.get("LOCAL_ONLY", "0").strip().lower() in {"1", "true", "yes", "on"} else "hybrid"
    if mode not in {"local", "cloud", "hybrid"}:
        return "hybrid"
    return mode


def local_only() -> bool:
    return skynet_mode() == "local"


def cloud_available() -> bool:
    if skynet_mode() == "local":
        return False
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def anthropic_available() -> bool:
    if skynet_mode() == "local":
        return False
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def openai_available() -> bool:
    if skynet_mode() == "local":
        return False
    return bool(os.environ.get("OPENAI_API_KEY"))


def cloud_default_model() -> str:
    configured = os.environ.get("CLOUD_DEFAULT_MODEL", "").strip()
    if configured:
        return configured
    if openai_available():
        return os.environ.get("OPENAI_DEFAULT_MODEL", OPENAI_DEFAULT_MODEL).strip() or OPENAI_DEFAULT_MODEL
    return OPENAI_DEFAULT_MODEL


def model_provider_available(model: str) -> bool:
    if model.startswith("anthropic/"):
        return anthropic_available()
    if model.startswith("openai/"):
        return openai_available()
    if model.startswith(("ollama/", "ollama_chat/")):
        return skynet_mode() != "cloud"
    return True


def model_from_env(env_var: str, default: str) -> str:
    if skynet_mode() == "local":
        configured = os.environ.get(env_var, "").strip()
        if configured.startswith(("ollama/", "ollama_chat/")):
            return configured
        return os.environ.get("LOCAL_DEFAULT_MODEL", "ollama/llama3.1:8b")

    if env_var in os.environ and os.environ[env_var].strip():
        configured = os.environ[env_var].strip()
        if model_provider_available(configured):
            return configured
        if openai_available():
            return cloud_default_model()
        return configured

    if skynet_mode() == "hybrid" and not cloud_available():
        return os.environ.get("LOCAL_DEFAULT_MODEL", "ollama/llama3.1:8b")
    if not model_provider_available(default) and openai_available():
        return cloud_default_model()
    return default
