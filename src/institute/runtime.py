"""Provider-neutral runtime policy for every agent and crew."""

import os

from institute.local_mode import skynet_mode


def _int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, default)))
    except ValueError:
        return default


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name, "1" if default else "0").strip().lower()
    return value in {"1", "true", "yes", "on"}


def agent_runtime_kwargs() -> dict:
    """Bound retries and iterations so a local run cannot loop indefinitely."""
    return {
        "max_iter": _int_env("AGENT_MAX_ITER", 8),
        "max_retry_limit": _int_env("AGENT_MAX_RETRY_LIMIT", 2),
        "max_rpm": _int_env("AGENT_MAX_RPM", 20),
        "max_execution_time": _int_env("AGENT_MAX_EXECUTION_TIME", 900),
        "respect_context_window": True,
    }


def crew_memory_enabled() -> bool:
    """CrewAI memory stays opt-in because local embeddings may require an API."""
    return skynet_mode() != "local" and _bool_env("ENABLE_CREW_MEMORY", False)


def quality_gate_enabled() -> bool:
    return _bool_env("ENABLE_QUALITY_GATE", True)
