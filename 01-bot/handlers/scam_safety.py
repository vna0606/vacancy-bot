from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message


router = Router()

ARTICLE_URL = "https://telegra.ph/Ostorozhno-moshenniki-09-18-3"


@router.message(F.text == "⚠️ Про мошенников")
async def cmd_scam_safety(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Читать статью", url=ARTICLE_URL),
    ]])
    await message.answer(
        "⚠️ Актуальные схемы мошенничества при поиске работы и правила безопасности:",
        reply_markup=keyboard,
    )
