from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from db import get_user, upsert_user, update_stacks

router = Router()

ALL_STACKS = [
    "Backend",
    "Frontend",
    "FullStack",
    "Mobile",
    "DevOps",
    "ML/AI",
    "Data",
    "QA",
    "PM",
]

STACK_MENU_TEXT = (
    "Выбери одно или несколько направлений — буду присылать вакансии по каждому.\n"
    "Mobile включает iOS, Android и Flutter.\n"
    "PM — Product Manager.\n\n"
    "Нажми 💾 Сохранить когда закончишь:"
)

JOIN_COMMUNITY_TEXT = (
    "🔒 Чтобы получать ежедневные подборки вакансий — вступи в наше закрытое сообщество.\n\n"
    "Как только вступишь, нажми /start и рассылка сразу начнётся по твоему стеку."
)


def build_stacks_keyboard(selected: list) -> InlineKeyboardMarkup:
    buttons = []
    for stack in ALL_STACKS:
        mark = "✅" if stack in selected else "◻️"
        buttons.append(
            InlineKeyboardButton(
                text=f"{mark} {stack}",
                callback_data=f"stack_toggle:{stack}",
            )
        )
    rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(text="💾 Сохранить", callback_data="stack_save")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _show_stacks(message: Message):
    tg_id = message.from_user.id
    user = await get_user(tg_id)
    if user is None:
        await upsert_user(tg_id, message.from_user.username or "", message.from_user.full_name or "")
        selected = []
    else:
        selected = user.get("stacks") or []
    await message.answer(STACK_MENU_TEXT, reply_markup=build_stacks_keyboard(selected))


@router.message(Command("setstacks"))
async def cmd_setstacks(message: Message):
    await _show_stacks(message)


@router.message(F.text == "⚙️ Настроить стек")
async def btn_setstacks(message: Message):
    await _show_stacks(message)


@router.message(Command("mystacks"))
async def cmd_mystacks(message: Message):
    tg_id = message.from_user.id
    user = await get_user(tg_id)
    selected = user.get("stacks") or [] if user else []
    stacks_str = ", ".join(selected) if selected else "не выбрано"
    await message.answer(
        f"Твои направления: *{stacks_str}*",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✏️ Изменить", callback_data="open_setstacks")
        ]])
    )


@router.callback_query(F.data == "open_setstacks")
async def cb_open_setstacks(callback: CallbackQuery):
    tg_id = callback.from_user.id
    user = await get_user(tg_id)
    selected = user.get("stacks") or [] if user else []
    await callback.message.edit_text(
        STACK_MENU_TEXT,
        reply_markup=build_stacks_keyboard(selected),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("stack_toggle:"))
async def cb_stack_toggle(callback: CallbackQuery):
    stack = callback.data.split(":", 1)[1]
    tg_id = callback.from_user.id
    user = await get_user(tg_id)
    selected = list(user.get("stacks") or []) if user else []

    if stack in selected:
        selected.remove(stack)
    else:
        selected.append(stack)

    await callback.message.edit_reply_markup(reply_markup=build_stacks_keyboard(selected))
    await update_stacks(tg_id, selected)
    await callback.answer()


@router.callback_query(F.data == "stack_save")
async def cb_stack_save(callback: CallbackQuery):
    tg_id = callback.from_user.id
    user = await get_user(tg_id)
    selected = user.get("stacks") or [] if user else []
    stacks_str = ", ".join(selected) if selected else "не выбрано"

    is_active = int(user.get("notify_enabled", 0)) if user else 0

    if is_active:
        text = (
            f"✅ Готово! Буду присылать вакансии по: *{stacks_str}*\n\n"
            "Изменить можно через кнопку *⚙️ Настроить стек* в меню."
        )
    else:
        text = (
            f"✅ Стек сохранён: *{stacks_str}*\n\n"
            + JOIN_COMMUNITY_TEXT
        )

    await callback.message.edit_text(text)
    await callback.answer("Сохранено!")
