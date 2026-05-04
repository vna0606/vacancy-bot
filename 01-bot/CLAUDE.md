# 01-bot — Telegram-бот (регистрация и профили)

## Зона ответственности

Всё, что связано с взаимодействием пользователя с ботом:
- Команды: /start, /mystacks, /addstack, /removestack, /settings, /stop
- Регистрация нового пользователя в Turso (таблица `users`)
- Просмотр и редактирование своего стека направлений
- Включение/отключение уведомлений

Этот этап НЕ занимается рассылкой вакансий — только управлением профилем.

## Входной контракт

Нет входного контракта от других этапов проекта.
Бот реагирует на события от Telegram API (входящие сообщения и callback'и).

## Выходной контракт (Turso, таблица `users`)

```sql
CREATE TABLE IF NOT EXISTS users (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id          INTEGER UNIQUE NOT NULL,
    username       TEXT,
    stacks         TEXT NOT NULL DEFAULT '',   -- JSON-массив: ["Python","Backend"]
    notify_enabled INTEGER NOT NULL DEFAULT 1,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Этап пишет в эту таблицу. Этап 02-notifier читает из неё — не менять схему без согласования.

## Структура файлов

```
01-bot/
  bot.py              — точка входа, регистрация хендлеров, запуск polling
  handlers/
    start.py          — /start, регистрация
    stacks.py         — /mystacks, /addstack, /removestack
    settings.py       — /settings, /stop (отключить уведомления)
  db/
    turso.py          — клиент Turso, функции работы с таблицей users
    schema.py         — DDL для создания таблицы users при первом запуске
  keyboards/
    stacks_kb.py      — InlineKeyboard для выбора стеков
  .env                — секреты (не в git)
  .env.example        — шаблон
  requirements.txt
```

## Принципы реализации

- Фреймворк: aiogram 3.x (async)
- Turso-клиент: libsql-client (sync-обёртка через asyncio.to_thread) или httpx напрямую к Turso HTTP API
- Стеки хранятся как JSON-строка в поле `stacks`; сериализация/десериализация — в `db/turso.py`
- При /start: если пользователь уже есть в БД — приветствие без перезаписи; если нет — INSERT
- Список допустимых стеков захардкожен в конфиге (constants.py): Python, Backend, Frontend, ML, DevOps, QA, Android, iOS, Data, fullstack
- При обновлении stacks: обновлять поле `updated_at`

## СТРОГИЕ ЗАПРЕТЫ

- НЕ читай файлы из `02-notifier/`
- НЕ реализуй логику рассылки вакансий здесь
- НЕ читай таблицу `vacancies` из этого этапа
- НЕ меняй схему таблицы `users` без обновления корневого CLAUDE.md

## Переменные окружения (.env)

```
TELEGRAM_BOT_TOKEN=...
TURSO_URL=libsql://...
TURSO_TOKEN=...
```
