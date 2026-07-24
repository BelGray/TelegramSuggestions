from aiogram import Router, Bot, F, types
from aiogram.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton, PreCheckoutQuery

from telegram_suggestions.database.requests import get_or_create_user
from telegram_suggestions.database.engine import async_session
from telegram_suggestions.database.models import Channel
from sqlalchemy import update
from telegram_suggestions.utils.localization import t

router = Router()


@router.callback_query(F.data.startswith("sub_premium_"))
async def show_premium_options(callback: types.CallbackQuery):
    channel_id = int(callback.data.replace("sub_premium_", ""))
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language_code

    text = t("premium_menu_text", lang)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_plan_1m", lang), callback_data=f"buy_prem_1m_{channel_id}")],
        [InlineKeyboardButton(text=t("btn_plan_3m", lang), callback_data=f"buy_prem_3m_{channel_id}")],
        [InlineKeyboardButton(text=t("btn_plan_life", lang), callback_data=f"buy_prem_life_{channel_id}")],
        [InlineKeyboardButton(text=t("btn_back", lang), callback_data=f"adm_ch_{channel_id}")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("buy_prem_"))
async def send_stars_invoice(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    plan, channel_id = parts[2], int(parts[3])

    if plan == "1m":
        title = "Onward Premium (1 Month)"
        stars_amount = 50
    elif plan == "3m":
        title = "Onward Premium (3 Months)"
        stars_amount = 120
    else:
        title = "Onward Premium (Lifetime)"
        stars_amount = 350

    prices = [LabeledPrice(label=title, amount=stars_amount)]

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=title,
        description=f"Premium access for channel {channel_id}",
        payload=f"stars_pay_{plan}_{channel_id}",
        provider_token="",
        currency="XTR",
        prices=prices
    )
    await callback.answer()


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    user = await get_or_create_user(message.from_user.id)
    lang = user.language_code

    payload = message.successful_payment.invoice_payload
    parts = payload.split("_")
    plan, channel_id = parts[2], int(parts[3])

    async with async_session() as session:
        stmt = update(Channel).where(Channel.id == channel_id).values(is_premium=True)
        await session.execute(stmt)
        await session.commit()

    await message.answer(t("pay_success", lang, channel_id=channel_id), parse_mode="Markdown")