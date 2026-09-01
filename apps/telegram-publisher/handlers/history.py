import json
import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, MessageOriginChannel
from aiogram.exceptions import TelegramBadRequest

from database import Database
from handlers.start import get_main_menu_keyboard
from handlers.post_creator import parse_buttons
from services.post_service import build_inline_keyboard

logger = logging.getLogger(__name__)
def get_friendly_error_message(error_str: str) -> str:
    err_lower = error_str.lower()
    if "message_id_invalid" in err_lower or "message to edit not found" in err_lower:
        return "Invalid message ID (MESSAGE_ID_INVALID).\nMake sure this message was sent by THIS EXACT BOT (bots cannot edit messages from other users/bots) and has not been deleted from the channel."
    if "message can't be edited" in err_lower:
        return "Message cannot be edited.\nMake sure the message was published by this bot and the bot has permissions to edit messages."
    if "message is not modified" in err_lower:
        return "Message content was not modified (the new text or buttons are identical to the current ones)."
    if "chat not found" in err_lower:
        return "Channel not found. Make sure the bot is added to the channel as an administrator."
    return error_str


router = Router()

class EditPostedPost(StatesGroup):
    input_text = State()
    input_buttons = State()

@router.message(F.text == "📜 Post History")
async def show_posted_history(message: Message, db: Database):
    user_id = message.from_user.id
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, c.title as channel_title 
            FROM posts p
            JOIN channels c ON p.channel_id = c.channel_id
            WHERE p.user_id = ? AND p.status = 'posted'
            ORDER BY p.created_at DESC
            LIMIT 10
        """, (user_id,))
        posts = [dict(row) for row in cursor.fetchall()]
        
    if not posts:
        await message.answer("📜 <b>You don't have any published posts in history yet.</b>", parse_mode="HTML")
        return
        
    text = "📜 <b>History of your published posts (last 10):</b>\n\nSelect a post to edit in the channel:"
    keyboard_rows = []
    for post in posts:
        post_id = post['post_id']
        chan_title = post['channel_title']
        post_text = post.get('text') or ""
        # Create a snippet of the post text
        snippet = post_text[:20] + "..." if len(post_text) > 20 else (post_text or f"Media ({post['content_type']})")
        display_name = f"📢 {chan_title}: {snippet}"
        keyboard_rows.append([InlineKeyboardButton(text=display_name, callback_data=f"hist_view:{post_id}")])
        
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    await message.answer(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data.startswith("hist_view:"))
async def view_history_post(callback: CallbackQuery, db: Database):
    post_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    post = db.get_post(post_id)
    if not post or post['user_id'] != user_id:
        await callback.answer("Post not found.")
        return
        
    channels = db.get_channels_by_user(user_id)
    channel = next((c for c in channels if c['channel_id'] == post['channel_id']), None)
    chan_title = channel['title'] if channel else f"ID: {post['channel_id']}"
    
    text = (
        f"📜 <b>Published Post #{post_id}</b>\n\n"
        f"<b>Channel:</b> {chan_title}\n"
        f"<b>Content type:</b> <code>{post['content_type']}</code>\n"
    )
    if post.get('text'):
        preview_text = post['text']
        if len(preview_text) > 300:
            preview_text = preview_text[:300] + "..."
        text += f"\n<b>Text/Caption:</b>\n{preview_text}\n"
        
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Edit text on channel", callback_data=f"hist_edit_txt:{post_id}"),
            InlineKeyboardButton(text="🔗 Edit buttons on channel", callback_data=f"hist_edit_btn:{post_id}")
        ],
        [InlineKeyboardButton(text="🔙 Back to List", callback_data="hist_list")]
    ])
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data == "hist_list")
async def back_to_history_list(callback: CallbackQuery, db: Database):
    user_id = callback.from_user.id
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, c.title as channel_title 
            FROM posts p
            JOIN channels c ON p.channel_id = c.channel_id
            WHERE p.user_id = ? AND p.status = 'posted'
            ORDER BY p.created_at DESC
            LIMIT 10
        """, (user_id,))
        posts = [dict(row) for row in cursor.fetchall()]
        
    if not posts:
        await callback.message.edit_text("📜 <b>You don't have any published posts in history yet.</b>", parse_mode="HTML")
        await callback.answer()
        return
        
    text = "📜 <b>History of your published posts (last 10):</b>\n\nSelect a post to edit in the channel:"
    keyboard_rows = []
    for post in posts:
        post_id = post['post_id']
        chan_title = post['channel_title']
        post_text = post.get('text') or ""
        snippet = post_text[:20] + "..." if len(post_text) > 20 else (post_text or f"Media ({post['content_type']})")
        display_name = f"📢 {chan_title}: {snippet}"
        keyboard_rows.append([InlineKeyboardButton(text=display_name, callback_data=f"hist_view:{post_id}")])
        
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("hist_edit_txt:"))
async def request_new_text(callback: CallbackQuery, state: FSMContext):
    post_id = int(callback.data.split(":")[1])
    await state.update_data(edit_post_id=post_id)
    await state.set_state(EditPostedPost.input_text)
    
    await callback.message.answer(
        "📝 <b>Send the new text/caption for the channel post:</b>\n"
        "The bot will update the text and preserve original formatting. Click «❌ Cancel» to abort.",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Cancel")]], resize_keyboard=True)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("hist_edit_btn:"))
async def request_new_buttons(callback: CallbackQuery, state: FSMContext):
    post_id = int(callback.data.split(":")[1])
    await state.update_data(edit_post_id=post_id)
    await state.set_state(EditPostedPost.input_buttons)
    
    text = (
        "🔗 <b>Edit URL buttons on channel</b>\n\n"
        "Send new buttons in the format: <code>Button Text - https://link.com</code>.\n"
        "Each line is a new row, separator for buttons in the same row is <code>|</code>.\n\n"
        "Send <code>none</code> to remove all buttons."
    )
    await callback.message.answer(text, parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Cancel")]], resize_keyboard=True))
    await callback.answer()


@router.message(EditPostedPost.input_text)
async def process_new_text(message: Message, state: FSMContext, db: Database, bot: Bot):
    if message.text == "❌ Cancel":
        await state.clear()
        await message.answer("Editing cancelled.", reply_markup=get_main_menu_keyboard())
        return
        
    new_text = message.html_text
    data = await state.get_data()
    post_id = data['edit_post_id']
    
    # Update text in DB
    db.update_post(post_id, text=new_text)
    
    # Get post & sent mapping
    post = db.get_post(post_id)
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id, message_id FROM sent_posts WHERE post_id = ?", (post_id,))
        sent_messages = cursor.fetchall()
        
    if not sent_messages:
        await message.answer("❌ Error: No linked messages found in the database for this post.", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
        
    success_count = 0
    fail_errors = []
    
    markup = build_inline_keyboard(post, db)
    
    for row in sent_messages:
        channel_id = row[0]
        message_id = row[1]
        try:
            if post['content_type'] == 'text':
                await bot.edit_message_text(
                    chat_id=channel_id,
                    message_id=message_id,
                    text=new_text,
                    reply_markup=markup,
                    parse_mode="HTML"
                )
            else:
                await bot.edit_message_caption(
                    chat_id=channel_id,
                    message_id=message_id,
                    caption=new_text,
                    reply_markup=markup,
                    parse_mode="HTML"
                )
            success_count += 1
        except TelegramBadRequest as e:
            fail_errors.append(get_friendly_error_message(str(e)))
        except Exception as e:
            fail_errors.append(get_friendly_error_message(str(e)))
            
        await state.clear()
    
    if success_count > 0:
        await message.answer(
            f"✅ <b>Post successfully edited in the channel!</b>\n"
            f"Messages updated: {success_count}.",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        err_msg = "\n".join(fail_errors)
        await message.answer(
            f"❌ <b>Failed to update post in the channel.</b>\n\n"
            f"<b>Error details:</b>\n<code>{err_msg}</code>\n\n"
            f"<i>Note: The bot must remain an administrator in the channel with the «Edit Messages» permission enabled.</i>",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )


@router.message(EditPostedPost.input_buttons)
async def process_new_buttons(message: Message, state: FSMContext, db: Database, bot: Bot):
    if message.text == "❌ Cancel":
        await state.clear()
        await message.answer("Editing cancelled.", reply_markup=get_main_menu_keyboard())
        return
        
    text = message.text.strip()
    data = await state.get_data()
    post_id = data['edit_post_id']
    
    try:
        buttons_json = None
        if text.lower() != 'none':
            buttons = parse_buttons(text)
            buttons_json = json.dumps(buttons)
            
        # Update buttons in DB
        db.update_post(post_id, buttons_json=buttons_json)
        
        # Get post & sent messages
        post = db.get_post(post_id)
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT channel_id, message_id FROM sent_posts WHERE post_id = ?", (post_id,))
            sent_messages = cursor.fetchall()
            
        if not sent_messages:
            await message.answer("❌ Error: No linked messages found in the database for this post.", reply_markup=get_main_menu_keyboard())
            await state.clear()
            return
            
        success_count = 0
        fail_errors = []
        
        markup = build_inline_keyboard(post, db)
        
        for row in sent_messages:
            channel_id = row[0]
            message_id = row[1]
            try:
                await bot.edit_message_reply_markup(
                    chat_id=channel_id,
                    message_id=message_id,
                    reply_markup=markup
                )
                success_count += 1
            except TelegramBadRequest as e:
                fail_errors.append(get_friendly_error_message(str(e)))
            except Exception as e:
                fail_errors.append(get_friendly_error_message(str(e)))
                
        await state.clear()
        
        if success_count > 0:
            await message.answer(
                f"✅ <b>Post buttons successfully updated in the channel!</b>\n"
                f"Messages updated: {success_count}.",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            err_msg = "\n".join(fail_errors)
            await message.answer(
                f"❌ <b>Failed to update buttons in the channel.</b>\n\n"
                f"<b>Error details:</b>\n<code>{err_msg}</code>",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard()
            )
            
    except ValueError as e:
        await message.answer(f"❌ <b>Button format error:</b>\n{e}\n\nTry again or send <code>none</code>.", parse_mode="HTML")


# 11. Forwarded post handler (Auto-registration and direct editing)
@router.message(F.forward_origin)
async def handle_forwarded_post(message: Message, bot: Bot, db: Database):
    user_id = message.from_user.id
    origin = message.forward_origin
    
    if not isinstance(origin, MessageOriginChannel):
        await message.answer("⚠️ Please forward a message specifically from a <b>channel</b>.", parse_mode="HTML")
        return
        
    channel_id = origin.chat.id
    message_id = origin.message_id
    
    # 1. Verify user is admin in that channel
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        if member.status not in ('administrator', 'creator'):
            await message.answer("❌ You must be an administrator in this channel to edit posts.")
            return
    except Exception as e:
        await message.answer("❌ The bot cannot access this channel. Make sure the bot is added to the channel as an administrator.")
        return

    # 2. Make sure channel is registered in DB (auto-register if not)
    user_channels = db.get_channels_by_user(user_id)
    channel_linked = next((c for c in user_channels if c['channel_id'] == channel_id), None)
    
    if not channel_linked:
        try:
            chat = await bot.get_chat(channel_id)
            db.add_channel(channel_id, chat.title or "Channel", chat.username or "", user_id)
            await message.answer(f"📢 Channel «{chat.title}» was automatically connected to your account!")
        except Exception:
            db.add_channel(channel_id, "Channel", "", user_id)
            await message.answer("📢 Channel was automatically connected to your account!")

    # 3. Check if we already have this post in DB
    post = db.get_post_by_sent_msg(channel_id, message_id)
    
    if not post:
        # Create a new post record so we can edit it
        content_type = None
        media_file_id = None
        text = None
        
        # Determine content type
        if message.text:
            content_type = 'text'
            text = message.html_text
        elif message.photo:
            content_type = 'photo'
            media_file_id = message.photo[-1].file_id
            text = message.html_text
        elif message.video:
            content_type = 'video'
            media_file_id = message.video.file_id
            text = message.html_text
        elif message.document:
            content_type = 'document'
            media_file_id = message.document.file_id
            text = message.html_text
        elif message.audio:
            content_type = 'audio'
            media_file_id = message.audio.file_id
            text = message.html_text
        elif message.voice:
            content_type = 'voice'
            media_file_id = message.voice.file_id
            text = message.html_text
        elif message.animation:
            content_type = 'animation'
            media_file_id = message.animation.file_id
            text = message.html_text
        elif message.sticker:
            content_type = 'sticker'
            media_file_id = message.sticker.file_id
        else:
            await message.answer("❌ This message format is not supported for editing.")
            return

        post_id = db.create_post(
            user_id=user_id,
            channel_id=channel_id,
            content_type=content_type,
            text=text,
            media_file_id=media_file_id,
            status='posted'
        )
        # Link sent post
        db.add_sent_post(channel_id, message_id, post_id)
        post = db.get_post(post_id)
    else:
        post_id = post['post_id']

    # Show menu to edit
    try:
        chat_info = await bot.get_chat(channel_id)
        chan_title = chat_info.title or "Channel"
    except Exception:
        chan_title = "Channel"
    
    preview_text = (
        f"🎯 <b>Recognized forwarded post #{post_id}</b>\n\n"
        f"<b>Channel:</b> {chan_title}\n"
        f"<b>Content type:</b> <code>{post['content_type']}</code>\n"
    )
    if post.get('text'):
        snippet = post['text']
        if len(snippet) > 300:
            snippet = snippet[:300] + "..."
        preview_text += f"\n<b>Current text/caption:</b>\n{snippet}\n"
        
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Edit text on channel", callback_data=f"hist_edit_txt:{post_id}"),
            InlineKeyboardButton(text="🔗 Edit buttons on channel", callback_data=f"hist_edit_btn:{post_id}")
        ],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="hist_cancel_edit")]
    ])
    
    await message.answer(preview_text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data == "hist_cancel_edit")
async def cancel_history_edit(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Editing cancelled.", reply_markup=get_main_menu_keyboard())
    await callback.answer()
