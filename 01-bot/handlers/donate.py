import os
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

DONATE_URL = os.getenv("TRIBUTE_DONATE_URL", "")


def donate_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Поддержать проект", url=DONATE_URL)]
    ])


@router.message(F.text == "❤️ Поддержать")
async def cmd_donate(message: Message):
    await message.answer(
        "Бот существует и развивается благодаря поддержке таких людей, как ты 🙏\n\n"
        "Можешь задонатить любую сумму на своё усмотрение — разово или с ежемесячной "
        "подпиской. Сумму и способ оплаты выбираешь на следующем шаге.",
        reply_markup=donate_keyboard(),
    )
