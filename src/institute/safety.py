import os
import re
from pathlib import Path


DEFAULT_AGENT_ENV_ALLOWLIST = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "SERPER_API_KEY")


def safe_docker_tag(value: str, fallback: str = "skynet-agent") -> str:
    """Return a Docker-safe tag/container name with a predictable fallback."""
    normalized = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip().lower()).strip(".-")
    return normalized[:120] or fallback


def resolve_inside_dir(base_dir: str, filename: str) -> Path:
    """Resolve filename under base_dir and reject path traversal."""
    base = Path(base_dir).resolve()
    raw = Path(filename)
    target = raw.resolve() if raw.is_absolute() else (base / raw).resolve()
    if base != target and base not in target.parents:
        raise ValueError(f"Path escapes base directory: {filename}")
    return target


def parse_env_allowlist(raw: str | None = None) -> list[str]:
    value = raw if raw is not None else os.environ.get("GENERATED_AGENT_ENV_ALLOWLIST", "")
    if not value.strip():
        return list(DEFAULT_AGENT_ENV_ALLOWLIST)
    return [item.strip() for item in value.split(",") if item.strip()]


def build_env_args(allowlist: list[str] | None = None) -> list[str]:
    """Build `docker run -e KEY` args for explicitly allowed existing env vars."""
    keys = allowlist or parse_env_allowlist()
    args: list[str] = []
    for key in keys:
        if key in os.environ:
            args.extend(["-e", key])
    return args
