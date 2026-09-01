"""
Tests for UI Builder Interoperability and Schema Translation.
"""

from packages.formatter.ui_builder_compat import post_schema_to_screen, screen_to_post_schema
from packages.post_schema import ContentType, InlineButton, ParseMode, PostSchema


def test_roundtrip_ui_builder_screen_compatibility():
    original_post = PostSchema(
        content_type=ContentType.AI_TOOL,
        title="Cursor Editor",
        body="AI-first Code Editor.",
        parse_mode=ParseMode.HTML,
        buttons=[
            InlineButton(text="Download", url="https://cursor.com"),
            InlineButton(text="Docs", url="https://docs.cursor.com"),
        ],
    )

    # Convert to UI Builder Screen object
    screen = post_schema_to_screen(original_post)
    assert screen["name"] == "Cursor Editor"
    assert screen["message_content"] == "AI-first Code Editor."
    assert len(screen["keyboard"]) == 1
    assert len(screen["keyboard"][0]["buttons"]) == 2

    # Convert back to PostSchema
    converted_post = screen_to_post_schema(screen, content_type=ContentType.AI_TOOL)
    assert converted_post.title == original_post.title
    assert converted_post.body == original_post.body
    assert len(converted_post.buttons) == 2
    assert converted_post.buttons[0].text == "Download"
    assert converted_post.buttons[0].url == "https://cursor.com"
