import logging
from aiogram import Router, Bot, F, types
from aiogram.filters import CommandStart, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from telegram_suggestions.database.requests import (
    get_or_create_user,
    get_channel_by_hash,
    get_channel_rating,
    get_channel_by_id,
    get_channel_admins,
    check_review_cooldown,
    is_user_banned,
    add_message,
    is_channel_premium,
    add_admin_notification
)
from telegram_suggestions.utils.localization import t

router = Router()


class SubscriberFSM(StatesGroup):
    choosing_anonymity = State()
    waiting_for_idea = State()
    waiting_for_question_all = State()
    waiting_for_question_admin = State()
    waiting_for_review_rating = State()
    waiting_for_review_text = State()


# ==================== 1. ВХОД ПО ССЫЛКЕ КАНАЛА (c_HASH) ====================

@router.message(CommandStart(deep_link=True, magic=F.args.startswith("c_")))
async def open_subscriber_menu(message: types.Message, command: CommandObject, state: FSMContext, bot: Bot):
    await state.clear()

    hash_str = command.args.replace("c_", "")
    user_id = message.from_user.id
    user = await get_or_create_user(user_id, message.from_user.language_code)
    lang = user.language_code

    channel = await get_channel_by_hash(hash_str)
    if not channel:
        await message.answer(t("err_channel_not_found_subscriber", lang))
        return

    if await is_user_banned(channel.id, user_id):
        await message.answer(t("user_banned_error", lang))
        return

    try:
        chat = await bot.get_chat(channel.id)
        channel_title = chat.title or "Channel"
    except Exception:
        channel_title = "Channel"

    rating_count, rating_avg = await get_channel_rating(channel.id)
    rating_str = ""
    if rating_count >= 5:
        rating_str = t("rating_line", lang, avg_rating=rating_avg, count=rating_count)

    settings = channel.settings or {}
    keyboard_buttons = []

    if settings.get("ideas", True):
        keyboard_buttons.append(
            [InlineKeyboardButton(text=t("btn_idea", lang), callback_data=f"sub_idea_{channel.id}")])

    if settings.get("questions_all", True):
        keyboard_buttons.append(
            [InlineKeyboardButton(text=t("btn_question_all", lang), callback_data=f"sub_qall_{channel.id}")])

    admins = await get_channel_admins(channel.id)
    active_admins = [a for a in admins if a.accepts_direct_questions]
    if active_admins:
        keyboard_buttons.append(
            [InlineKeyboardButton(text=t("btn_question_admin", lang), callback_data=f"sub_qadmin_{channel.id}")])

    if settings.get("reviews", True):
        keyboard_buttons.append(
            [InlineKeyboardButton(text=t("btn_review", lang), callback_data=f"sub_review_{channel.id}")])

    kb = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    # Кастомное приветствие работает, если активирован Премиум
    has_premium = await is_channel_premium(channel)
    if has_premium and channel.welcome_message:
        welcome_text = channel.welcome_message
    else:
        welcome_text = t("sub_menu_header", lang, channel_title=channel_title, rating_str=rating_str)

    await message.answer(welcome_text, reply_markup=kb)


# ==================== 2. ВЫБОР АНОНИМНОСТИ ====================

async def ask_anonymity(callback: types.CallbackQuery, state: FSMContext, lang: str):
    username = callback.from_user.username or callback.from_user.first_name
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("btn_anon", lang), callback_data="anon_true"),
        InlineKeyboardButton(text=t("btn_public", lang, username=username), callback_data="anon_false")
    ]])
    await callback.message.edit_text(t("choose_anonymity", lang), reply_markup=kb)
    await state.set_state(SubscriberFSM.choosing_anonymity)


@router.callback_query(F.data.startswith("sub_idea_"))
async def start_idea(callback: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.replace("sub_idea_", ""))
    await state.update_data(channel_id=channel_id, msg_type="idea")
    user = await get_or_create_user(callback.from_user.id)
    await ask_anonymity(callback, state, user.language_code)


@router.callback_query(F.data.startswith("sub_qall_"))
async def start_question_all(callback: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.replace("sub_qall_", ""))
    await state.update_data(channel_id=channel_id, msg_type="question_all")
    user = await get_or_create_user(callback.from_user.id)
    await ask_anonymity(callback, state, user.language_code)


@router.callback_query(F.data.startswith("sub_qadmin_"))
async def choose_admin_list(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    channel_id = int(callback.data.replace("sub_qadmin_", ""))
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language_code

    admins = await get_channel_admins(channel_id)
    active_admins = [a for a in admins if a.accepts_direct_questions]

    kb_buttons = []
    for idx, admin in enumerate(active_admins, 1):
        if admin.display_type == "name":
            try:
                tg_user = await bot.get_chat(admin.user_id)
                display_name = tg_user.first_name or f"{t('disp_anon_title', lang).replace('X', str(idx))}"
            except Exception:
                display_name = f"{t('disp_anon_title', lang).replace('X', str(idx))}"
        elif admin.display_type == "username":
            try:
                tg_user = await bot.get_chat(admin.user_id)
                display_name = f"@{tg_user.username}" if tg_user.username else f"{t('disp_anon_title', lang).replace('X', str(idx))}"
            except Exception:
                display_name = f"{t('disp_anon_title', lang).replace('X', str(idx))}"
        else:
            display_name = f"{t('disp_anon_title', lang).replace('X', str(idx))}"

        kb_buttons.append([InlineKeyboardButton(
            text=f"👤 {display_name}",
            callback_data=f"pick_adm_{channel_id}_{admin.user_id}"
        )])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.edit_text(t("prompt_choose_admin", lang), reply_markup=kb)


@router.callback_query(F.data.startswith("pick_adm_"))
async def admin_picked(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    channel_id, target_admin_id = int(parts[2]), int(parts[3])
    await state.update_data(channel_id=channel_id, msg_type="question_admin", target_admin_id=target_admin_id)
    user = await get_or_create_user(callback.from_user.id)
    await ask_anonymity(callback, state, user.language_code)


@router.callback_query(SubscriberFSM.choosing_anonymity, F.data.startswith("anon_"))
async def process_anonymity_choice(callback: types.CallbackQuery, state: FSMContext):
    is_anon = callback.data == "anon_true"
    await state.update_data(is_anonymous=is_anon)

    data = await state.get_data()
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language_code

    if data["msg_type"] == "idea":
        await callback.message.edit_text(t("prompt_send_idea", lang))
        await state.set_state(SubscriberFSM.waiting_for_idea)
    else:
        await callback.message.edit_text(t("prompt_send_question", lang))
        await state.set_state(SubscriberFSM.waiting_for_question_all)


# ==================== 3. ОТПРАВКА ИДЕИ ИЛИ ВОПРОСА ====================

@router.message(StateFilter(SubscriberFSM.waiting_for_idea, SubscriberFSM.waiting_for_question_all))
async def receive_suggestion_content(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    channel_id = data["channel_id"]
    msg_type = data["msg_type"]
    is_anon = data["is_anonymous"]
    target_admin_id = data.get("target_admin_id")

    user_id = message.from_user.id
    user = await get_or_create_user(user_id, message.from_user.language_code)
    lang = user.language_code

    text = message.text or message.caption or ""
    media_file_id, media_type = None, None

    if message.photo:
        media_file_id, media_type = message.photo[-1].file_id, "photo"
    elif message.video:
        media_file_id, media_type = message.video.file_id, "video"
    elif message.voice:
        media_file_id, media_type = message.voice.file_id, "voice"
    elif message.document:
        media_file_id, media_type = message.document.file_id, "document"

    db_msg = await add_message(
        channel_id=channel_id,
        sender_id=user_id,
        msg_type=msg_type,
        is_anonymous=is_anon,
        text=text,
        media_file_id=media_file_id,
        media_type=media_type,
        target_admin_id=target_admin_id
    )

    try:
        chat = await bot.get_chat(channel_id)
        ch_title = chat.title or "Channel"
    except Exception:
        ch_title = "Channel"

    sender_info = t("btn_anon", lang) if is_anon else f"@{message.from_user.username or message.from_user.first_name}"

    if target_admin_id:
        target_admins = [target_admin_id]
    else:
        admins_list = await get_channel_admins(channel_id)
        target_admins = [a.user_id for a in admins_list]

        # Внутри receive_suggestion_content в файле subscriber.py:
        for adm_id in target_admins:
            try:
                adm_user = await get_or_create_user(adm_id)
                adm_lang = adm_user.language_code

                media_txt = t("media_placeholder", adm_lang)
                admin_card_text = t("admin_new_idea", adm_lang, channel_title=ch_title, sender_info=sender_info,
                                    text=text or media_txt) if msg_type == "idea" else t("admin_new_question", adm_lang,
                                                                                         channel_title=ch_title,
                                                                                         sender_info=sender_info,
                                                                                         text=text or media_txt)

                buttons = []
                if msg_type == "idea":
                    buttons.append([InlineKeyboardButton(text=t("btn_publish_idea", adm_lang),
                                                         callback_data=f"pub_idea_{db_msg.id}")])

                buttons.append([
                    InlineKeyboardButton(text=t("btn_reply_private", adm_lang), callback_data=f"rep_priv_{db_msg.id}"),
                    InlineKeyboardButton(text=t("btn_reply_public", adm_lang), callback_data=f"rep_pub_{db_msg.id}")
                ])
                buttons.append([InlineKeyboardButton(text=t("btn_ban_user", adm_lang),
                                                     callback_data=f"ban_{channel_id}_{user_id}")])

                kb = InlineKeyboardMarkup(inline_keyboard=buttons)

                if media_type == "photo":
                    sent_m = await bot.send_photo(chat_id=adm_id, photo=media_file_id, caption=admin_card_text,
                                                  reply_markup=kb)
                elif media_type == "video":
                    sent_m = await bot.send_video(chat_id=adm_id, video=media_file_id, caption=admin_card_text,
                                                  reply_markup=kb)
                elif media_type == "voice":
                    sent_m = await bot.send_voice(chat_id=adm_id, voice=media_file_id, caption=admin_card_text,
                                                  reply_markup=kb)
                elif media_type == "document":
                    sent_m = await bot.send_document(chat_id=adm_id, document=media_file_id, caption=admin_card_text,
                                                     reply_markup=kb)
                else:
                    sent_m = await bot.send_message(chat_id=adm_id, text=admin_card_text, reply_markup=kb)

                # Сохраняем ID отправленного сообщения для синхронизации
                if sent_m:
                    await add_admin_notification(db_msg.id, adm_id, sent_m.message_id)

            except Exception as e:
                logging.error(f"Ошибка отправки сообщения админу {adm_id}: {e}")

    # Уведомление об успешной отправке + Автоответ если включен Премиум
    channel_obj = await get_channel_by_id(channel_id)
    has_prem = await is_channel_premium(channel_obj)

    if has_prem and channel_obj.auto_reply:
        await message.answer(f"{t('msg_sent_success', lang)}\n\n🤖 **Автоответ канала:**\n{channel_obj.auto_reply}")
    else:
        await message.answer(t("msg_sent_success", lang))

    await state.clear()


# ==================== 4. ОСТАВИТЬ ОТЗЫВ И ОЦЕНКУ ====================

@router.callback_query(F.data.startswith("sub_review_"))
async def start_review(callback: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.replace("sub_review_", ""))
    user_id = callback.from_user.id
    user = await get_or_create_user(user_id)
    lang = user.language_code

    can_review, days_left = await check_review_cooldown(channel_id, user_id)
    if not can_review:
        await callback.message.answer(t("review_cooldown_error", lang, days_left=days_left))
        await callback.answer()
        return

    await state.update_data(channel_id=channel_id)

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="1 ⭐", callback_data="rate_1"),
        InlineKeyboardButton(text="2 ⭐", callback_data="rate_2"),
        InlineKeyboardButton(text="3 ⭐", callback_data="rate_3"),
        InlineKeyboardButton(text="4 ⭐", callback_data="rate_4"),
        InlineKeyboardButton(text="5 ⭐", callback_data="rate_5")
    ]])

    await callback.message.edit_text(t("prompt_select_rating", lang), reply_markup=kb)
    await state.set_state(SubscriberFSM.waiting_for_review_rating)


@router.callback_query(SubscriberFSM.waiting_for_review_rating, F.data.startswith("rate_"))
async def rating_selected(callback: types.CallbackQuery, state: FSMContext):
    stars = int(callback.data.replace("rate_", ""))
    await state.update_data(rating_value=stars)

    user = await get_or_create_user(callback.from_user.id)
    lang = user.language_code

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("btn_skip", lang), callback_data="skip_review_text")
    ]])

    await callback.message.edit_text(t("prompt_send_review_text", lang), reply_markup=kb)
    await state.set_state(SubscriberFSM.waiting_for_review_text)


@router.message(SubscriberFSM.waiting_for_review_text)
async def process_review_text(message: types.Message, state: FSMContext):
    await save_and_notify_review(message.from_user.id, message.text, state, message)


@router.callback_query(SubscriberFSM.waiting_for_review_text, F.data == "skip_review_text")
async def process_review_skip(callback: types.CallbackQuery, state: FSMContext):
    await save_and_notify_review(callback.from_user.id, None, state, callback.message)


async def save_and_notify_review(user_id: int, text: str, state: FSMContext, event_obj):
    data = await state.get_data()
    channel_id = data["channel_id"]
    rating_value = data["rating_value"]

    user = await get_or_create_user(user_id)
    lang = user.language_code

    await add_message(
        channel_id=channel_id,
        sender_id=user_id,
        msg_type="review",
        is_anonymous=True,
        text=text,
        rating_value=rating_value
    )

    if isinstance(event_obj, types.Message):
        await event_obj.answer(t("review_saved_success", lang))
    else:
        await event_obj.edit_text(t("review_saved_success", lang))

    await state.clear()