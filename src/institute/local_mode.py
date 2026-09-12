import os


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


def model_from_env(env_var: str, default: str) -> str:
    if env_var in os.environ and os.environ[env_var].strip():
        return os.environ[env_var].strip()
    if skynet_mode() == "local":
        return os.environ.get("LOCAL_DEFAULT_MODEL", "ollama/llama3.1:8b")
    if skynet_mode() == "hybrid" and not cloud_available():
        return os.environ.get("LOCAL_DEFAULT_MODEL", "ollama/llama3.1:8b")
    return default
