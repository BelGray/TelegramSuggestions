from aiogram import Router, Bot, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from telegram_suggestions.database.requests import (
    get_or_create_user,
    get_user_channels,
    get_channel_by_id,
    update_channel_settings,
    get_admin_record,
    update_admin_personal_settings,
    get_banned_users,
    unban_user,
    is_channel_premium,
    set_channel_welcome_message,
    set_channel_auto_reply
)
from telegram_suggestions.utils.localization import t

router = Router()


class AdminSettingsFSM(StatesGroup):
    waiting_for_welcome_msg = State()
    waiting_for_auto_reply = State()


async def show_admin_channels_list(event_obj, user_id: int, bot: Bot, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(user_id)
    lang = user.language_code

    channels = await get_user_channels(user_id)
    if not channels:
        text = t("admin_welcome_no_channels", lang)
        if isinstance(event_obj, types.Message):
            await event_obj.answer(text)
        else:
            await event_obj.message.edit_text(text)
        return

    kb_buttons = []
    for ch in channels:
        try:
            chat = await bot.get_chat(ch.id)
            title = chat.title or f"Channel {ch.id}"
        except Exception:
            title = f"Channel {ch.id}"

        kb_buttons.append([InlineKeyboardButton(text=f"📢 {title}", callback_data=f"adm_ch_{ch.id}")])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    text = t("admin_panel_welcome", lang)

    if isinstance(event_obj, types.Message):
        await event_obj.answer(text, reply_markup=kb)
    else:
        await event_obj.message.edit_text(text, reply_markup=kb)


@router.message(Command("admin"))
@router.message(Command("start"))
async def open_admin_panel(message: types.Message, bot: Bot, state: FSMContext):
    await show_admin_channels_list(message, message.from_user.id, bot, state)


@router.callback_query(F.data == "back_channels")
async def back_to_channels(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    await show_admin_channels_list(callback, callback.from_user.id, bot, state)
    await callback.answer()


@router.callback_query(F.data.startswith("adm_ch_"))
async def open_channel_menu(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    await state.clear()
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

    has_prem = await is_channel_premium(channel)
    status_str = t("status_premium", lang) if has_prem else t("status_free", lang)

    buttons = [
        [InlineKeyboardButton(text=t("btn_set_btns", lang), callback_data=f"set_btns_{channel_id}")],
        [InlineKeyboardButton(text=t("btn_set_profile", lang), callback_data=f"set_profile_{channel_id}")],
        [InlineKeyboardButton(text=t("btn_add_coadmin", lang), callback_data=f"get_inv_{channel_id}")],
        [InlineKeyboardButton(text=t("btn_ban_list", lang), callback_data=f"ban_list_{channel_id}")]
    ]

    if has_prem:
        buttons.append(
            [InlineKeyboardButton(text=t("btn_manage_premium", lang), callback_data=f"prem_manage_{channel_id}")])
    else:
        buttons.append([InlineKeyboardButton(text=t("btn_premium", lang), callback_data=f"sub_premium_{channel_id}")])

    buttons.append([InlineKeyboardButton(text=t("btn_back_channels", lang), callback_data="back_channels")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = t("admin_channel_manage", lang, ch_title=ch_title, status=status_str, sub_link=sub_link)
    await callback.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data.startswith("prem_manage_"))
async def manage_premium_menu(callback: types.CallbackQuery):
    channel_id = int(callback.data.replace("prem_manage_", ""))
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language_code

    channel = await get_channel_by_id(channel_id)
    settings = channel.settings or {}
    show_copy = settings.get("show_copyright", True)

    btn_copy_status = t("btn_copyright_on", lang) if show_copy else t("btn_copyright_off", lang)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_set_welcome", lang), callback_data=f"set_welc_{channel_id}")],
        [InlineKeyboardButton(text=t("btn_set_autoreply", lang), callback_data=f"set_autorep_{channel_id}")],
        [InlineKeyboardButton(text=btn_copy_status, callback_data=f"tog_copy_{channel_id}")],
        [InlineKeyboardButton(text=t("btn_back", lang), callback_data=f"adm_ch_{channel_id}")]
    ])

    await callback.message.edit_text(t("premium_settings_header", lang), reply_markup=kb)


@router.callback_query(F.data.startswith("set_welc_"))
async def prompt_welcome(callback: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.replace("set_welc_", ""))
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language_code

    await state.update_data(channel_id=channel_id)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t("btn_reset", lang), callback_data=f"reset_welc_{channel_id}")]])
    await callback.message.edit_text(t("prompt_enter_welcome", lang), reply_markup=kb)
    await state.set_state(AdminSettingsFSM.waiting_for_welcome_msg)


@router.message(AdminSettingsFSM.waiting_for_welcome_msg)
async def process_save_welcome(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    channel_id = data["channel_id"]
    user = await get_or_create_user(message.from_user.id)
    lang = user.language_code

    await set_channel_welcome_message(channel_id, message.text)
    await message.answer(t("welcome_saved_success", lang))
    await open_admin_panel(message, bot, state)


@router.callback_query(F.data.startswith("reset_welc_"))
async def reset_welcome(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    channel_id = int(callback.data.replace("reset_welc_", ""))
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language_code

    await set_channel_welcome_message(channel_id, None)
    await callback.answer(t("welcome_reset_success", lang))
    await open_admin_panel(callback.message, bot, state)


@router.callback_query(F.data.startswith("set_autorep_"))
async def prompt_autoreply(callback: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.replace("set_autorep_", ""))
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language_code

    await state.update_data(channel_id=channel_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_reset", lang), callback_data=f"reset_autorep_{channel_id}")]])
    await callback.message.edit_text(t("prompt_enter_autoreply", lang), reply_markup=kb)
    await state.set_state(AdminSettingsFSM.waiting_for_auto_reply)


@router.message(AdminSettingsFSM.waiting_for_auto_reply)
async def process_save_autoreply(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    channel_id = data["channel_id"]
    user = await get_or_create_user(message.from_user.id)
    lang = user.language_code

    await set_channel_auto_reply(channel_id, message.text)
    await message.answer(t("autoreply_saved_success", lang))
    await open_admin_panel(message, bot, state)


@router.callback_query(F.data.startswith("reset_autorep_"))
async def reset_autoreply(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    channel_id = int(callback.data.replace("reset_autorep_", ""))
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language_code

    await set_channel_auto_reply(channel_id, None)
    await callback.answer(t("autoreply_reset_success", lang))
    await open_admin_panel(callback.message, bot, state)


@router.callback_query(F.data.startswith("tog_copy_"))
async def toggle_copyright(callback: types.CallbackQuery):
    channel_id = int(callback.data.replace("tog_copy_", ""))
    channel = await get_channel_by_id(channel_id)
    settings = channel.settings or {}

    settings["show_copyright"] = not settings.get("show_copyright", True)
    await update_channel_settings(channel_id, settings)
    await manage_premium_menu(callback)


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

    await callback.message.edit_text(t("header_set_btns", lang), reply_markup=kb)


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


async def show_admin_profile_settings(callback: types.CallbackQuery, channel_id: int):
    user_id = callback.from_user.id
    user = await get_or_create_user(user_id)
    lang = user.language_code

    admin_rec = await get_admin_record(channel_id, user_id)
    accepts = admin_rec.accepts_direct_questions if admin_rec else True
    disp_type = admin_rec.display_type if admin_rec else "anon"

    status_accepts = t("btn_accepts_on", lang) if accepts else t("btn_accepts_off", lang)

    disp_anon = f"🟢 {t('disp_anon_title', lang)}" if disp_type == "anon" else f"⚪ {t('disp_anon_title', lang)}"
    disp_name = f"🟢 {t('disp_name_title', lang)}" if disp_type == "name" else f"⚪ {t('disp_name_title', lang)}"
    disp_username = f"🟢 {t('disp_username_title', lang)}" if disp_type == "username" else f"⚪ {t('disp_username_title', lang)}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=status_accepts, callback_data=f"prof_acc_{channel_id}")],
        [
            InlineKeyboardButton(text=disp_anon, callback_data=f"prof_dt_{channel_id}_anon"),
            InlineKeyboardButton(text=disp_name, callback_data=f"prof_dt_{channel_id}_name"),
            InlineKeyboardButton(text=disp_username, callback_data=f"prof_dt_{channel_id}_username")
        ],
        [InlineKeyboardButton(text=t("btn_back", lang), callback_data=f"adm_ch_{channel_id}")]
    ])

    await callback.message.edit_text(t("header_set_profile", lang), reply_markup=kb)


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
    await callback.message.edit_text(text, reply_markup=kb)


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
            text=t("btn_unban_id", lang, user_id=b.user_id),
            callback_data=f"unban_usr_{channel_id}_{b.user_id}"
        )])

    kb_buttons.append([InlineKeyboardButton(text=t("btn_back", lang), callback_data=f"adm_ch_{channel_id}")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.edit_text(t("ban_list_header", lang), reply_markup=kb)


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