"""
Telegram Inline Keyboard Definitions for Heyaaashu Studio Bot.
"""

from typing import List
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from packages.post_schema import ContentType


def get_content_type_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting the type of post to create."""
    keyboard = [
        [
            InlineKeyboardButton(text="🚨 AI News", callback_data="ctype:ai_news"),
            InlineKeyboardButton(text="💼 Job", callback_data="ctype:job"),
        ],
        [
            InlineKeyboardButton(text="🎓 Internship", callback_data="ctype:internship"),
            InlineKeyboardButton(text="🏆 Hackathon", callback_data="ctype:hackathon"),
        ],
        [
            InlineKeyboardButton(text="🛠 AI Tool", callback_data="ctype:ai_tool"),
            InlineKeyboardButton(text="🧠 Career", callback_data="ctype:career"),
        ],
        [
            InlineKeyboardButton(text="📚 Resource", callback_data="ctype:resource"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="action:cancel_creation"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_preview_action_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    """Action controls for reviewing, modifying, and publishing a draft."""
    keyboard = [
        [
            InlineKeyboardButton(text="✏️ Edit", callback_data=f"pv:edit:{draft_id}"),
            InlineKeyboardButton(text="✨ Improve", callback_data=f"pv:improve:{draft_id}"),
        ],
        [
            InlineKeyboardButton(text="🔄 Regenerate", callback_data=f"pv:regen:{draft_id}"),
            InlineKeyboardButton(text="🖼 Add Image", callback_data=f"pv:image:{draft_id}"),
        ],
        [
            InlineKeyboardButton(text="🔗 Add Buttons", callback_data=f"pv:btn:{draft_id}"),
            InlineKeyboardButton(text="📚 Add Source", callback_data=f"pv:src:{draft_id}"),
        ],
        [
            InlineKeyboardButton(text="🚀 Publish", callback_data=f"pv:pub:{draft_id}"),
            InlineKeyboardButton(text="❌ Cancel", callback_data=f"pv:cancel:{draft_id}"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_research_category_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting research topics."""
    keyboard = [
        [
            InlineKeyboardButton(text="🚨 AI News", callback_data="res_cat:ai_news"),
            InlineKeyboardButton(text="💼 Jobs & Hiring", callback_data="res_cat:job"),
        ],
        [
            InlineKeyboardButton(text="🎓 Internships", callback_data="res_cat:internship"),
            InlineKeyboardButton(text="🏆 Hackathons", callback_data="res_cat:hackathon"),
        ],
        [
            InlineKeyboardButton(text="🛠 AI Tools", callback_data="res_cat:ai_tool"),
            InlineKeyboardButton(text="🧠 Career Insights", callback_data="res_cat:career"),
        ],
        [
            InlineKeyboardButton(text="📚 Resources", callback_data="res_cat:resource"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="action:cancel_creation"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_research_candidates_keyboard(candidates: list, cat_key: str) -> InlineKeyboardMarkup:
    """Keyboard listing top verified research candidates."""
    keyboard = []
    
    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    for i, cand in enumerate(candidates):
        num = number_emojis[i] if i < len(number_emojis) else f"{i+1}."
        short_title = cand.title if len(cand.title) <= 28 else cand.title[:25] + "..."
        keyboard.append([
            InlineKeyboardButton(
                text=f"{num} {short_title}",
                callback_data=f"res_pick:{cand.id}",
            )
        ])

    keyboard.append([
        InlineKeyboardButton(text="🔄 Refresh Sources", callback_data=f"res_cat:{cat_key}"),
        InlineKeyboardButton(text="❌ Cancel", callback_data="action:cancel_creation"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main start menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton(text="✍️ New Post (/new)", callback_data="cmd:new"),
            InlineKeyboardButton(text="🔍 Research (/research)", callback_data="cmd:research"),
        ],
        [
            InlineKeyboardButton(text="📁 Drafts", callback_data="cmd:drafts"),
            InlineKeyboardButton(text="📢 Channels", callback_data="cmd:channels"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
