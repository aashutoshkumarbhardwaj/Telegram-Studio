"""
Tests for Telegram Formatter Engine (HTML, MarkdownV2, Inline Keyboards, Constraints).
"""

from packages.formatter import (
    CONTENT_HEADERS,
    escape_html_text,
    escape_markdown_v2,
    format_post_text,
    generate_telegram_payload,
    validate_telegram_constraints,
)
from packages.post_schema import ContentType, InlineButton, ParseMode, PostSchema


def test_html_formatting_includes_header_and_body():
    post = PostSchema(
        content_type=ContentType.JOB,
        title="AI Research Scientist",
        body="Join top AI research team working on multi-agent reasoning.",
        parse_mode=ParseMode.HTML,
        buttons=[InlineButton(text="💼 Apply", url="https://example.com/apply")],
        hashtags=["AIJobs", "Hiring"],
    )

    formatted = format_post_text(post, include_header=True)
    assert "💼 <b>JOB ALERT</b>" in formatted
    assert "<b>AI Research Scientist</b>" in formatted
    assert "Join top AI research team" in formatted
    assert "#AIJobs #Hiring" in formatted


def test_markdown_v2_escaping():
    text = "Model v2.0-beta [Update]! Cost is $0.05 / 1k."
    escaped = escape_markdown_v2(text)
    assert r"\." in escaped
    assert r"\[" in escaped
    assert r"\!" in escaped
    assert r"\-" in escaped


def test_telegram_payload_generation_without_media():
    post = PostSchema(
        content_type=ContentType.AI_TOOL,
        title="vLLM v0.6",
        body="High-throughput LLM serving engine.",
        parse_mode=ParseMode.HTML,
        buttons=[InlineButton(text="🚀 GitHub", url="https://github.com/vllm-project/vllm")],
    )

    payload = generate_telegram_payload(post, chat_id="@heyaaahu")
    assert payload["method"] == "sendMessage"
    assert payload["chat_id"] == "@heyaaahu"
    assert payload["parse_mode"] == "HTML"
    assert "reply_markup" in payload
    assert payload["reply_markup"]["inline_keyboard"][0][0]["text"] == "🚀 GitHub"


def test_length_constraint_validator():
    ok_text = "Hello world"
    is_valid, err = validate_telegram_constraints(ok_text, has_media=False)
    assert is_valid is True
    assert err is None

    overflow_text = "X" * 4097
    is_valid, err = validate_telegram_constraints(overflow_text, has_media=False)
    assert is_valid is False
    assert "exceeds Telegram limit" in err
