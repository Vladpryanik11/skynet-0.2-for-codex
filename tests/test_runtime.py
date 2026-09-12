from institute.contracts import RunManifest
from institute.registry import DEPARTMENT_REGISTRY, keyword_route
from institute.run_store import RunStore
from institute.runtime import agent_runtime_kwargs, crew_memory_enabled, quality_gate_enabled


def test_registry_contains_lazy_loaders_for_all_departments():
    assert set(DEPARTMENT_REGISTRY) == {"coders", "marketing", "design", "quality_control"}
    assert all(":" in spec.loader for spec in DEPARTMENT_REGISTRY.values())


def test_registry_routes_without_loading_a_model():
    assert keyword_route("собери UI макет") == "design"
    assert keyword_route("напиши пост для запуска") == "marketing"


def test_runtime_policy_is_bounded(monkeypatch):
    monkeypatch.setenv("AGENT_MAX_ITER", "12")
    monkeypatch.setenv("AGENT_MAX_RETRY_LIMIT", "3")
    policy = agent_runtime_kwargs()
    assert policy["max_iter"] == 12
    assert policy["max_retry_limit"] == 3
    assert policy["respect_context_window"] is True


def test_memory_is_off_by_default_in_local_mode(monkeypatch):
    monkeypatch.setenv("SKYNET_MODE", "local")
    monkeypatch.delenv("ENABLE_CREW_MEMORY", raising=False)
    assert crew_memory_enabled() is False


def test_quality_gate_defaults_to_enabled(monkeypatch):
    monkeypatch.delenv("ENABLE_QUALITY_GATE", raising=False)
    assert quality_gate_enabled() is True


def test_run_store_persists_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv("SKYNET_MODE", "local")
    store = RunStore(str(tmp_path))
    manifest = store.start("создай сайт", "design")
    assert manifest.status == "running"
    store.complete(manifest, "готовый результат")

    saved = RunManifest.model_validate_json(
        (tmp_path / f"{manifest.run_id}.json").read_text(encoding="utf-8")
    )
    assert saved.status == "completed"
    assert saved.mode == "local"
    assert saved.output_preview == "готовый результат"
