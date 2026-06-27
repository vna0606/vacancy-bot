# 01-bot — Telegram-бот (регистрация, профили, приём вакансий)

## Зона ответственности

Всё, что связано с взаимодействием пользователя с ботом:
- Команды: /start, /mystacks, /setstacks, /notify, /status
- Регистрация нового пользователя в Turso (таблица `users`)
- Просмотр и редактирование своего стека направлений
- Включение/отключение уведомлений
- Приём вакансий от пользователей (кнопка «📨 Разместить вакансию»): фильтрация
  (rule-based + LLM, только технические IT-вакансии), LLM-форматирование по шаблону,
  создание Telegraph-страницы с полным текстом, модерация админом, запись одобренных
  вакансий в таблицу `vacancies`
- Админ-функции: статистика (`/stats`), пересылка сообщений пользователей админу и ответ
  через reply (`handlers/admin.py`)
- Донаты (кнопка «❤️ Поддержать»): только отдаёт статическую ссылку на донат-страницу Tribute.
  Приём вебхуков об оплате, запись в `donations`, благодарность донору — отдельный этап
  `03-tribute-webhook/` (Vercel, другой стек) — см. корневой `CLAUDE.md`

Рассылкой вакансий пользователям этот этап не занимается — это зона `02-notifier`.

## Входной контракт

Нет входного контракта от других этапов проекта.
Бот реагирует на события от Telegram API (входящие сообщения и callback'и).

## Выходные контракты (Turso)

### Таблица `users` (пишет этот этап, читает `02-notifier`)

```sql
CREATE TABLE IF NOT EXISTS users (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id                  INTEGER UNIQUE NOT NULL,
    username               TEXT,
    full_name              TEXT,
    stacks                 TEXT NOT NULL DEFAULT '',   -- JSON-массив: ["Python","Backend"]
    notify_enabled         INTEGER NOT NULL DEFAULT 1,
    notify_hour            INTEGER,
    ref_source             TEXT,                       -- payload из /start (например "youtube")
    disabled_reason        TEXT,                       -- 'manual' / 'blocked' / 'non_member'
    last_seen_at           TIMESTAMP,
    stacks_set_at          TIMESTAMP,
    vacancy_submitted_at   TIMESTAMP,                  -- когда впервые подал заявку на вакансию
    vacancy_submit_count   INTEGER NOT NULL DEFAULT 0, -- сколько раз подавал заявок
    created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Не менять схему без обновления корневого `CLAUDE.md` и `02-notifier/CLAUDE.md`.

### Таблица `vacancy_submissions` (пишет и читает только этот этап)

```sql
CREATE TABLE IF NOT EXISTS vacancy_submissions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id        INTEGER NOT NULL,
    status       TEXT NOT NULL,   -- 'pending' / 'approved' / 'rejected'
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Фиксирует каждую заявку на вакансию и её итог. Используется для сегментации при рассылках
(кто подавал, кто одобрен, кто отклонён). Поля `vacancy_submitted_at` и `vacancy_submit_count`
в `users` — агрегаты для быстрой фильтрации без JOIN с этой таблицей.

### Таблица `vacancies` (пишет этот этап ПОСЛЕ одобрения админом; также пишет `it-vacancies-base`, читает `02-notifier`)

```sql
-- INSERT (db.py:insert_vacancy) использует подмножество колонок реальной схемы:
INSERT INTO vacancies
  (raw_post_id, title, company_name, recruiter_contact,
   salary, work_format, telegraph_url, direction, category, dedup_key)
VALUES (0, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```

`raw_post_id` всегда `0` для вакансий, пришедших через бота (не из автопайплайна
`it-vacancies-base`). Полная схема таблицы — в корневом `CLAUDE.md`. Это теперь ДВА
независимых писателя в одну таблицу — менять схему можно только согласовав с обеих сторон.

`dedup_key` — колонка, уже существующая в схеме (создана `it-vacancies-base/03-processor`,
используется для предотвращения повторной публикации той же вакансии в течение 7 дней).
Бот вычисляет её тем же алгоритмом (`vacancy_dedup.py`, портировано из
`it-vacancies-base/03-processor/db_processor.py`) и проверяет на совпадение через
`db.py:find_duplicate_vacancy()` ПЕРЕД созданием Telegraph-страницы и отправкой на модерацию —
если вакансия с тем же ключом уже была за последние 7 дней, пользователю показывается
предупреждение со ссылкой на существующую публикацию вместо повторной отправки.

## Структура файлов

```
01-bot/
  bot.py                  — точка входа: регистрация роутеров, APScheduler-джоба ежедневного дайджеста, polling
  db.py                   — клиент Turso (httpx), функции работы с users и vacancies
  vacancy_keywords.py     — ~900 IT-ключевых слов для фильтра (портировано из it-vacancies-base)
  vacancy_filter.py       — быстрый regex-фильтр технических вакансий (relevant/irrelevant/uncertain)
  vacancy_llm_filter.py   — LLM-проверка для "uncertain" случаев vacancy_filter
  vacancy_formatter.py    — LLM-форматирование текста вакансии по шаблону + category/direction
  telegraph.py            — создание Telegraph-страницы с полным текстом вакансии
  handlers/
    start.py              — /start, регистрация, главное меню
    stacks.py              — /setstacks, /mystacks — выбор направлений
    settings.py            — /notify, /status — уведомления и профиль
    submit_vacancy.py      — кнопка «Разместить вакансию»: FSM-диалог, модерация, публикация
    admin.py               — /stats, пересылка сообщений пользователей админу
    donate.py              — кнопка «❤️ Поддержать»: ссылка на донат-страницу Tribute
  .env                    — секреты (не в git)
  requirements.txt
```

## Принципы реализации

- Фреймворк: aiogram 3.x (async), FSM на встроенном `MemoryStorage` (по умолчанию у `Dispatcher()`)
- Turso-клиент: httpx напрямую к Turso HTTP API (`db.py:execute()`)
- Стеки хранятся как JSON-строка в поле `stacks`
- При /start: если пользователь уже есть в БД — обновляем username/full_name без перезаписи ref_source; если нет — INSERT
- Список допустимых стеков — `ALL_STACKS` в `handlers/stacks.py`
- Приём вакансий: технический фильтр (`vacancy_filter` → при необходимости `vacancy_llm_filter`)
  ОБЯЗАТЕЛЬНО проходит до LLM-форматирования — `vacancy_formatter` сам по себе не отбраковывает
  нетехнические вакансии (нетехническую роль просто помечает category/direction="other")
- Модерация: по умолчанию каждая вакансия уходит админу (`ADMIN_TG_ID`) на подтверждение
  перед записью в `vacancies`; флаг `VACANCY_AUTO_PUBLISH=1` отключает модерацию (запись сразу
  после подтверждения отправителем) — переключатель на будущее, без изменения кода
- Очередь модерации хранится в памяти процесса (`submit_vacancy.py:_pending_moderation`) —
  не переживает перезапуск бота, как и аналогичный механизм в `it-vacancies-base/03-processor/admin_bot.py`

### Интеграция с Tribute (донаты)

Кнопка «❤️ Поддержать» (`handlers/donate.py`) только отдаёт статическую ссылку
`TRIBUTE_DONATE_URL` (`https://t.me/tribute/app?startapp=...`) — сумму, периодичность
(разово/ежемесячно/...) и способ оплаты выбирает сам донатер в интерфейсе Tribute.

Приём вебхуков об оплате, таблица `donations`, проверка подписи и благодарность донору —
в отдельном этапе `03-tribute-webhook/` (Vercel/Node, другой стек и другая инфраструктура).
01-bot НЕ читает и не пишет таблицу `donations`. Подробности — в корневом `CLAUDE.md` и
`03-tribute-webhook/CLAUDE.md`.

## СТРОГИЕ ЗАПРЕТЫ

- НЕ читай файлы из `02-notifier/`
- НЕ реализуй логику рассылки вакансий здесь
- Пиши в таблицу `vacancies` ТОЛЬКО через `db.py:insert_vacancy()`, и только после одобрения
  админом (или сразу — если `VACANCY_AUTO_PUBLISH=1`). НЕ читай `vacancies` для иных целей
- НЕ меняй схему таблицы `users` или `vacancies` без обновления корневого CLAUDE.md

## Переменные окружения (.env)

```
TELEGRAM_BOT_TOKEN=...
TURSO_URL=libsql://...
TURSO_TOKEN=...
ADMIN_TG_ID=...                          # кому пересылаются сообщения и заявки на модерацию вакансий
COMMUNITY_CHAT_ID=...                    # опционально: chat_id закрытого сообщества для проверки членства
NOTIFY_HOUR=9                            # час ежедневного дайджеста (UTC)

# Приём вакансий через «📨 Разместить вакансию»
OPENROUTER_API_KEY=...                   # тот же ключ, что используется в it-vacancies-base
OPENAI_MODEL=openai/gpt-4o
TELEGRAPH_ACCESS_TOKEN=...                # тот же токен, что используется в it-vacancies-base
TELEGRAPH_AUTHOR_NAME=IT Вакансии
VACANCY_AUTO_PUBLISH=0                   # 1 — публиковать без модерации админом

# Донаты через Tribute («❤️ Поддержать»)
TRIBUTE_DONATE_URL=https://t.me/tribute/app?startapp=...   # ссылка на донат-страницу
```
