import pytest

from telegram_bot import (
    extract_runner_result,
    parse_allowed_user_ids,
    progress_bar,
    progress_percent,
    split_for_telegram,
)


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
