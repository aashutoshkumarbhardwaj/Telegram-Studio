"""
Tests for Worker Dry Run and Publish Fixture Validation.
"""

import json
from pathlib import Path
from packages.formatter import format_post_text, generate_telegram_payload, validate_telegram_constraints
from packages.post_schema import PostSchema

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_dry_run_end_to_end():
    post_file = ROOT_DIR / "test-data" / "test-post.json"
    assert post_file.exists()

    with open(post_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    post = PostSchema(**data)
    formatted_text = format_post_text(post)
    is_valid, err = validate_telegram_constraints(formatted_text)
    assert is_valid is True

    payload = generate_telegram_payload(post, chat_id="-1003756584531")
    assert payload["method"] == "sendMessage"
    assert payload["chat_id"] == "-1003756584531"
    assert payload["parse_mode"] == "HTML"
    assert "reply_markup" in payload
    assert "<b>Gemini Crosses 1 Billion Users</b>" in payload["text"]
    assert "🚨 <b>AI NEWS</b>" in payload["text"]
