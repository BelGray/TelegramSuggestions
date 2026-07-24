from aiogram import Router, Bot, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, update

from telegram_suggestions.database.engine import async_session
from telegram_suggestions.database.models import Message, Channel
from telegram_suggestions.database.requests import get_or_create_user, ban_user, unban_user
from telegram_suggestions.utils.localization import t

router = Router()


class AdminReplyFSM(StatesGroup):
    waiting_for_private_reply = State()
    waiting_for_public_reply = State()


# ==================== 1. НАЧАЛО ЛИЧНОГО ОТВЕТА ====================

@router.callback_query(F.data.startswith("rep_priv_"))
async def start_private_reply(callback: types.CallbackQuery, state: FSMContext):
    msg_id = int(callback.data.replace("rep_priv_", ""))
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language_code

    await state.update_data(reply_msg_id=msg_id)
    await callback.message.answer(t("admin_reply_priv_prompt", lang))
    await state.set_state(AdminReplyFSM.waiting_for_private_reply)
    await callback.answer()


@router.message(AdminReplyFSM.waiting_for_private_reply)
async def send_private_reply_to_user(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    msg_id = data["reply_msg_id"]

    user = await get_or_create_user(message.from_user.id)
    lang = user.language_code

    async with async_session() as session:
        res = await session.execute(select(Message).where(Message.id == msg_id))
        orig_msg = res.scalar_one_or_none()

    if not orig_msg:
        await message.answer("❌ Сообщение не найдено.")
        await state.clear()
        return

    # Получаем язык подписчика для отправки ответа
    sender_user = await get_or_create_user(orig_msg.sender_id)
    sender_lang = sender_user.language_code

    try:
        chat = await bot.get_chat(orig_msg.channel_id)
        ch_title = chat.title or "Канал"
    except Exception:
        ch_title = "Канал"

    reply_text = t("sub_received_priv_reply", sender_lang, channel_title=ch_title, text=message.text or "")

    # Пересылаем медиа или текст подписчику
    try:
        if message.photo:
            await bot.send_photo(chat_id=orig_msg.sender_id, photo=message.photo[-1].file_id, caption=reply_text, parse_mode="Markdown")
        elif message.video:
            await bot.send_video(chat_id=orig_msg.sender_id, video=message.video.file_id, caption=reply_text, parse_mode="Markdown")
        else:
            await bot.send_message(chat_id=orig_msg.sender_id, text=reply_text, parse_mode="Markdown")

        # Обновляем статус в БД
        async with async_session() as session:
            await session.execute(update(Message).where(Message.id == msg_id).values(status="answered"))
            await session.commit()

        await message.answer(t("reply_sent_to_user_success", lang))
    except Exception:
        await message.answer("❌ Не удалось отправить ответ. Возможно, подписчик заблокировал бота.")

    await state.clear()


# ==================== 2. ПУБЛИЧНЫЙ ОТВЕТ В КАНАЛ ====================

@router.callback_query(F.data.startswith("rep_pub_"))
async def start_public_reply(callback: types.CallbackQuery, state: FSMContext):
    msg_id = int(callback.data.replace("rep_pub_", ""))
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language_code

    await state.update_data(reply_msg_id=msg_id)
    await callback.message.answer(t("admin_reply_pub_prompt", lang))
    await state.set_state(AdminReplyFSM.waiting_for_public_reply)
    await callback.answer()


@router.message(AdminReplyFSM.waiting_for_public_reply)
async def post_public_reply_to_channel(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    msg_id = data["reply_msg_id"]

    user = await get_or_create_user(message.from_user.id)
    lang = user.language_code

    async with async_session() as session:
        res = await session.execute(select(Message).where(Message.id == msg_id))
        orig_msg = res.scalar_one_or_none()

    if not orig_msg:
        await message.answer("❌ Сообщение не найдено.")
        await state.clear()
        return

    bot_info = await bot.get_me()
    async with async_session() as session:
        res_ch = await session.execute(select(Channel).where(Channel.id == orig_msg.channel_id))
        ch_obj = res_ch.scalar_one_or_none()

    bot_link = f"https://t.me/{bot_info.username}?start=c_{ch_obj.deep_link_hash}" if ch_obj else ""

    sender_str = "🕵️ Анонимный вопрос" if orig_msg.is_anonymous else f"Вопрос от пользователей"

    post_text = (
        f"❓ **{sender_str}**\n"
        f"«_{orig_msg.text or ''}_»\n\n"
        f"💬 **Ответ:**\n"
        f"«_{message.text or ''}_»\n\n"
        f"🤖 *Задать свой вопрос: {bot_link}*"
    )

    try:
        await bot.send_message(chat_id=orig_msg.channel_id, text=post_text, parse_mode="Markdown")

        # Уведомляем автора в ЛС
        sender_user = await get_or_create_user(orig_msg.sender_id)
        try:
            await bot.send_message(chat_id=orig_msg.sender_id, text=t("sub_published_in_channel", sender_user.language_code))
        except Exception:
            pass

        async with async_session() as session:
            await session.execute(update(Message).where(Message.id == msg_id).values(status="published"))
            await session.commit()

        await message.answer(t("post_published_success", lang))
    except Exception as e:
        await message.answer(f"❌ Ошибка при публикации в канал: {e}")

    await state.clear()


# ==================== 3. ПУБЛИКАЦИЯ ИДЕИ ДЛЯ ПОСТА ====================

@router.callback_query(F.data.startswith("pub_idea_"))
async def publish_idea_to_channel(callback: types.CallbackQuery, bot: Bot):
    msg_id = int(callback.data.replace("pub_idea_", ""))
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language_code

    async with async_session() as session:
        res = await session.execute(select(Message).where(Message.id == msg_id))
        orig_msg = res.scalar_one_or_none()

    if not orig_msg:
        await callback.answer("Сообщение не найдено.")
        return

    bot_info = await bot.get_me()
    async with async_session() as session:
        res_ch = await session.execute(select(Channel).where(Channel.id == orig_msg.channel_id))
        ch_obj = res_ch.scalar_one_or_none()

    bot_link = f"https://t.me/{bot_info.username}?start=c_{ch_obj.deep_link_hash}" if ch_obj else ""

    post_text = (
        f"💡 **Идея от подписчика**\n\n"
        f"{orig_msg.text or ''}\n\n"
        f"🤖 *Предложить свою идею: {bot_link}*"
    )

    try:
        if orig_msg.media_type == "photo":
            await bot.send_photo(chat_id=orig_msg.channel_id, photo=orig_msg.media_file_id, caption=post_text, parse_mode="Markdown")
        elif orig_msg.media_type == "video":
            await bot.send_video(chat_id=orig_msg.channel_id, video=orig_msg.media_file_id, caption=post_text, parse_mode="Markdown")
        else:
            await bot.send_message(chat_id=orig_msg.channel_id, text=post_text, parse_mode="Markdown")

        sender_user = await get_or_create_user(orig_msg.sender_id)
        try:
            await bot.send_message(chat_id=orig_msg.sender_id, text=t("sub_idea_published", sender_user.language_code))
        except Exception:
            pass

        async with async_session() as session:
            await session.execute(update(Message).where(Message.id == msg_id).values(status="published"))
            await session.commit()

        await callback.answer(t("post_published_success", lang))
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка публикации: {e}")


# ==================== 4. БЛОКИРОВКА ИЗ КАРТОЧКИ ====================

@router.callback_query(F.data.startswith("ban_"))
async def ban_from_card(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    channel_id, user_id = int(parts[1]), int(parts[2])
    admin_user = await get_or_create_user(callback.from_user.id)
    lang = admin_user.language_code

    await ban_user(channel_id, user_id)

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("btn_unban_user", lang), callback_data=f"unban_card_{channel_id}_{user_id}")
    ]])

    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer(t("card_banned_text", lang))


@router.callback_query(F.data.startswith("unban_card_"))
async def unban_from_card(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    channel_id, user_id = int(parts[2]), int(parts[3])
    admin_user = await get_or_create_user(callback.from_user.id)
    lang = admin_user.language_code

    await unban_user(channel_id, user_id)
    await callback.answer(t("toast_unbanned", lang))