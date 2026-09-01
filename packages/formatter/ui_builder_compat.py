"""
Telegram UI Builder Interoperability Module for Heyaaashu Studio.
Converts between apps/message-builder Screen/Keyboard objects and canonical PostSchema.
"""

from typing import Any, Dict, List, Optional
from packages.post_schema import (
    ContentType,
    InlineButton,
    MediaItem,
    ParseMode,
    PostSchema,
    SourceInfo,
)


def screen_to_post_schema(screen: Dict[str, Any], content_type: ContentType = ContentType.AI_NEWS) -> PostSchema:
    """
    Converts a Telegram UI Builder `Screen` dict into a canonical PostSchema.
    """
    body = screen.get("message_content", "")
    parse_mode_str = screen.get("parse_mode", "HTML")
    parse_mode = ParseMode.MARKDOWN_V2 if parse_mode_str == "MarkdownV2" else ParseMode.HTML

    buttons: List[InlineButton] = []
    keyboard_rows = screen.get("keyboard", [])
    for row in keyboard_rows:
        row_buttons = row.get("buttons", []) if isinstance(row, dict) else row
        for btn in row_buttons:
            text = btn.get("text", "Link")
            url = btn.get("url") or "https://t.me"
            buttons.append(InlineButton(text=text, url=url))

    media: List[MediaItem] = []
    if screen.get("media_url"):
        m_type = screen.get("message_type", "photo")
        media.append(MediaItem(type=m_type, url_or_path=screen["media_url"]))

    title = screen.get("name") or "UI Builder Post"

    return PostSchema(
        content_type=content_type,
        title=title,
        body=body,
        parse_mode=parse_mode,
        media=media,
        buttons=buttons,
    )


def post_schema_to_screen(post: PostSchema, screen_id: str = "main_screen") -> Dict[str, Any]:
    """
    Converts a canonical PostSchema into a Telegram UI Builder `Screen` object.
    """
    keyboard_rows: List[Dict[str, Any]] = []
    current_buttons: List[Dict[str, Any]] = []

    for i, btn in enumerate(post.buttons):
        current_buttons.append({
            "id": f"btn_{i}",
            "text": btn.text,
            "url": btn.url,
        })
        if len(current_buttons) >= 2:
            keyboard_rows.append({
                "id": f"row_{len(keyboard_rows)}",
                "buttons": current_buttons,
            })
            current_buttons = []

    if current_buttons:
        keyboard_rows.append({
            "id": f"row_{len(keyboard_rows)}",
            "buttons": current_buttons,
        })

    first_media = post.media[0] if post.media else None

    return {
        "id": screen_id,
        "name": post.title,
        "message_content": post.body,
        "parse_mode": post.parse_mode.value,
        "message_type": first_media.type if first_media else "text",
        "media_url": (first_media.url_or_path or first_media.file_id) if first_media else None,
        "keyboard": keyboard_rows,
    }
