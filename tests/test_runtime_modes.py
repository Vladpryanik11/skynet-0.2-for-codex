from institute.local_mode import cloud_available, cloud_default_model, local_only, model_from_env, skynet_mode


def test_mode_defaults_to_hybrid(monkeypatch):
    monkeypatch.delenv("SKYNET_MODE", raising=False)
    monkeypatch.delenv("LOCAL_ONLY", raising=False)
    assert skynet_mode() == "hybrid"


def test_local_mode_forces_local_model(monkeypatch):
    monkeypatch.setenv("SKYNET_MODE", "local")
    monkeypatch.setenv("LOCAL_DEFAULT_MODEL", "ollama/test-model")
    assert local_only() is True
    assert model_from_env("MISSING_MODEL", "anthropic/claude-sonnet-5") == "ollama/test-model"


def test_local_mode_ignores_cloud_model_overrides(monkeypatch):
    monkeypatch.setenv("SKYNET_MODE", "local")
    monkeypatch.setenv("LOCAL_DEFAULT_MODEL", "ollama/local")
    monkeypatch.setenv("CODERS_CODER_MODEL", "anthropic/claude-sonnet-5")
    assert model_from_env("CODERS_CODER_MODEL", "anthropic/claude-sonnet-5") == "ollama/local"


def test_local_mode_allows_explicit_ollama_role_model(monkeypatch):
    monkeypatch.setenv("SKYNET_MODE", "local")
    monkeypatch.setenv("LOCAL_DEFAULT_MODEL", "ollama/default")
    monkeypatch.setenv("CODERS_CODER_MODEL", "ollama/qwen2.5-coder:7b")
    assert model_from_env("CODERS_CODER_MODEL", "anthropic/claude-sonnet-5") == "ollama/qwen2.5-coder:7b"


def test_hybrid_without_keys_falls_back_to_local_model(monkeypatch):
    monkeypatch.setenv("SKYNET_MODE", "hybrid")
    monkeypatch.setenv("LOCAL_DEFAULT_MODEL", "ollama/local")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert cloud_available() is False
    assert model_from_env("MISSING_MODEL", "anthropic/claude-sonnet-5") == "ollama/local"


def test_cloud_mode_uses_cloud_default_when_key_exists(monkeypatch):
    monkeypatch.setenv("SKYNET_MODE", "cloud")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    assert model_from_env("MISSING_MODEL", "anthropic/claude-sonnet-5") == "anthropic/claude-sonnet-5"


def test_cloud_mode_falls_back_to_openai_when_anthropic_missing(monkeypatch):
    monkeypatch.setenv("SKYNET_MODE", "cloud")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("CLOUD_DEFAULT_MODEL", "openai/gpt-test")
    assert cloud_default_model() == "openai/gpt-test"
    assert model_from_env("MISSING_MODEL", "anthropic/claude-sonnet-5") == "openai/gpt-test"


def test_cloud_mode_ignores_unavailable_anthropic_override(monkeypatch):
    monkeypatch.setenv("SKYNET_MODE", "cloud")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("CLOUD_DEFAULT_MODEL", "openai/gpt-test")
    monkeypatch.setenv("CODERS_CODER_MODEL", "anthropic/claude-sonnet-5")
    assert model_from_env("CODERS_CODER_MODEL", "anthropic/claude-sonnet-5") == "openai/gpt-test"
