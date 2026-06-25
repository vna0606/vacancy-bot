# vacancy-notifier

Telegram-бот для соискателей. Пользователи регистрируются, указывают стек/направление,
и ежедневно получают подборку подходящих вакансий из базы `it-vacancies-base`.

## Архитектура системы

```
[it-vacancies-base pipeline]              [01-bot: «Разместить вакансию»]
        |                                  (фильтр + LLM-форматирование +
        | sync (04-sync шаг,               модерация админом)
        |  не реализован здесь)                    |
        v                                          v
              [Turso cloud] — vacancies table
                          |
        +-----------------+------------------+
        |                                    |
        v                                    v
   [01-bot]                            [02-notifier]
   users table, vacancies (запись      читает vacancies + users
   после одобрения)                    ежедневная рассылка
   регистрация /start, /mystacks
```

`vacancies` теперь пишут ДВА независимых процесса: автопайплайн `it-vacancies-base` и `01-bot`
(после модерации админом). Любое изменение схемы `vacancies` нужно согласовывать с обеих сторон.

## Этапы

- `01-bot/` — Telegram-бот: регистрация, команды, хранение профилей в Turso; приём вакансий от
  пользователей (фильтрация, LLM-форматирование, модерация, запись в `vacancies`); кнопка
  «❤️ Поддержать» отдаёт ссылку на донат-страницу Tribute
- `02-notifier/` — Планировщик: читает свежие вакансии и users из Turso, рассылает
- `03-tribute-webhook/` — Vercel/Node-функция: принимает вебхуки Tribute о донатах, пишет в
  `donations`, благодарит донора в Telegram. Отдельный стек (Node, не Python) и отдельная
  инфраструктура (Vercel, не AWS-сервер) — именно поэтому отдельный этап, а не часть `01-bot/`

## Контракты (Turso)

Единая БД Turso используется как шина данных между всеми частями системы.

### Таблица `vacancies` (пишут it-vacancies-base И 01-bot, читает 02-notifier)

```sql
CREATE TABLE IF NOT EXISTS vacancies (
    id                INTEGER PRIMARY KEY,
    raw_post_id       INTEGER,        -- 0 для вакансий, пришедших через 01-bot
    title             TEXT,
    formatted_post    TEXT,           -- заполняет только it-vacancies-base; 01-bot не пишет это поле
    company_name      TEXT,
    recruiter_contact TEXT,
    direction         TEXT,           -- ключевое поле для фильтрации по stacks пользователя
    salary            TEXT,
    work_format       TEXT,
    telegraph_url     TEXT,           -- ссылка на полный текст вакансии (Telegraph); читает 02-notifier
    category          TEXT,           -- более широкая классификация, чем direction (словарь значений — в vacancy_formatter.py)
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Поле `direction` — ключевое для фильтрации. Примеры значений: Python, Backend, ML, Frontend, DevOps, QA, Android, iOS, Data.
Поля `telegraph_url`/`category` фактически используются обоими писателями и читаются
`02-notifier`, хотя раньше не были описаны в этом документе — не убирать при рефакторинге.

### Таблица `users` (пишет 01-bot, читает 02-notifier)

```sql
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id           INTEGER UNIQUE NOT NULL,
    username        TEXT,
    full_name       TEXT,
    stacks          TEXT NOT NULL DEFAULT '',   -- JSON-массив строк: ["Python","Backend"]
    notify_enabled  INTEGER NOT NULL DEFAULT 1, -- 1 = уведомления включены
    notify_hour     INTEGER,
    ref_source      TEXT,                        -- payload из /start
    disabled_reason TEXT,                         -- 'manual' / 'blocked' / 'non_member'
    last_seen_at    TIMESTAMP,
    stacks_set_at   TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Поле `stacks` хранится как JSON-строка: `["Python", "Backend"]`.
Сопоставление с `vacancies.direction` — регистронезависимое, нечёткое (LOWER + LIKE).

### Таблица `sent_notifications` (пишет 02-notifier, читает 02-notifier)

```sql
CREATE TABLE IF NOT EXISTS sent_notifications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id       INTEGER NOT NULL,
    vacancy_id  INTEGER NOT NULL,
    sent_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tg_id, vacancy_id)
);
```

Служит для дедупликации: одна вакансия не отправляется пользователю дважды.

### Таблица `donations` (пишет и читает только `03-tribute-webhook`)

```sql
CREATE TABLE IF NOT EXISTS donations (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type           TEXT NOT NULL,    -- new_donation / recurrent_donation / cancelled_donation
    donation_request_id  INTEGER,
    donation_name        TEXT,
    telegram_user_id     INTEGER,          -- NULL если донат анонимный
    telegram_username    TEXT,
    amount                INTEGER,          -- в минимальных единицах валюты (копейки/центы)
    currency              TEXT,
    period                TEXT,             -- once / monthly / quarterly / yearly
    anonymously           INTEGER,
    message               TEXT,
    webhook_created_at    TEXT,             -- created_at из конверта вебхука Tribute (дедуп повторной доставки)
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_type, donation_request_id, telegram_user_id, amount, period, webhook_created_at)
);
```

`01-bot` не читает и не пишет эту таблицу — только отдаёт ссылку на донат-страницу.
Источник данных — вебхуки Tribute (`new_donation`, `recurrent_donation`, `cancelled_donation`),
подпись `trbt-signature` (HMAC-SHA256) проверяется в `03-tribute-webhook/api/webhook.js`.

## Связь с it-vacancies-base (sync-шаг)

В проекте `it-vacancies-base` нужно добавить шаг `04-sync/` (или скрипт в корне),
который запускается ПОСЛЕ завершения 03-processor и выполняет:

1. Читает из локальной `vacancies.db` записи из таблицы `vacancies` за последние 24 часа
2. Делает upsert в Turso (по полю `id`)
3. Логирует количество синхронизированных записей

Этот шаг НЕ является частью vacancy-notifier. Описание — только для справки.
Зависимости для sync-шага: `libsql-client`, `python-dotenv`.
Переменные окружения: `TURSO_URL`, `TURSO_TOKEN`, `LOCAL_DB_PATH`.

## Переменные окружения

Все секреты хранятся в `.env` файле каждого этапа (не в корне проекта).
Шаблон — `.env.example` в каждой подпапке.

Исключение — `03-tribute-webhook/`: это Vercel-функция, секреты там настраиваются как
Environment Variables проекта на Vercel (`vercel env add`), а не через `.env` на сервере;
`.env.example` в этой папке — только справочный список нужных переменных.

## Правила работы с проектом

- НЕ читай файлы соседнего этапа при работе внутри одного этапа
- Схемы таблиц менять ТОЛЬКО через явное согласование (они — контракт между этапами)
- Turso — единственная точка обмена данными между 01-bot и 02-notifier
- При добавлении полей в `users` — обновить этот CLAUDE.md и CLAUDE.md обоих этапов
- При изменении схемы `vacancies` — согласовать с it-vacancies-base (туда тоже пишут), не только
  с 02-notifier; теперь это таблица с двумя независимыми писателями
