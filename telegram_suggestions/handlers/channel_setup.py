import logging
from aiogram import Router, Bot, F, types
from aiogram.filters import CommandStart, CommandObject, ChatMemberUpdatedFilter, ADMINISTRATOR, KICKED, LEFT
from aiogram.types import ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from ..database.requests import (
    get_or_create_user,
    create_channel,
    get_channel_by_id,
    add_admin
)
from telegram_suggestions.utils.localization import t

router = Router()


# ==================== 1. ДОБАВЛЕНИЕ БОТА В КАНАЛ ====================

@router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=ADMINISTRATOR)
)
async def bot_added_to_channel(event: ChatMemberUpdated, bot: Bot):
    if event.chat.type != "channel":
        return

    channel_id = event.chat.id
    user_id = event.from_user.id
    channel_title = event.chat.title or "Channel"

    user = await get_or_create_user(user_id, event.from_user.language_code)
    lang = user.language_code

    channel = await create_channel(channel_id, owner_id=user_id)
    bot_info = await bot.get_me()
    sub_link = f"https://t.me/{bot_info.username}?start=c_{channel.deep_link_hash}"

    success_text = t("channel_setup_success", lang, channel_title=channel_title, sub_link=sub_link)

    try:
        await bot.send_message(chat_id=user_id, text=success_text, parse_mode="Markdown")
    except (TelegramForbiddenError, TelegramBadRequest):
        reg_link = f"https://t.me/{bot_info.username}?start=reg_{channel_id}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("btn_complete_setup", lang), url=reg_link)
        ]])

        try:
            await bot.send_message(
                chat_id=channel_id,
                text=t("channel_setup_temp_post", lang),
                reply_markup=kb,
                disable_notification=True,
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение в канал: {e}")


@router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=KICKED | LEFT)
)
async def bot_removed_from_channel(event: ChatMemberUpdated, bot: Bot):
    if event.chat.type != "channel":
        return

    user = await get_or_create_user(event.from_user.id)
    lang = user.language_code

    try:
        await bot.send_message(
            chat_id=event.from_user.id,
            text=t("bot_removed_from_channel", lang)
        )
    except Exception:
        pass


# ==================== 2. ОБРАБОТКА DEEP-LINK РЕГИСТРАЦИИ ====================

@router.message(CommandStart(deep_link=True))
async def handle_deep_links(message: types.Message, command: CommandObject, bot: Bot):
    args = command.args
    user_id = message.from_user.id
    user = await get_or_create_user(user_id, message.from_user.language_code)
    lang = user.language_code

    # --- А. Регистрация канала (reg_CHANNEL_ID) ---
    if args.startswith("reg_"):
        try:
            channel_id = int(args.replace("reg_", ""))
        except ValueError:
            return

        try:
            member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status not in ["creator", "administrator"]:
                await message.answer(t("err_not_channel_admin", lang))
                return
        except Exception:
            await message.answer(t("err_check_rights_failed", lang))
            return

        channel = await create_channel(channel_id, owner_id=user_id)
        bot_info = await bot.get_me()
        sub_link = f"https://t.me/{bot_info.username}?start=c_{channel.deep_link_hash}"

        await message.answer(t("reg_success", lang, sub_link=sub_link), parse_mode="Markdown")
        return

    # --- Б. Приглашение со-админа (inv_CHANNEL_ID) ---
    if args.startswith("inv_"):
        try:
            channel_id = int(args.replace("inv_", ""))
        except ValueError:
            return

        try:
            member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status not in ["creator", "administrator"]:
                await message.answer(t("err_inv_not_admin", lang))
                return
        except Exception:
            await message.answer(t("err_channel_not_found", lang))
            return

        added = await add_admin(channel_id, user_id, is_owner=False)
        if added:
            await message.answer(t("coadmin_registered_success", lang))
        else:
            await message.answer(t("coadmin_already_registered", lang))
        return