"""
End-to-End User Experience & Flow Tests for Heyaaashu Studio.
Tests the exact user flow: Raw Input -> PostSchema -> Formatter -> Preview -> Edit -> Improve -> Regenerate -> Add Source -> Add Buttons -> Publish Payload.
"""

import pytest
from packages.ai.extractor import (
    extract_post_schema_from_input,
    improve_post_schema,
    regenerate_post_schema,
)
from packages.formatter import format_post_text, generate_telegram_payload, validate_telegram_constraints
from packages.post_schema import ContentType, InlineButton, ParseMode, PostSchema, SourceInfo


@pytest.mark.asyncio
async def test_exact_user_raw_input_flow():
    """
    Step 1: Test exact user input from prompt:
    Google says Gemini has crossed 1 billion monthly users.

    The Gemini app supports voice, camera, screen sharing and image generation.

    https://blog.google/
    """
    raw_input = (
        "Google says Gemini has crossed 1 billion monthly users.\n\n"
        "The Gemini app supports voice, camera, screen sharing and image generation.\n\n"
        "https://blog.google/"
    )

    # 1. Extraction into PostSchema
    post = await extract_post_schema_from_input(ContentType.AI_NEWS, raw_input)

    assert isinstance(post, PostSchema)
    assert post.content_type == ContentType.AI_NEWS
    assert post.parse_mode == ParseMode.HTML
    assert "Google" in post.title or "Gemini" in post.title
    assert "1 billion" in post.title or "1 billion" in post.body
    assert "voice, camera, screen sharing" in post.body
    assert post.get_source_url() == "https://blog.google/"
    assert len(post.buttons) >= 1
    assert post.buttons[0].url == "https://blog.google/"

    # 2. Formatter & Preview Generation
    formatted_preview = format_post_text(post, include_header=True)
    assert "🚨 <b>AI NEWS</b>" in formatted_preview
    assert "<b>" in formatted_preview and "</b>" in formatted_preview
    assert "⚡ <b>KEY TAKEAWAYS</b>" in formatted_preview
    assert "💡 <b>WHY IT MATTERS</b>" in formatted_preview
    assert not ("<b>" not in formatted_preview and "<" in formatted_preview)

    # 3. Constraint Check
    is_valid, err = validate_telegram_constraints(formatted_preview)
    assert is_valid is True
    assert err is None

    # 4. Telegram Payload Generation
    payload = generate_telegram_payload(post, chat_id="-1003756584531")
    assert payload["method"] == "sendMessage"
    assert payload["chat_id"] == "-1003756584531"
    assert payload["parse_mode"] == "HTML"
    assert payload["reply_markup"]["inline_keyboard"][0][0]["text"] == "📚 Read Source"


def test_edit_flow():
    """Step 2: Test Edit flow modifies body without losing metadata."""
    post = PostSchema(
        content_type=ContentType.AI_NEWS,
        title="Gemini Crosses 1 Billion Users",
        body="Initial body text",
        source="https://blog.google/",
        buttons=[InlineButton(text="Read Source", url="https://blog.google/")],
    )

    new_body = "Updated body with more technical details."
    post.body = new_body

    formatted = format_post_text(post)
    assert "Updated body with more technical details." in formatted
    assert post.get_source_url() == "https://blog.google/"


def test_improve_flow():
    """Step 3: Test Improve preserves facts and sharpens structure."""
    post = PostSchema(
        content_type=ContentType.AI_NEWS,
        title="Gemini Hits 1B Users",
        body="Google launched Gemini with 1 billion users across voice and camera.",
        source="https://blog.google/",
    )

    improved = improve_post_schema(post)
    assert "KEY TAKEAWAYS" in improved.body
    assert "1 billion users" in improved.body


def test_regenerate_flow():
    """Step 4: Test Regenerate produces variant without introducing fake claims."""
    post = PostSchema(
        content_type=ContentType.AI_NEWS,
        title="Gemini Crosses 1 Billion Users",
        body="Google says Gemini has crossed 1 billion monthly users.",
        source="https://blog.google/",
    )

    regenerated = regenerate_post_schema(post)
    assert "1 Billion" in regenerated.body or "1 Billion" in regenerated.title
    assert "KEY TAKEAWAYS" in regenerated.body
    assert "WHY IT MATTERS" in regenerated.body


def test_add_buttons_and_source_flow():
    """Step 5: Test adding multiple buttons and source URL."""
    post = PostSchema(
        content_type=ContentType.AI_NEWS,
        title="Gemini Crosses 1 Billion Users",
        body="Google multimodal update.",
    )

    # Attach Source
    post.source = SourceInfo(title="Google Blog", url="https://blog.google/")
    post.buttons.append(InlineButton(text="📚 Read Source", url="https://blog.google/"))

    # Attach Additional Button (e.g. Discuss)
    post.buttons.append(InlineButton(text="💬 Discuss", url="https://t.me/heyaaahu"))

    assert len(post.buttons) == 2
    assert post.buttons[0].text == "📚 Read Source"
    assert post.buttons[1].text == "💬 Discuss"

    payload = generate_telegram_payload(post, chat_id="-1003756584531")
    # Verified that 2 buttons are in the inline keyboard
    keyboard = payload["reply_markup"]["inline_keyboard"]
    assert len(keyboard[0]) == 2
    assert keyboard[0][0]["text"] == "📚 Read Source"
    assert keyboard[0][1]["text"] == "💬 Discuss"
