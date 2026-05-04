# vacancy-notifier

Telegram-бот для соискателей. Пользователи регистрируются, указывают стек/направление,
и ежедневно получают подборку подходящих вакансий из базы `it-vacancies-base`.

## Архитектура системы

```
[it-vacancies-base pipeline]
        |
        | sync (04-sync шаг — описан ниже, не реализован здесь)
        v
    [Turso cloud]
     vacancies table
        |
        +------------------+
        |                  |
        v                  v
   [01-bot]          [02-notifier]
   users table       читает vacancies + users
   регистрация       ежедневная рассылка
   /start, /mystacks
```

## Этапы

- `01-bot/` — Telegram-бот: регистрация, команды, хранение профилей в Turso
- `02-notifier/` — Планировщик: читает свежие вакансии и users из Turso, рассылает

## Контракты (Turso)

Единая БД Turso используется как шина данных между всеми частями системы.

### Таблица `vacancies` (пишет it-vacancies-base, читает 02-notifier)

```sql
CREATE TABLE IF NOT EXISTS vacancies (
    id                INTEGER PRIMARY KEY,
    raw_post_id       INTEGER,
    title             TEXT,
    formatted_post    TEXT,
    company_name      TEXT,
    recruiter_contact TEXT,
    direction         TEXT,
    salary            TEXT,
    work_format       TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Поле `direction` — ключевое для фильтрации. Примеры значений: Python, Backend, ML, Frontend, DevOps, QA, Android, iOS, Data.

### Таблица `users` (пишет 01-bot, читает 02-notifier)

```sql
CREATE TABLE IF NOT EXISTS users (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id          INTEGER UNIQUE NOT NULL,
    username       TEXT,
    stacks         TEXT NOT NULL DEFAULT '',   -- JSON-массив строк: ["Python","Backend"]
    notify_enabled INTEGER NOT NULL DEFAULT 1, -- 1 = уведомления включены
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

## Правила работы с проектом

- НЕ читай файлы соседнего этапа при работе внутри одного этапа
- Схемы таблиц менять ТОЛЬКО через явное согласование (они — контракт между этапами)
- Turso — единственная точка обмена данными между 01-bot и 02-notifier
- При добавлении полей в `users` — обновить этот CLAUDE.md и CLAUDE.md обоих этапов
