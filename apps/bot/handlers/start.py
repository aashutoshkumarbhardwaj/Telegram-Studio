"""
Start & Navigation Router for Heyaaashu Studio Bot.
"""

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery

from apps.bot.keyboards import get_main_menu_keyboard, get_content_type_keyboard, get_research_category_keyboard
from packages.shared.db import StudioDatabase

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, db: StudioDatabase):
    user = message.from_user
    if user:
        # Register user in DB
        with db.get_connection() as conn:
            conn.cursor().execute("""
                INSERT INTO users (user_id, username, first_name)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name
            """, (user.id, user.username, user.first_name))
            conn.commit()

    welcome_text = (
        f"👋 Welcome to <b>Heyaaashu Studio</b>, {user.first_name if user else 'Creator'}!\n\n"
        "Your private AI + Tech + Jobs + Career content operating system.\n\n"
        "<b>Available Commands:</b>\n"
        "• <code>/new</code> — Create a new structured post draft\n"
        "• <code>/research</code> — Generate curated research & news\n"
        "• <code>/drafts</code> — View saved drafts\n"
        "• <code>/channels</code> — Manage connected Telegram channels\n"
        "• <code>/settings</code> — Bot preferences"
    )
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=get_main_menu_keyboard())


@router.callback_query(F.data == "cmd:new")
async def cb_new(callback: CallbackQuery):
    await callback.message.edit_text(
        "📝 <b>Select Content Type:</b>\n\nChoose the category for your new post:",
        parse_mode="HTML",
        reply_markup=get_content_type_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "cmd:research")
async def cb_research(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔍 <b>AI Research Studio</b>\n\nSelect a topic category to gather intelligence and generate drafts:",
        parse_mode="HTML",
        reply_markup=get_research_category_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "cmd:channels")
async def cb_channels(callback: CallbackQuery, db: StudioDatabase):
    channels = db.get_channels_for_user(callback.from_user.id)
    if not channels:
        text = "📢 <b>Connected Channels:</b>\n\nNo channels linked yet. Add this bot as Administrator to your channel."
    else:
        text = "📢 <b>Connected Channels:</b>\n\n"
        for ch in channels:
            text += f"• <b>{ch['title']}</b> (ID: <code>{ch['channel_id']}</code>)\n"
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()
