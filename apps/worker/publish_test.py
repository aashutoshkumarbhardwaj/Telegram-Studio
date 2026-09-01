"""
Single Message Publisher CLI for Heyaaashu Studio.
Publishes ONLY test-data/test-post.json to the configured target channel.
Does NOT start polling, schedulers, or background tasks.

Usage:
    python -m apps.worker.publish_test
"""

import asyncio
import json
import sys
from pathlib import Path

# Ensure monorepo root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from packages.post_schema import PostSchema
from packages.shared.config import BOT_TOKEN, get_target_channel_id
from packages.telegram.publisher import publish_post_to_telegram


async def run_publish_test():
    post_file = ROOT_DIR / "test-data" / "test-post.json"
    if not post_file.exists():
        print(f"ERROR: Fixture not found at {post_file}")
        sys.exit(1)

    print("=" * 60)
    print("🚀 HEYAAASHU STUDIO — SINGLE POST PUBLISHER TEST")
    print("=" * 60)

    # 1. Load JSON
    with open(post_file, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # 2. Validate
    try:
        post = PostSchema(**raw_data)
        print("✅ Validation: PostSchema is VALID.")
    except Exception as e:
        print(f"❌ Validation Failed: {e}")
        sys.exit(1)

    # 3. Publish to Channel
    target_channel = get_target_channel_id()
    print(f"📡 Publishing post to Telegram channel: {target_channel}")
    print(f"📌 Post Title: '{post.title}'")

    try:
        result = await publish_post_to_telegram(post, channel_id=target_channel)
        if result.get("success"):
            print("\n" + "=" * 60)
            print("🎉 SUCCESS: Post published to Telegram channel!")
            print(f"• Message ID:     {result.get('message_id')}")
            print(f"• Channel ID:     {result.get('chat_id')}")
            print(f"• Channel Title:  {result.get('channel_title')}")
            print("=" * 60)
        else:
            print(f"❌ Publishing failed: {result}")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during Telegram publication: {e}")
        sys.exit(1)


def main():
    asyncio.run(run_publish_test())


if __name__ == "__main__":
    main()
