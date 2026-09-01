from aiogram import Router, F, Bot
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, 
    KeyboardButtonRequestChat, ChatAdministratorRights,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from database import Database
from handlers.start import get_main_menu_keyboard

router = Router()

def get_channels_keyboard() -> ReplyKeyboardMarkup:
    # Button to request a channel chat
    btn = KeyboardButton(
        text="➕ Add New Channel",
        request_chat=KeyboardButtonRequestChat(
            request_id=1001,
            chat_is_channel=True,
            user_administrator_rights=ChatAdministratorRights(
                is_anonymous=False,
                can_manage_chat=True,
                can_post_messages=True,
                can_edit_messages=True,
                can_delete_messages=True,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_post_stories=False,
                can_edit_stories=False,
                can_delete_stories=False,
                can_send_welcome_messages=False,
            ),
            bot_administrator_rights=ChatAdministratorRights(
                is_anonymous=False,
                can_manage_chat=True,
                can_post_messages=True,
                can_edit_messages=True,
                can_delete_messages=True,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_post_stories=False,
                can_edit_stories=False,
                can_delete_stories=False,
                can_send_welcome_messages=False,
            ),
            bot_is_member=True,
            request_title=True,
            request_username=True
        )
    )
    back_btn = KeyboardButton(text="🔙 Back to Menu")
    return ReplyKeyboardMarkup(keyboard=[[btn], [back_btn]], resize_keyboard=True)


@router.message(F.text == "📢 My Channels")
async def show_channels_list(message: Message, db: Database):
    user_id = message.from_user.id
    channels = db.get_channels_by_user(user_id)
    
    # Always update reply keyboard when entering channels section
    await message.answer("📢 Channel Management:", reply_markup=get_channels_keyboard())
    
    if not channels:
        text = (
            "📢 <b>You don't have any connected channels yet.</b>\n\n"
            "To add a channel, click the <b>«➕ Add New Channel»</b> button on the keyboard below. "
            "You will be prompted to select a channel where you are an administrator, "
            "and add our bot there with permissions to publish posts."
        )
        await message.answer(text, parse_mode="HTML")
        return
        
    text = "📢 <b>Your connected channels:</b>\n\nSelect a channel to manage:"
    
    keyboard_rows = []
    for chan in channels:
        title = chan['title']
        username = chan['username']
        display_name = f"{title} (@{username})" if username else title
        keyboard_rows.append([InlineKeyboardButton(text=display_name, callback_data=f"chan_view:{chan['channel_id']}")])
        
    # Add an inline helper button
    keyboard_rows.append([InlineKeyboardButton(text="➕ Connect another channel", callback_data="chan_add_prompt")])
        
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    await message.answer(text, parse_mode="HTML", reply_markup=markup)


@router.message(F.chat_shared)
async def handle_chat_shared(message: Message, bot: Bot, db: Database):
    chat_shared = message.chat_shared
    if chat_shared.request_id != 1001:
        return
        
    channel_id = chat_shared.chat_id
    user_id = message.from_user.id
    
    try:
        # Check bot's status and permissions in the channel
        member = await bot.get_chat_member(channel_id, bot.id)
        if member.status not in ('administrator', 'creator'):
            await message.answer(
                "❌ <b>Error:</b> The bot is not an administrator in the selected channel.\n"
                "Please add the bot to the channel as an administrator with permission to send messages.",
                parse_mode="HTML"
            )
            return
            
        if not member.can_post_messages:
            await message.answer(
                "❌ <b>Error:</b> The bot does not have permission to post messages in the channel.\n"
                "Please grant the bot the \"Post Messages\" administrator right.",
                parse_mode="HTML"
            )
            return
            
        # Get up-to-date channel info
        chat = await bot.get_chat(channel_id)
        db.add_channel(channel_id, chat.title or "Channel", chat.username or "", user_id)
        
        await message.answer(
            f"✅ <b>Channel successfully connected!</b>\n\n"
            f"<b>Title:</b> {chat.title}\n"
            f"<b>ID:</b> <code>{channel_id}</code>\n"
            f"<b>Link:</b> " + (f"@{chat.username}" if chat.username else "Private channel") + "\n\n"
            "You can now create posts for this channel!",
            parse_mode="HTML",
            reply_markup=get_channels_keyboard()
        )
        
    except Exception as e:
        await message.answer(
            f"❌ <b>Failed to verify bot permissions in the channel.</b>\n"
            f"Make sure the bot has been added to the channel as an administrator with posting rights.\n"
            f"Details: {e}",
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("chan_view:"))
async def view_channel_details(callback: CallbackQuery, db: Database, bot: Bot):
    channel_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    # Verify user has access to this channel in our DB
    user_channels = db.get_channels_by_user(user_id)
    channel = next((c for c in user_channels if c['channel_id'] == channel_id), None)
    
    if not channel:
        await callback.answer("Channel not found or you don't have permissions.", show_alert=True)
        return
        
    # Query current details
    try:
        chat = await bot.get_chat(channel_id)
        title = chat.title
        username = chat.username
    except Exception:
        title = channel['title']
        username = channel['username']
        
    text = (
        f"📢 <b>Channel Info:</b>\n\n"
        f"<b>Title:</b> {title}\n"
        f"<b>ID:</b> <code>{channel_id}</code>\n"
        f"<b>Link:</b> " + (f"@{username}" if username else "Private channel") + "\n"
    )
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑️ Delete Channel from Bot", callback_data=f"chan_del:{channel_id}")],
        [InlineKeyboardButton(text="🔙 Back to List", callback_data="chan_list")]
    ])
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data == "chan_list")
async def back_to_channels_list(callback: CallbackQuery, db: Database):
    user_id = callback.from_user.id
    channels = db.get_channels_by_user(user_id)
    
    if not channels:
        text = "📢 <b>You don't have any connected channels yet.</b>"
        markup = None
    else:
        text = "📢 <b>Your connected channels:</b>\n\nSelect a channel to manage:"
        keyboard_rows = []
        for chan in channels:
            title = chan['title']
            username = chan['username']
            display_name = f"{title} (@{username})" if username else title
            keyboard_rows.append([InlineKeyboardButton(text=display_name, callback_data=f"chan_view:{chan['channel_id']}")])
        keyboard_rows.append([InlineKeyboardButton(text="➕ Connect another channel", callback_data="chan_add_prompt")])
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
        
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("chan_del:"))
async def delete_channel(callback: CallbackQuery, db: Database):
    channel_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    db.remove_channel(channel_id, user_id)
    await callback.answer("Channel removed from your list.", show_alert=True)
    
    # Refresh list
    channels = db.get_channels_by_user(user_id)
    if not channels:
        await callback.message.edit_text(
            "📢 <b>You don't have any connected channels yet.</b>",
            parse_mode="HTML",
            reply_markup=None
        )
    else:
        text = "📢 <b>Your connected channels:</b>\n\nSelect a channel to manage:"
        keyboard_rows = []
        for chan in channels:
            title = chan['title']
            username = chan['username']
            display_name = f"{title} (@{username})" if username else title
            keyboard_rows.append([InlineKeyboardButton(text=display_name, callback_data=f"chan_view:{chan['channel_id']}")])
        keyboard_rows.append([InlineKeyboardButton(text="➕ Connect another channel", callback_data="chan_add_prompt")])
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data == "chan_add_prompt")
async def channel_add_prompt(callback: CallbackQuery):
    await callback.message.answer(
        "To connect a new channel, click the <b>«➕ Add New Channel»</b> button on the keyboard below 👇",
        parse_mode="HTML",
        reply_markup=get_channels_keyboard()
    )
    await callback.answer()


@router.message(F.text == "🔙 Back to Menu")
async def back_to_menu(message: Message):
    await message.answer("You have returned to the main menu.", reply_markup=get_main_menu_keyboard())
