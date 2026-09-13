"""Small Anthropic helper used outside CrewAI, mirroring openai_client.py."""

from __future__ import annotations

DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5"


class AnthropicRequestError(RuntimeError):
    pass


def anthropic_text_completion(
    system_prompt: str,
    user_prompt: str,
    *,
    model: str | None = None,
    max_tokens: int = 300,
    timeout: int = 60,
) -> str:
    """Single-turn text completion with a bounded timeout and no unhandled
    exceptions escaping to the caller (a bare network failure here used to
    crash classify_department()/JudgeOutputTool before the run was even
    recorded in RunStore)."""
    import anthropic

    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model=model or DEFAULT_ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            timeout=timeout,
        )
    except anthropic.AnthropicError as exc:
        raise AnthropicRequestError(f"Anthropic API error: {exc}") from exc

    for block in response.content:
        if block.type == "text":
            return block.text.strip()
    raise AnthropicRequestError(f"Unexpected Anthropic response shape: {response!r}")
