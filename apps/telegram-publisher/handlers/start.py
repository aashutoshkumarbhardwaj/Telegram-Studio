from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from database import Database

router = Router()

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="✍️ Create Post"), KeyboardButton(text="📢 My Channels")],
        [KeyboardButton(text="📅 Scheduled Posts"), KeyboardButton(text="📜 Post History")],
        [KeyboardButton(text="❓ Help")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

@router.message(CommandStart())
async def cmd_start(message: Message, db: Database):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    
    # Save user to DB
    db.add_user(user_id, username, first_name)
    
    welcome_text = (
        f"Hello, {first_name}! 👋\n\n"
        "I am a bot for posting to your Telegram channels.\n\n"
        "With my help you can:\n"
        "• Add your channels\n"
        "• Create posts with text, media, URL buttons, and reactions\n"
        "• Schedule publications for a specific time\n\n"
        "To get started, add at least one channel in the \"📢 My Channels\" section."
    )
    
    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard())

@router.message(F.text == "❓ Help")
async def cmd_help(message: Message):
    help_text = (
        "ℹ️ <b>Bot Help</b>\n\n"
        "<b>📢 Adding a channel:</b>\n"
        "Go to «My Channels» -> «➕ Add New Channel». The bot will prompt you to select your channel. "
        "Make sure the bot is added to the channel as an administrator with post publishing rights.\n\n"
        "<b>✍️ Creating a post:</b>\n"
        "1. Click «Create Post» and select the desired channel.\n"
        "2. Send text, photo, video, document, audio, sticker, or GIF.\n"
        "3. Add URL buttons (format: <code>Button Text - https://link.com</code>).\n"
        "4. Add reaction buttons (e.g., 👍 👎 🔥).\n"
        "5. Choose «Publish Now» or «Schedule Post».\n\n"
        "<b>📅 Scheduled Posts:</b>\n"
        "You can view scheduled posts, change their publication time, or delete them."
    )
    await message.answer(help_text, parse_mode="HTML")
