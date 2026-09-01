"""
Unified Headless Telegram Publisher for Heyaaashu Studio.
Directly converts PostSchema into Telegram Bot API dispatches without starting polling or schedulers.
"""

import json
import logging
from typing import Any, Dict, Optional, Union
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from packages.formatter import build_inline_keyboard, format_post_text, generate_telegram_payload
from packages.post_schema import PostSchema
from packages.shared.config import BOT_TOKEN, get_target_channel_id

logger = logging.getLogger(__name__)


from packages.formatter.telegram_formatter import is_valid_button_url


def build_aiogram_inline_keyboard(post: PostSchema, max_per_row: int = 2) -> Optional[InlineKeyboardMarkup]:
    """
    Constructs an aiogram InlineKeyboardMarkup instance from a PostSchema object.
    Filters out invalid/dummy URLs.
    """
    valid_buttons = [b for b in post.buttons if is_valid_button_url(b.url)]
    if not valid_buttons:
        return None
        
    rows = []
    current_row = []
    
    for btn in valid_buttons:
        current_row.append(InlineKeyboardButton(text=btn.text, url=btn.url))
        if len(current_row) >= max_per_row:
            rows.append(current_row)
            current_row = []
            
    if current_row:
        rows.append(current_row)
        
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def publish_post_to_telegram(
    post: PostSchema,
    bot: Optional[Bot] = None,
    channel_id: Optional[Union[int, str]] = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Publishes a PostSchema object to the specified Telegram channel.
    If bot is not provided, a temporary Bot session is created and closed safely.
    """
    target_channel = channel_id or get_target_channel_id()
    bot_token = token or BOT_TOKEN
    
    if not bot_token:
        raise ValueError("BOT_TOKEN is missing. Please configure it in .env.")

    own_bot = False
    if bot is None:
        bot = Bot(token=bot_token)
        own_bot = True
        
    try:
        reply_markup = build_aiogram_inline_keyboard(post)
        formatted_text = format_post_text(post, include_header=True)
        parse_mode = ParseMode.HTML if post.parse_mode.value == "HTML" else ParseMode.MARKDOWN_V2
        
        has_media = bool(post.media)
        sent_message = None
        
        if not has_media:
            sent_message = await bot.send_message(
                chat_id=target_channel,
                text=formatted_text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_web_page_preview=False,
            )
        else:
            first_media = post.media[0]
            m_type = first_media.type.lower()
            media_source = first_media.url_or_path or first_media.file_id
            
            if m_type == "photo":
                sent_message = await bot.send_photo(
                    chat_id=target_channel,
                    photo=media_source,
                    caption=formatted_text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                )
            elif m_type == "video":
                sent_message = await bot.send_video(
                    chat_id=target_channel,
                    video=media_source,
                    caption=formatted_text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                )
            elif m_type == "document":
                sent_message = await bot.send_document(
                    chat_id=target_channel,
                    document=media_source,
                    caption=formatted_text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                )
            elif m_type == "animation":
                sent_message = await bot.send_animation(
                    chat_id=target_channel,
                    animation=media_source,
                    caption=formatted_text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                )
            else:
                sent_message = await bot.send_message(
                    chat_id=target_channel,
                    text=formatted_text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                )
                
        return {
            "success": True,
            "message_id": sent_message.message_id if sent_message else None,
            "chat_id": sent_message.chat.id if sent_message else target_channel,
            "channel_title": getattr(sent_message.chat, "title", None) if sent_message else None,
        }
    except Exception as e:
        logger.error(f"Failed to publish post to {target_channel}: {e}", exc_info=True)
        raise e
    finally:
        if own_bot:
            await bot.session.close()
