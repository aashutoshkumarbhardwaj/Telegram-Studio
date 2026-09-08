"""
Unit & Integration Tests for PostSchema Validation.
"""

import json
from pathlib import Path
import pytest
import jsonschema

from packages.post_schema import (
    ContentType,
    InlineButton,
    MediaItem,
    ParseMode,
    PostSchema,
    SourceInfo,
    VerificationInfo,
    VerificationStatus,
)

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_validate_test_post_json_against_schema():
    schema_file = ROOT_DIR / "packages" / "post-schema" / "post.schema.json"
    test_post_file = ROOT_DIR / "test-data" / "test-post.json"

    with open(schema_file, "r", encoding="utf-8") as f:
        schema = json.load(f)

    with open(test_post_file, "r", encoding="utf-8") as f:
        instance = json.load(f)

    # Validate against JSON Schema
    jsonschema.validate(instance=instance, schema=schema)


def test_post_schema_pydantic_instantiation():
    post = PostSchema(
        content_type=ContentType.AI_NEWS,
        title="OpenAI Ships New Reasoning Model",
        body="Detailed benchmark facts and developer pricing.",
        parse_mode=ParseMode.HTML,
        source="https://openai.com/news/123",
        buttons=[
            InlineButton(text="Read More", url="https://openai.com")
        ],
        hashtags=["AI", "OpenAI"],
        verification=VerificationInfo(status=VerificationStatus.VERIFIED, sources=["https://openai.com"]),
    )

    assert post.content_type == ContentType.AI_NEWS
    assert post.get_source_url() == "https://openai.com/news/123"
    assert len(post.buttons) == 1
    assert post.buttons[0].text == "Read More"


def test_post_schema_invalid_content_type():
    with pytest.raises(Exception):
        PostSchema(
            content_type="invalid_type",
            title="Invalid",
            body="Invalid",
        )


def test_post_schema_callback_button_and_github_type():
    post = PostSchema(
        content_type=ContentType.GITHUB,
        title="Awesome AI Studio",
        body="Comprehensive open source Telegram studio for AI developers.",
        buttons=[
            InlineButton(text="GitHub Repo", url="https://github.com/heyaaashu/studio"),
            InlineButton(text="❤️ Like", callback_data="react_like"),
        ],
    )
    assert post.content_type == ContentType.GITHUB
    assert len(post.buttons) == 2
    assert post.buttons[0].url == "https://github.com/heyaaashu/studio"
    assert post.buttons[1].callback_data == "react_like"
    assert post.buttons[1].url is None


def test_build_aiogram_inline_keyboard():
    from packages.telegram.publisher import build_aiogram_inline_keyboard

    post = PostSchema(
        content_type=ContentType.AI_TOOL,
        title="Tool Spotlight",
        body="Check out this tool.",
        buttons=[
            InlineButton(text="Visit", url="https://tool.ai"),
            InlineButton(text="❤️ Like", callback_data="react_like"),
            InlineButton(text="Invalid Dummy", url=""),  # Should be safely skipped
        ],
    )
    kb = build_aiogram_inline_keyboard(post)
    assert kb is not None
    assert len(kb.inline_keyboard) >= 1
    flat_btns = [btn for row in kb.inline_keyboard for btn in row]
    assert len(flat_btns) == 2
    assert flat_btns[0].text == "Visit"
    assert flat_btns[0].url == "https://tool.ai"
    assert flat_btns[1].text == "❤️ Like"
    assert flat_btns[1].callback_data == "react_like"

