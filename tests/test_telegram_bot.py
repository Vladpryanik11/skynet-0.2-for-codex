import asyncio

import pytest

from telegram_bot import (
    BotState,
    WORK_MODES,
    default_mode,
    extract_runner_result,
    mode_for_chat,
    parse_allowed_user_ids,
    progress_bar,
    progress_percent,
    split_for_telegram,
)
from telegram_task_runner import build_fast_payload, ollama_model_name


def test_parse_allowed_user_ids_accepts_commas_and_semicolons():
    assert parse_allowed_user_ids("123, 456;bad; 789") == {123, 456, 789}


def test_split_for_telegram_keeps_chunks_under_limit():
    chunks = split_for_telegram("hello world " * 20, limit=40)
    assert len(chunks) > 1
    assert all(len(chunk) <= 40 for chunk in chunks)


def test_progress_bar_clamps_percent():
    assert progress_bar(150, width=10) == "[██████████]"
    assert progress_bar(-10, width=10) == "[░░░░░░░░░░]"


def test_progress_percent_stays_below_done_until_runner_finishes():
    assert progress_percent(0, 100) == 5
    assert progress_percent(100, 100) == 95


def test_extract_runner_result_prefers_sentinel_payload():
    output = "log line\n<<<SKYNET_RESULT_START>>>\nfinal answer\n<<<SKYNET_RESULT_END>>>\nmore logs"
    assert extract_runner_result(output) == "final answer"


def test_extract_runner_result_falls_back_to_stdout():
    assert extract_runner_result("plain output") == "plain output"


def test_fast_mode_is_available_and_default(monkeypatch):
    monkeypatch.delenv("TELEGRAM_DEFAULT_MODE", raising=False)
    state = BotState(queue=asyncio.Queue())
    assert "fast" in WORK_MODES
    assert default_mode() == "fast"
    assert mode_for_chat(state, 123) == "fast"


def test_default_mode_ignores_unknown_value(monkeypatch):
    monkeypatch.setenv("TELEGRAM_DEFAULT_MODE", "unknown")
    assert default_mode() == "fast"


def test_ollama_model_name_strips_litellm_prefix():
    assert ollama_model_name("ollama/llama3.2:1b") == "llama3.2:1b"
    assert ollama_model_name("ollama_chat/qwen2.5:3b") == "qwen2.5:3b"


def test_build_fast_payload_caps_response(monkeypatch):
    monkeypatch.setenv("LOCAL_DEFAULT_MODEL", "ollama/llama3.2:1b")
    monkeypatch.setenv("FAST_MODE_NUM_PREDICT", "128")
    payload = build_fast_payload("привет")
    assert payload["model"] == "llama3.2:1b"
    assert payload["options"]["num_predict"] == 128
