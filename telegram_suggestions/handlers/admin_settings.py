from aiogram import Router, Bot, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from telegram_suggestions.database.requests import (
    get_or_create_user,
    get_user_channels,
    get_channel_by_id,
    update_channel_settings,
    get_admin_record,
    update_admin_personal_settings,
    get_banned_users,
    unban_user
)
from telegram_suggestions.utils.localization import t

router = Router()


# ==================== 1. ГЛАВНОЕ МЕНЮ АДМИНА ====================

async def show_admin_channels_list(event_obj, user_id: int, bot: Bot):
    """Отрисовка списка каналов админа (поддерживает и Message, и CallbackQuery)"""
    user = await get_or_create_user(user_id)
    lang = user.language_code

    channels = await get_user_channels(user_id)
    if not channels:
        text = t("admin_welcome_no_channels", lang)
        if isinstance(event_obj, types.Message):
            await event_obj.answer(text, parse_mode="Markdown")
        else:
            await event_obj.message.edit_text(text, parse_mode="Markdown")
        return

    kb_buttons = []
    for ch in channels:
        try:
            chat = await bot.get_chat(ch.id)
            title = chat.title or f"Канал {ch.id}"
        except Exception:
            title = f"Канал {ch.id}"

        kb_buttons.append([InlineKeyboardButton(text=f"📢 {title}", callback_data=f"adm_ch_{ch.id}")])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    text = t("admin_panel_welcome", lang)

    if isinstance(event_obj, types.Message):
        await event_obj.answer(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await event_obj.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.message(Command("admin"))
@router.message(Command("start"))
async def open_admin_panel(message: types.Message, bot: Bot):
    await show_admin_channels_list(message, message.from_user.id, bot)


@router.callback_query(F.data == "back_channels")
async def back_to_channels(callback: types.CallbackQuery, bot: Bot):
    await show_admin_channels_list(callback, callback.from_user.id, bot)
    await callback.answer()


# ==================== 2. МЕНЮ УПРАВЛЕНИЯ КАНАЛОМ ====================

@router.callback_query(F.data.startswith("adm_ch_"))
async def open_channel_menu(callback: types.CallbackQuery, bot: Bot):
    channel_id = int(callback.data.replace("adm_ch_", ""))
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language_code

    channel = await get_channel_by_id(channel_id)
    bot_info = await bot.get_me()
    sub_link = f"https://t.me/{bot_info.username}?start=c_{channel.deep_link_hash}"

    try:
        chat = await bot.get_chat(channel_id)
        ch_title = chat.title or "Channel"
    except Exception:
        ch_title = "Channel"

    status_str = t("status_premium", lang) if channel.is_premium else t("status_free", lang)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_set_btns", lang), callback_data=f"set_btns_{channel_id}")],
        [InlineKeyboardButton(text=t("btn_set_profile", lang), callback_data=f"set_profile_{channel_id}")],
        [InlineKeyboardButton(text=t("btn_add_coadmin", lang), callback_data=f"get_inv_{channel_id}")],
        [InlineKeyboardButton(text=t("btn_ban_list", lang), callback_data=f"ban_list_{channel_id}")],
        [InlineKeyboardButton(text=t("btn_premium", lang), callback_data=f"sub_premium_{channel_id}")],
        [InlineKeyboardButton(text=t("btn_back_channels", lang), callback_data="back_channels")]
    ])

    text = t("admin_channel_manage", lang, ch_title=ch_title, status=status_str, sub_link=sub_link)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


# ==================== 3. НАСТРОЙКА КНОПОК ПРЕДЛОЖКИ ====================

async def show_buttons_menu(callback: types.CallbackQuery, channel_id: int):
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language_code

    channel = await get_channel_by_id(channel_id)
    settings = channel.settings or {}

    btn_ideas = ("✅ " if settings.get("ideas", True) else "❌ ") + t("btn_idea", lang)
    btn_qall = ("✅ " if settings.get("questions_all", True) else "❌ ") + t("btn_question_all", lang)
    btn_reviews = ("✅ " if settings.get("reviews", True) else "❌ ") + t("btn_review", lang)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_ideas, callback_data=f"tog_ideas_{channel_id}")],
        [InlineKeyboardButton(text=btn_qall, callback_data=f"tog_qall_{channel_id}")],
        [InlineKeyboardButton(text=btn_reviews, callback_data=f"tog_rev_{channel_id}")],
        [InlineKeyboardButton(text=t("btn_back", lang), callback_data=f"adm_ch_{channel_id}")]
    ])

    await callback.message.edit_text(t("header_set_btns", lang), reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("set_btns_"))
async def toggle_buttons_menu_entry(callback: types.CallbackQuery):
    channel_id = int(callback.data.replace("set_btns_", ""))
    await show_buttons_menu(callback, channel_id)


@router.callback_query(F.data.startswith("tog_"))
async def process_toggle_button(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    key, channel_id = parts[1], int(parts[2])

    channel = await get_channel_by_id(channel_id)
    settings = channel.settings or {}

    setting_key = "ideas" if key == "ideas" else "questions_all" if key == "qall" else "reviews"
    settings[setting_key] = not settings.get(setting_key, True)

    await update_channel_settings(channel_id, settings)
    await show_buttons_menu(callback, channel_id)


# ==================== 4. ПЕРСОНАЛЬНЫЙ ПРОФИЛЬ АДМИНА ====================

async def show_admin_profile_settings(callback: types.CallbackQuery, channel_id: int):
    user_id = callback.from_user.id
    user = await get_or_create_user(user_id)
    lang = user.language_code

    admin_rec = await get_admin_record(channel_id, user_id)
    accepts = admin_rec.accepts_direct_questions if admin_rec else True
    disp_type = admin_rec.display_type if admin_rec else "anon"

    status_accepts = t("btn_accepts_on", lang) if accepts else t("btn_accepts_off", lang)

    disp_anon = "🟢 Админ №X" if disp_type == "anon" else "⚪ Админ №X"
    disp_name = "🟢 Имя" if disp_type == "name" else "⚪ Имя"
    disp_username = "🟢 @username" if disp_type == "username" else "⚪ @username"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=status_accepts, callback_data=f"prof_acc_{channel_id}")],
        [
            InlineKeyboardButton(text=disp_anon, callback_data=f"prof_dt_{channel_id}_anon"),
            InlineKeyboardButton(text=disp_name, callback_data=f"prof_dt_{channel_id}_name"),
            InlineKeyboardButton(text=disp_username, callback_data=f"prof_dt_{channel_id}_username")
        ],
        [InlineKeyboardButton(text=t("btn_back", lang), callback_data=f"adm_ch_{channel_id}")]
    ])

    await callback.message.edit_text(t("header_set_profile", lang), reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("set_profile_"))
async def admin_profile_settings_entry(callback: types.CallbackQuery):
    channel_id = int(callback.data.replace("set_profile_", ""))
    await show_admin_profile_settings(callback, channel_id)


@router.callback_query(F.data.startswith("prof_acc_"))
async def toggle_accepts_questions(callback: types.CallbackQuery):
    channel_id = int(callback.data.replace("prof_acc_", ""))
    user_id = callback.from_user.id

    admin_rec = await get_admin_record(channel_id, user_id)
    new_accepts = not (admin_rec.accepts_direct_questions if admin_rec else True)
    disp_type = admin_rec.display_type if admin_rec else "anon"

    await update_admin_personal_settings(channel_id, user_id, new_accepts, disp_type)
    await show_admin_profile_settings(callback, channel_id)


@router.callback_query(F.data.startswith("prof_dt_"))
async def change_display_type(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    channel_id = int(parts[2])
    new_disp_type = parts[3]
    user_id = callback.from_user.id

    admin_rec = await get_admin_record(channel_id, user_id)
    accepts = admin_rec.accepts_direct_questions if admin_rec else True

    await update_admin_personal_settings(channel_id, user_id, accepts, new_disp_type)
    await show_admin_profile_settings(callback, channel_id)


# ==================== 5. ПРИГЛАШЕНИЕ СО-АДМИНА И СПИСОК БАНОВ ====================

@router.callback_query(F.data.startswith("get_inv_"))
async def get_invite_link(callback: types.CallbackQuery, bot: Bot):
    channel_id = int(callback.data.replace("get_inv_", ""))
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language_code

    bot_info = await bot.get_me()
    inv_link = f"https://t.me/{bot_info.username}?start=inv_{channel_id}"

    text = t("coadmin_text", lang, inv_link=inv_link)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t("btn_back", lang), callback_data=f"adm_ch_{channel_id}")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


async def show_banned_users_menu(callback: types.CallbackQuery, channel_id: int):
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language_code

    bans = await get_banned_users(channel_id)

    if not bans:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=t("btn_back", lang), callback_data=f"adm_ch_{channel_id}")]])
        await callback.message.edit_text(t("ban_list_empty", lang), reply_markup=kb)
        return

    kb_buttons = []
    for b in bans:
        kb_buttons.append([InlineKeyboardButton(
            text=f"🔓 Unban (ID: {b.user_id})",
            callback_data=f"unban_usr_{channel_id}_{b.user_id}"
        )])

    kb_buttons.append([InlineKeyboardButton(text=t("btn_back", lang), callback_data=f"adm_ch_{channel_id}")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.edit_text(t("ban_list_header", lang), reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("ban_list_"))
async def show_banned_users_entry(callback: types.CallbackQuery):
    channel_id = int(callback.data.replace("ban_list_", ""))
    await show_banned_users_menu(callback, channel_id)


@router.callback_query(F.data.startswith("unban_usr_"))
async def process_unban_user(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    channel_id, target_user_id = int(parts[2]), int(parts[3])
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language_code

    await unban_user(channel_id, target_user_id)
    await callback.answer(t("toast_unbanned", lang))
    await show_banned_users_menu(callback, channel_id)