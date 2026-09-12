import os

import pytest

from institute.safety import build_env_args, parse_env_allowlist, resolve_inside_dir, safe_docker_tag


def test_safe_docker_tag_normalizes_unsafe_text():
    assert safe_docker_tag("My Agent: RSS Monitor!") == "my-agent-rss-monitor"


def test_safe_docker_tag_has_fallback():
    assert safe_docker_tag("!!!") == "skynet-agent"


def test_resolve_inside_dir_rejects_traversal(tmp_path):
    with pytest.raises(ValueError):
        resolve_inside_dir(str(tmp_path), "../agent.py")


def test_parse_env_allowlist_uses_default_when_empty(monkeypatch):
    monkeypatch.delenv("GENERATED_AGENT_ENV_ALLOWLIST", raising=False)
    assert "ANTHROPIC_API_KEY" in parse_env_allowlist()


def test_build_env_args_only_includes_existing_allowed_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    args = build_env_args(["OPENAI_API_KEY", "ANTHROPIC_API_KEY"])
    assert args == ["-e", "OPENAI_API_KEY"]
