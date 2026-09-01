"""
Telegram Dry-Run CLI for Heyaaashu Studio.
Validates, formats, and inspects test-data/test-post.json without publishing.

Usage:
    python -m apps.worker.dry_run
"""

import json
import sys
from pathlib import Path

# Ensure monorepo root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from packages.formatter import format_post_text, generate_telegram_payload, validate_telegram_constraints
from packages.post_schema import PostSchema
from packages.shared.config import get_target_channel_id


def run_dry_run():
    post_file = ROOT_DIR / "test-data" / "test-post.json"
    if not post_file.exists():
        print(f"ERROR: Fixture not found at {post_file}")
        sys.exit(1)

    print("=" * 60)
    print("🚀 HEYAAASHU STUDIO — TELEGRAM POST DRY-RUN")
    print("=" * 60)

    # 1. Load Raw JSON
    with open(post_file, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # 2. Validate with Pydantic PostSchema
    try:
        post = PostSchema(**raw_data)
        print("✅ Validation: PostSchema is VALID.")
    except Exception as e:
        print(f"❌ Validation Failed: {e}")
        sys.exit(1)

    # 3. Format message text
    formatted_text = format_post_text(post, include_header=True)
    is_valid, length_err = validate_telegram_constraints(formatted_text, has_media=bool(post.media))
    if not is_valid:
        print(f"❌ Constraint Violation: {length_err}")
        sys.exit(1)

    # 4. Generate Telegram Bot API Payload
    target_channel = get_target_channel_id()
    payload = generate_telegram_payload(post, chat_id=target_channel)

    # 5. Formatted Output Display
    print("\n--- POST METADATA ---")
    print(f"• Content Type:         {post.content_type.value}")
    print(f"• Title:                {post.title}")
    print(f"• Parse Mode:           {post.parse_mode.value}")
    print(f"• Source:               {post.get_source_title()} ({post.get_source_url()})")
    print(f"• Verification Status:  {post.verification.status.value}")
    print(f"• Buttons Count:        {len(post.buttons)}")
    for i, btn in enumerate(post.buttons, start=1):
        print(f"    [{i}] '{btn.text}' -> {btn.url}")
    print(f"• Hashtags:             {', '.join(post.hashtags) if post.hashtags else 'None'}")
    print(f"• Media Attachments:    {len(post.media)}")

    print("\n--- FORMATTED MESSAGE (Preview) ---")
    print(formatted_text)

    print("\n--- GENERATED TELEGRAM API PAYLOAD ---")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print("✅ Dry-run complete. NOTHING was published.")
    print("=" * 60)


if __name__ == "__main__":
    run_dry_run()
