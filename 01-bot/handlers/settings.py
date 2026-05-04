from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from db import get_user, upsert_user, update_notify

router = Router()


async def _show_notify(message: Message):
    tg_id = message.from_user.id
    user = await get_user(tg_id)
    if user is None:
        await upsert_user(tg_id, message.from_user.username or '', message.from_user.full_name or '')
        user = await get_user(tg_id)

    enabled = user.get('notify_enabled', 1)
    status = 'включены ✅' if enabled else 'выключены ❌'
    toggle_text = '❌ Выключить' if enabled else '✅ Включить'
    toggle_cb = 'notify_off' if enabled else 'notify_on'

    await message.answer(
        f'Уведомления сейчас: *{status}*\n\nЕжедневная рассылка вакансий по твоему стеку.',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=toggle_text, callback_data=toggle_cb)
        ]])
    )


@router.message(Command('notify'))
async def cmd_notify(message: Message):
    await _show_notify(message)


@router.message(F.text == "🔔 Уведомления")
async def btn_notify(message: Message):
    await _show_notify(message)


@router.callback_query(F.data.in_({'notify_on', 'notify_off'}))
async def cb_notify_toggle(callback: CallbackQuery):
    tg_id = callback.from_user.id
    enabled = 1 if callback.data == 'notify_on' else 0
    await update_notify(tg_id, enabled)
    status = 'включены ✅' if enabled else 'выключены ❌'
    toggle_text = '❌ Выключить' if enabled else '✅ Включить'
    toggle_cb = 'notify_off' if enabled else 'notify_on'
    await callback.message.edit_text(
        f'Уведомления сейчас: *{status}*\n\nЕжедневная рассылка вакансий по твоему стеку.',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=toggle_text, callback_data=toggle_cb)
        ]])
    )
    await callback.answer('Сохранено!')


@router.message(Command('status'))
async def cmd_status(message: Message):
    await _show_profile(message)


@router.message(F.text == "👤 Мой профиль")
async def btn_profile(message: Message):
    await _show_profile(message)


async def _show_profile(message: Message):
    tg_id = message.from_user.id
    user = await get_user(tg_id)
    if user is None:
        await upsert_user(tg_id, message.from_user.username or '', message.from_user.full_name or '')
        user = await get_user(tg_id)

    stacks = user.get('stacks') or []
    stacks_str = ', '.join(stacks) if stacks else 'не выбрано'
    notify = 'включены ✅' if user.get('notify_enabled', 1) else 'выключены ❌'

    await message.answer(
        f'👤 *Твой профиль*\n\n'
        f'Имя: {user.get("full_name", "")}\n'
        f'Стек: {stacks_str}\n'
        f'Уведомления: {notify}'
    )
