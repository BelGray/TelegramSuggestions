import logging
from aiogram import Router, Bot, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, update

from telegram_suggestions.database.engine import async_session
from telegram_suggestions.database.models import Message, Channel
from telegram_suggestions.database.requests import get_or_create_user, ban_user, unban_user, is_channel_premium, get_admin_notifications
from telegram_suggestions.utils.localization import t

router = Router()


class AdminReplyFSM(StatesGroup):
    waiting_for_private_reply = State()
    waiting_for_public_reply = State()


async def sync_all_admin_cards(db_msg_id: int, actor_user_id: int, actor_name: str, action_key: str, answer_text: str, bot: Bot):
    """Синхронизация и обновление карточек у всех админов канала"""
    notifications = await get_admin_notifications(db_msg_id)

    async with async_session() as session:
        res = await session.execute(select(Message).where(Message.id == db_msg_id))
        orig_msg = res.scalar_one_or_none()

    orig_text = orig_msg.text if orig_msg and orig_msg.text else "[Media]"

    for notif in notifications:
        try:
            adm = await get_or_create_user(notif.admin_user_id)
            lang = adm.language_code

            action_str = t(action_key, lang)
            card_text = t(
                "admin_card_processed",
                lang,
                orig_text=orig_text,
                actor_name=actor_name,
                action_str=action_str,
                answer_text=answer_text
            )

            try:
                await bot.edit_message_caption(chat_id=notif.admin_user_id, message_id=notif.telegram_message_id, caption=card_text, reply_markup=None)
            except Exception:
                await bot.edit_message_text(chat_id=notif.admin_user_id, message_id=notif.telegram_message_id, text=card_text, reply_markup=None)
        except Exception as e:
            logging.error(f"Не удалось обновить карточку у админа {notif.admin_user_id}: {e}")

@router.callback_query(F.data.startswith("rep_priv_"))
async def start_private_reply(callback: types.CallbackQuery, state: FSMContext):
    msg_id = int(callback.data.replace("rep_priv_", ""))
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language_code

    await state.update_data(reply_msg_id=msg_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("btn_back", lang), callback_data="cancel_reply")]])
    await callback.message.answer(t("admin_reply_priv_prompt", lang), reply_markup=kb)
    await state.set_state(AdminReplyFSM.waiting_for_private_reply)
    await callback.answer()


@router.callback_query(F.data == "cancel_reply")
async def cancel_reply(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()


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
        await message.answer(t("err_msg_not_found", lang))
        await state.clear()
        return

    sender_user = await get_or_create_user(orig_msg.sender_id)
    sender_lang = sender_user.language_code

    try:
        chat = await bot.get_chat(orig_msg.channel_id)
        ch_title = chat.title or "Channel"
    except Exception:
        ch_title = "Channel"

    reply_text = t("sub_received_priv_reply", sender_lang, channel_title=ch_title, text=message.text or "")

    try:
        if message.photo:
            await bot.send_photo(chat_id=orig_msg.sender_id, photo=message.photo[-1].file_id, caption=reply_text)
        elif message.video:
            await bot.send_video(chat_id=orig_msg.sender_id, video=message.video.file_id, caption=reply_text)
        else:
            await bot.send_message(chat_id=orig_msg.sender_id, text=reply_text)

        async with async_session() as session:
            await session.execute(update(Message).where(Message.id == msg_id).values(status="answered"))
            await session.commit()

        # Имя админа берется прямо из Telegram
        actor_name = message.from_user.first_name or "Admin"
        await sync_all_admin_cards(msg_id, message.from_user.id, actor_name, "action_priv_reply", message.text or "[Media]", bot)

        await message.answer(t("reply_sent_to_user_success", lang))
    except Exception as e:
        logging.error(f"Ошибка отправки личного ответа: {e}")
        await message.answer(t("err_cant_reply", lang))

    await state.clear()


@router.callback_query(F.data.startswith("rep_pub_"))
async def start_public_reply(callback: types.CallbackQuery, state: FSMContext):
    msg_id = int(callback.data.replace("rep_pub_", ""))
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language_code

    await state.update_data(reply_msg_id=msg_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("btn_back", lang), callback_data="cancel_reply")]])
    await callback.message.answer(t("admin_reply_pub_prompt", lang), reply_markup=kb)
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
        await message.answer(t("err_msg_not_found", lang))
        await state.clear()
        return

    bot_info = await bot.get_me()
    async with async_session() as session:
        res_ch = await session.execute(select(Channel).where(Channel.id == orig_msg.channel_id))
        ch_obj = res_ch.scalar_one_or_none()

    has_prem = await is_channel_premium(ch_obj) if ch_obj else False
    settings = ch_obj.settings if ch_obj else {}
    show_copyright = settings.get("show_copyright", True)

    bot_link = f"https://t.me/{bot_info.username}?start=c_{ch_obj.deep_link_hash}" if ch_obj else ""

    sender_str = t("anon_question_title", lang) if orig_msg.is_anonymous else t("public_question_title", lang)
    reply_hdr = t("channel_reply_header", lang)
    ask_prompt = t("channel_ask_prompt", lang, bot_link=bot_link) if (not has_prem or show_copyright) else ""

    post_text = (
        f"{sender_str}\n"
        f"«{orig_msg.text or ''}»\n\n"
        f"{reply_hdr}\n"
        f"«{message.text or ''}»"
    )
    if ask_prompt:
        post_text += f"\n\n{ask_prompt}"

    try:
        await bot.send_message(chat_id=orig_msg.channel_id, text=post_text)

        sender_user = await get_or_create_user(orig_msg.sender_id)
        try:
            await bot.send_message(chat_id=orig_msg.sender_id, text=t("sub_published_in_channel", sender_user.language_code))
        except Exception:
            pass

        async with async_session() as session:
            await session.execute(update(Message).where(Message.id == msg_id).values(status="published"))
            await session.commit()

        actor_name = message.from_user.first_name or "Admin"
        await sync_all_admin_cards(msg_id, message.from_user.id, actor_name, "action_pub_reply", message.text or "", bot)

        await message.answer(t("post_published_success", lang))
    except Exception as e:
        await message.answer(t("err_publish_failed", lang, error=str(e)))

    await state.clear()


@router.callback_query(F.data.startswith("pub_idea_"))
async def publish_idea_to_channel(callback: types.CallbackQuery, bot: Bot):
    msg_id = int(callback.data.replace("pub_idea_", ""))
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language_code

    async with async_session() as session:
        res = await session.execute(select(Message).where(Message.id == msg_id))
        orig_msg = res.scalar_one_or_none()

    if not orig_msg:
        await callback.answer(t("err_msg_not_found", lang))
        return

    bot_info = await bot.get_me()
    async with async_session() as session:
        res_ch = await session.execute(select(Channel).where(Channel.id == orig_msg.channel_id))
        ch_obj = res_ch.scalar_one_or_none()

    has_prem = await is_channel_premium(ch_obj) if ch_obj else False
    settings = ch_obj.settings if ch_obj else {}
    show_copyright = settings.get("show_copyright", True)

    bot_link = f"https://t.me/{bot_info.username}?start=c_{ch_obj.deep_link_hash}" if ch_obj else ""

    idea_hdr = t("idea_post_header", lang)
    idea_prompt = t("idea_suggest_prompt", lang, bot_link=bot_link) if (not has_prem or show_copyright) else ""

    post_text = f"{idea_hdr}\n\n{orig_msg.text or ''}"
    if idea_prompt:
        post_text += f"\n\n{idea_prompt}"

    try:
        if orig_msg.media_type == "photo":
            await bot.send_photo(chat_id=orig_msg.channel_id, photo=orig_msg.media_file_id, caption=post_text)
        elif orig_msg.media_type == "video":
            await bot.send_video(chat_id=orig_msg.channel_id, video=orig_msg.media_file_id, caption=post_text)
        else:
            await bot.send_message(chat_id=orig_msg.channel_id, text=post_text)

        sender_user = await get_or_create_user(orig_msg.sender_id)
        try:
            await bot.send_message(chat_id=orig_msg.sender_id, text=t("sub_idea_published", sender_user.language_code))
        except Exception:
            pass

        async with async_session() as session:
            await session.execute(update(Message).where(Message.id == msg_id).values(status="published"))
            await session.commit()

        actor_name = callback.from_user.first_name or "Admin"
        await sync_all_admin_cards(msg_id, callback.from_user.id, actor_name, "action_published_idea", orig_msg.text or "[Media]", bot)

        await callback.answer(t("post_published_success", lang))
    except Exception as e:
        await callback.message.answer(t("err_publish_failed", lang, error=str(e)))


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