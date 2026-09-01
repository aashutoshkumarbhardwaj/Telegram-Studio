"""
Telegram message formatting and payload generation engine for Heyaaashu Studio.
Handles HTML validation, MarkdownV2 escaping, length constraint checking,
inline keyboard construction, and payload generation.
"""

import html
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from packages.post_schema import ContentType, ParseMode, PostSchema


# Telegram API Limits
MAX_MESSAGE_LENGTH = 4096
MAX_CAPTION_LENGTH = 1024
MAX_BUTTONS_PER_ROW = 8


# Content Type Header Badges
CONTENT_HEADERS: Dict[ContentType, str] = {
    ContentType.AI_NEWS: "🚨 <b>AI NEWS</b>",
    ContentType.JOB: "💼 <b>JOB ALERT</b>",
    ContentType.INTERNSHIP: "🎓 <b>INTERNSHIP ALERT</b>",
    ContentType.HACKATHON: "🏆 <b>HACKATHON</b>",
    ContentType.AI_TOOL: "🛠 <b>AI TOOL</b>",
    ContentType.CAREER: "🧠 <b>CAREER INSIGHT</b>",
    ContentType.RESOURCE: "📚 <b>RESOURCE</b>",
}

CONTENT_HEADERS_MD2: Dict[ContentType, str] = {
    ContentType.AI_NEWS: "🚨 *AI NEWS*",
    ContentType.JOB: "💼 *JOB ALERT*",
    ContentType.INTERNSHIP: "🎓 *INTERNSHIP ALERT*",
    ContentType.HACKATHON: "🏆 *HACKATHON*",
    ContentType.AI_TOOL: "🛠 *AI TOOL*",
    ContentType.CAREER: "🧠 *CAREER INSIGHT*",
    ContentType.RESOURCE: "📚 *RESOURCE*",
}


def escape_markdown_v2(text: str) -> str:
    """
    Escapes all Telegram MarkdownV2 reserved characters:
    _ * [ ] ( ) ~ ` > # + - = | { } . ! \
    """
    escape_chars = r"_*[]()~`>#+-=|{}.!\\"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)


def escape_html_text(text: str) -> str:
    """Escapes & < > for safe HTML inclusion."""
    return html.escape(text, quote=False)


def format_post_text(post: PostSchema, include_header: bool = True) -> str:
    """
    Formats the complete message text from a PostSchema object according to its parse mode.
    """
    parts = []
    
    if post.parse_mode == ParseMode.HTML:
        if include_header:
            header = CONTENT_HEADERS.get(post.content_type, "📢 <b>UPDATE</b>")
            parts.append(header)
            parts.append("")
        
        # Add Title
        if post.title:
            # Check if title already has HTML formatting, otherwise wrap in <b>
            if "<b" not in post.title and "<strong>" not in post.title:
                parts.append(f"<b>{post.title}</b>")
            else:
                parts.append(post.title)
            parts.append("")
        
        # Add Body
        parts.append(post.body.strip())
        
        # Add Hashtags if present
        if post.hashtags:
            parts.append("")
            tags = " ".join(f"#{t.lstrip('#')}" for t in post.hashtags)
            parts.append(tags)
            
    elif post.parse_mode == ParseMode.MARKDOWN_V2:
        if include_header:
            header = CONTENT_HEADERS_MD2.get(post.content_type, "📢 *UPDATE*")
            parts.append(header)
            parts.append("")
            
        if post.title:
            parts.append(f"*{escape_markdown_v2(post.title)}*")
            parts.append("")
            
        parts.append(post.body.strip())
        
        if post.hashtags:
            parts.append("")
            tags = " ".join(f"\\#{escape_markdown_v2(t.lstrip('#'))}" for t in post.hashtags)
            parts.append(tags)
            
    return "\n".join(parts)


def build_inline_keyboard(post: PostSchema, max_per_row: int = 2) -> Optional[Dict[str, Any]]:
    """
    Constructs Telegram inline keyboard markup from PostSchema buttons.
    """
    if not post.buttons:
        return None
        
    rows = []
    current_row = []
    
    for btn in post.buttons:
        current_row.append({"text": btn.text, "url": btn.url})
        if len(current_row) >= max_per_row:
            rows.append(current_row)
            current_row = []
            
    if current_row:
        rows.append(current_row)
        
    return {"inline_keyboard": rows}


def validate_telegram_constraints(text: str, has_media: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Validates character length constraints for Telegram messages.
    """
    limit = MAX_CAPTION_LENGTH if has_media else MAX_MESSAGE_LENGTH
    if len(text) > limit:
        return False, f"Message length ({len(text)}) exceeds Telegram limit of {limit} characters."
    return True, None


def generate_telegram_payload(
    post: PostSchema,
    chat_id: Union[int, str] = 0,
    include_header: bool = True,
) -> Dict[str, Any]:
    """
    Transforms a PostSchema object into a complete, validated Telegram Bot API payload.
    """
    formatted_text = format_post_text(post, include_header=include_header)
    reply_markup = build_inline_keyboard(post)
    
    has_media = bool(post.media)
    is_valid, error = validate_telegram_constraints(formatted_text, has_media=has_media)
    if not is_valid:
        raise ValueError(error)
        
    if not has_media:
        payload = {
            "method": "sendMessage",
            "chat_id": chat_id,
            "text": formatted_text,
            "parse_mode": post.parse_mode.value,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return payload
    else:
        first_media = post.media[0]
        media_type = first_media.type.lower()
        
        method_map = {
            "photo": "sendPhoto",
            "video": "sendVideo",
            "document": "sendDocument",
            "animation": "sendAnimation",
        }
        method = method_map.get(media_type, "sendPhoto")
        media_field = media_type if media_type in ["photo", "video", "document", "animation"] else "photo"
        
        payload = {
            "method": method,
            "chat_id": chat_id,
            media_field: first_media.url_or_path or first_media.file_id,
            "caption": formatted_text,
            "parse_mode": post.parse_mode.value,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return payload
