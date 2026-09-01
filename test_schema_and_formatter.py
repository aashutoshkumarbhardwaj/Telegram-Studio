#!/usr/bin/env python3
"""
Test Suite: Post Schema & Formatter Engine
Converts test-data/test-post.json into a valid Telegram message payload and validates constraints.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from packages.post_schema import (
    ContentType,
    InlineButton,
    MediaItem,
    ParseMode,
    PostSchema,
    SourceInfo,
    VerificationStatus,
)
from packages.formatter import (
    CONTENT_HEADERS,
    MAX_CAPTION_LENGTH,
    MAX_MESSAGE_LENGTH,
    escape_html_text,
    escape_markdown_v2,
    format_post_text,
    generate_telegram_payload,
    validate_telegram_constraints,
)


def test_load_and_validate_test_post():
    print(">>> 1. Loading test-data/test-post.json...")
    post_file = PROJECT_ROOT / "test-data" / "test-post.json"
    with open(post_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Validate with Pydantic
    post = PostSchema(**data)
    assert post.content_type == ContentType.AI_NEWS
    assert post.title == "Gemini Crosses 1 Billion Users"
    assert post.parse_mode == ParseMode.HTML
    assert len(post.buttons) == 1
    assert post.buttons[0].text == "📚 Read Source"
    assert post.buttons[0].url == "https://blog.google/"
    assert post.verification.status == VerificationStatus.VERIFIED
    print("    [PASS] Pydantic validation successful.")

    # 2. Format message text
    formatted_text = format_post_text(post)
    assert "🚨 <b>AI NEWS</b>" in formatted_text
    assert "<b>Gemini Crosses 1 Billion Users</b>" in formatted_text
    assert "Google says Gemini has crossed 1 billion monthly users." in formatted_text
    assert "#AI #Gemini #Tech" in formatted_text
    print("    [PASS] Message text formatted correctly with HTML.")

    # 3. Generate Telegram Bot API Payload
    payload = generate_telegram_payload(post, chat_id="@heyaaashu_channel")
    assert payload["method"] == "sendMessage"
    assert payload["chat_id"] == "@heyaaashu_channel"
    assert payload["parse_mode"] == "HTML"
    assert "reply_markup" in payload
    assert "inline_keyboard" in payload["reply_markup"]
    assert len(payload["reply_markup"]["inline_keyboard"]) == 1
    assert payload["reply_markup"]["inline_keyboard"][0][0]["text"] == "📚 Read Source"
    print("    [PASS] Telegram Bot API payload generated successfully.")
    
    print("\n--- Generated Telegram Payload ---")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print("----------------------------------\n")


def test_job_alert_template():
    print(">>> 2. Testing Job Alert template formatting...")
    job_post = PostSchema(
        content_type=ContentType.JOB,
        title="Senior AI Engineer @ Anthropic",
        body="🏢 <b>Company:</b> Anthropic\n📍 <b>Location:</b> San Francisco / Hybrid\n🎓 <b>Eligibility:</b> 5+ yrs ML Systems\n💰 <b>Compensation:</b> $250k - $380k + Equity\n📅 <b>Deadline:</b> Oct 15, 2026\n\n<b>About the Role:</b>\nWork on scalable RL and alignment infrastructure for Claude models.",
        parse_mode=ParseMode.HTML,
        source={"title": "Anthropic Careers", "url": "https://anthropic.com/careers"},
        buttons=[
            InlineButton(text="💼 Apply Now", url="https://anthropic.com/careers/123"),
            InlineButton(text="🏢 Company Info", url="https://anthropic.com"),
        ],
        hashtags=["AIJobs", "Hiring", "Anthropic"],
    )
    
    payload = generate_telegram_payload(job_post, chat_id="-100123456789")
    assert payload["method"] == "sendMessage"
    assert "💼 <b>JOB ALERT</b>" in payload["text"]
    assert "Senior AI Engineer @ Anthropic" in payload["text"]
    assert len(payload["reply_markup"]["inline_keyboard"][0]) == 2
    print("    [PASS] Job Alert formatted and payload generated.")


def test_media_post_with_photo():
    print(">>> 3. Testing Media Post with Photo attachment...")
    media_post = PostSchema(
        content_type=ContentType.AI_TOOL,
        title="Cursor 2.0 Released",
        body="Next generation AI code editor with native multi-file agentic editing.",
        parse_mode=ParseMode.HTML,
        media=[
            MediaItem(type="photo", url_or_path="https://cursor.com/assets/banner.png")
        ],
        buttons=[
            InlineButton(text="🚀 Try Cursor", url="https://cursor.com")
        ]
    )
    
    payload = generate_telegram_payload(media_post, chat_id="-100123456789")
    assert payload["method"] == "sendPhoto"
    assert payload["photo"] == "https://cursor.com/assets/banner.png"
    assert "caption" in payload
    assert "🛠 <b>AI TOOL</b>" in payload["caption"]
    print("    [PASS] Media post generated sendPhoto payload with caption.")


def test_length_validation():
    print(">>> 4. Testing character limit constraints...")
    valid_text = "A" * 4000
    is_valid, err = validate_telegram_constraints(valid_text, has_media=False)
    assert is_valid is True

    too_long_text = "A" * 4500
    is_valid, err = validate_telegram_constraints(too_long_text, has_media=False)
    assert is_valid is False
    assert "exceeds Telegram limit" in err

    too_long_caption = "A" * 1200
    is_valid, err = validate_telegram_constraints(too_long_caption, has_media=True)
    assert is_valid is False
    assert "exceeds Telegram limit of 1024" in err
    print("    [PASS] Constraint checks enforced correctly.")


def test_markdown_v2_escaping():
    print(">>> 5. Testing MarkdownV2 escaping...")
    raw = "New model v1.5 [Beta] released! Price: $0.002/1k tokens."
    escaped = escape_markdown_v2(raw)
    assert r"\." in escaped
    assert r"\[" in escaped
    assert r"\!" in escaped
    print(f"    Raw:     {raw}")
    print(f"    Escaped: {escaped}")
    print("    [PASS] MarkdownV2 characters escaped safely.")


if __name__ == "__main__":
    print("==================================================")
    print("HEYAAASHU STUDIO - SCHEMA & FORMATTER TEST SUITE")
    print("==================================================")
    test_load_and_validate_test_post()
    test_job_alert_template()
    test_media_post_with_photo()
    test_length_validation()
    test_markdown_v2_escaping()
    print("==================================================")
    print("ALL TESTS PASSED SUCCESSFULLY! [5/5]")
    print("==================================================")
