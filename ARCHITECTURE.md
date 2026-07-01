# Vacancy Bot — Telegram-бот для соискателей IT-вакансий

## Назначение
Telegram-бот для соискателей: пользователи регистрируются, указывают стек технологий, и ежедневно получают персонализированную подборку подходящих вакансий из базы it-vacancies-base. Дополнительно: пользователи могут подавать вакансии через бота (с LLM-фильтрацией и модерацией), поддерживать проект донатами через Tribute.co. Система состоит из трёх изолированных этапов, взаимодействующих через Turso cloud.

## Стек
- Язык: Python 3.12 (01-bot, 02-notifier), Node.js (03-tribute-webhook)
- Основные библиотеки: aiogram 3.7.0 (Telegram Bot framework), httpx (HTTP-клиент для Turso), apscheduler 3.10.4 (планировщик рассылки), python-dotenv
- Runtime / окружение: Linux, два постоянных процесса (01-bot polling + 02-notifier scheduler), Vercel serverless (03-tribute-webhook), Turso как шина данных

## Структура файлов
```
vacancy-bot/
├── CLAUDE.md                       — архитектурный документ: контракты Turso, схемы таблиц
├── apps_script_dashboard.gs        — Google Apps Script дашборд статистики бота
├── 01-bot/
│   ├── bot.py                      — точка входа: aiogram polling + APScheduler (ежедневный дайджест)
│   ├── db.py                       — работа с Turso: CRUD пользователей, вакансий, vacancy_submissions, аналитика; update_community_status()
│   ├── weekly_digest.py            — еженедельный дайджест статистики: активные/отписавшиеся/новые пользователи; логирует результат в stdout
│   ├── announce_nonmembers.py      — разовый анонс для не-членов сообщества со стеком (уведомляет об открытии рассылки)
│   ├── announce_nonmembers_nostack.py — разовый анонс для не-членов без стека (просит выбрать стек перед первой рассылкой)
│   ├── vacancy_filter.py           — rule-based классификация вакансий по направлению и категории
│   ├── vacancy_llm_filter.py       — LLM-классификация неуверенных вакансий (classify_uncertain)
│   ├── vacancy_formatter.py        — форматирование карточки вакансии для Telegram (HTML)
│   ├── vacancy_keywords.py         — словари ключевых слов для направлений и категорий
│   ├── vacancy_dedup.py            — генерация dedup_key для дедупликации вакансий
│   ├── telegraph.py                — публикация вакансий на Telegraph
│   ├── handlers/
│   │   ├── start.py                — /start: регистрация, главное меню, обновление community_member через get_chat_member(); notify_enabled больше НЕ зависит от членства
│   │   ├── stacks.py               — /mystacks: просмотр и изменение стека; после сохранения — разные сообщения членам (COMMUNITY_THANKS_TEXT) и не-членам (JOIN_COMMUNITY_TEXT + кнопка-ссылка)
│   │   ├── settings.py             — /settings: управление уведомлениями
│   │   ├── admin.py                — /stats, relay: пересылка сообщений пользователей админу, ответ через бота, логирование в messages.log
│   │   ├── donate.py               — кнопка поддержки проекта (ссылка на Tribute.co)
│   │   └── submit_vacancy.py       — приём вакансий от пользователей: FSM, LLM-фильтрация, модерация, запись в Turso
│   ├── requirements.txt            — aiogram, httpx, apscheduler, python-dotenv
│   ├── .env                        — TELEGRAM_BOT_TOKEN, TURSO_URL, TURSO_TOKEN, NOTIFY_HOUR, NOTIFY_MINUTE, COMMUNITY_CHAT_ID, ADMIN_TG_ID, VACANCY_AUTO_PUBLISH, OPENAI_API_KEY
│   ├── CLAUDE.md                   — граница ответственности этапа
│   ├── bot.log                     — лог работы бота
│   ├── messages.log                — JSONL-лог входящих сообщений пользователей
│   ├── weekly_digest.log           — лог еженедельных дайджестов
│   └── run.sh                      — скрипт запуска
├── 02-notifier/
│   ├── notifier.py                 — точка входа: python notifier.py --now (разовый) или APScheduler-цикл
│   ├── sender.py                   — матчинг direction↔stacks через STACK_TO_DIRECTION, конкурентная отправка (Semaphore), RateLimiter (~20 msg/сек), батчевая запись sent_notifications
│   ├── db.py                       — клиент Turso (один переиспользуемый httpx.AsyncClient); get_active_users(), get_fresh_vacancies(), get_sent_map(), mark_sent_bulk(), disable_user(); TEST_MODE
│   ├── requirements.txt            — aiogram, httpx, apscheduler, python-dotenv
│   ├── .env.example                — TELEGRAM_BOT_TOKEN, TURSO_URL, TURSO_TOKEN, NOTIFY_HOUR, NOTIFY_MINUTE, VACANCIES_LOOKBACK_HOURS, TEST_MODE, ADMIN_TG_ID
│   ├── CLAUDE.md                   — граница ответственности этапа
│   └── run.sh                      — скрипт запуска
└── 03-tribute-webhook/
    ├── api/
    │   └── webhook.js              — Vercel serverless function: приём вебхуков Tribute.co, запись доната в Turso, отправка благодарности донору в Telegram
    ├── package.json                — Node.js зависимости
    ├── .env.example                — TELEGRAM_BOT_TOKEN, TURSO_URL, TURSO_TOKEN, TRIBUTE_WEBHOOK_SECRET
    ├── .vercel/project.json        — конфигурация деплоя Vercel
    ├── CLAUDE.md                   — граница ответственности этапа
    └── .gitignore
```

## Интеграции и внешние сервисы
| Сервис | Для чего используется | Переменная окружения |
|--------|----------------------|---------------------|
| Telegram Bot API | Получение команд, отправка вакансий пользователям, благодарности донорам | TELEGRAM_BOT_TOKEN |
| Turso (libSQL cloud) | Шина данных: таблицы users, vacancies, sent_notifications, vacancy_submissions, donations | TURSO_URL, TURSO_TOKEN |
| OpenAI API | LLM-фильтрация вакансий при приёме от пользователей (classify_uncertain в vacancy_llm_filter.py) | OPENAI_API_KEY |
| Tribute.co | Приём донатов и подписок; вебхуки обрабатываются в 03-tribute-webhook на Vercel | TRIBUTE_WEBHOOK_SECRET |
| Vercel (Node.js serverless) | Хостинг webhook.js для обработки событий от Tribute.co | — (конфиг в .vercel/project.json) |
| Google Sheets | Дашборд статистики бота (apps_script_dashboard.gs) | — (Google Apps Script, без API-ключа) |
| Boosty | Ссылка на закрытое IT-сообщество "Технари" (inline URL-кнопка) | — (захардкожен COMMUNITY_URL в stacks.py) |

## Схемы Turso (контракт между этапами)

### Таблица `users` (пишет 01-bot, читает 02-notifier)
```sql
CREATE TABLE IF NOT EXISTS users (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id                  INTEGER UNIQUE NOT NULL,
    username               TEXT,
    full_name              TEXT,
    stacks                 TEXT NOT NULL DEFAULT '',   -- JSON-массив: ["Python","Backend"]
    notify_enabled         INTEGER NOT NULL DEFAULT 1, -- НЕ зависит от community_member: рассылка идёт всем
    notify_hour            INTEGER,
    ref_source             TEXT,                       -- payload из /start (например "youtube")
    disabled_reason        TEXT,                       -- 'manual' / 'blocked'
    community_member       INTEGER NOT NULL DEFAULT 0, -- 1 если состоит в COMMUNITY_CHAT_ID; обновляется при /start через get_chat_member(); 02-notifier это поле не читает — зарезервировано под future premium-рассылку
    last_seen_at           TIMESTAMP,
    stacks_set_at          TIMESTAMP,
    vacancy_submitted_at   TIMESTAMP,                  -- когда впервые подал заявку на вакансию
    vacancy_submit_count   INTEGER NOT NULL DEFAULT 0, -- сколько раз подавал заявок
    created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Таблица `vacancy_submissions` (пишет и читает только 01-bot)
```sql
CREATE TABLE IF NOT EXISTS vacancy_submissions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id        INTEGER NOT NULL,
    status       TEXT NOT NULL,   -- 'pending' / 'approved' / 'rejected'
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Таблица `vacancies` (пишет 01-bot после одобрения; пишет it-vacancies-base; читает 02-notifier)
```sql
CREATE TABLE IF NOT EXISTS vacancies (
    id                INTEGER PRIMARY KEY,
    raw_post_id       INTEGER,
    title             TEXT,
    formatted_post    TEXT,
    company_name      TEXT,
    recruiter_contact TEXT,
    direction         TEXT,       -- канонический enum: backend/frontend/fullstack/mobile/qa/devops/data/ml/security/embedded/other
    salary            TEXT,
    work_format       TEXT,
    telegraph_url     TEXT,
    category          TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Таблица `sent_notifications` (пишет и читает только 02-notifier)
```sql
CREATE TABLE IF NOT EXISTS sent_notifications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_tg_id  INTEGER NOT NULL,
    vacancy_id  INTEGER NOT NULL,
    sent_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_tg_id, vacancy_id)
);
```

## Ключевые паттерны
1. **Turso как шина данных**: 01-bot пишет в `users` и `vacancy_submissions`, 02-notifier читает `users` + `vacancies` (которые пишет it-vacancies-base). Прямой связи между этапами нет — только через Turso.
2. **Дедупликация через sent_notifications**: перед отправкой вакансии notifier загружает всю карту `get_sent_map()` одним запросом на прогон, записывает батчами через `mark_sent_bulk()` (~200 пар за раз) — одна вакансия никогда не отправляется пользователю дважды.
3. **Точное сопоставление стека**: сравнение `vacancies.direction` с `users.stacks` через словарь `STACK_TO_DIRECTION` в `02-notifier/sender.py` — точное равенство, а не substring по `title`. `direction` — канонический enum из `vacancy_formatter.py`, идентичный у обоих писателей vacancies. Нечёткий поиск создавал ложные срабатывания (например, "QA Fullstack" → стек FullStack).
4. **Конкурентная отправка с rate limiting**: `02-notifier/sender.py` обрабатывает пользователей параллельно через `asyncio.gather` + `Semaphore(CONCURRENCY=30)`. Общая скорость ограничена `RateLimiter(MSG_PER_SEC=20)` вместо per-user паузы — при 1000+ подписчиков последовательная отправка с sleep не укладывается в разумное время. `TelegramRetryAfter` (429) перехватывается и повторяется.
5. **Рассылка открыта всем**: `02-notifier/db.py` выбирает пользователей только по `notify_enabled=1`, поле `community_member` в выборку не входит. `notify_enabled` в `01-bot/handlers/start.py` больше не меняется при смене статуса членства — только `community_member` обновляется через `update_community_status()`.
6. **community_member** — информационное поле в `users`, обновляется при каждом `/start` через `get_chat_member(COMMUNITY_CHAT_ID)`. Используется только в `01-bot/handlers/stacks.py` (после сохранения стека: члены получают `COMMUNITY_THANKS_TEXT`, не-члены — `JOIN_COMMUNITY_TEXT` + кнопка-ссылка). `02-notifier` это поле не читает.
7. **TEST_MODE в 02-notifier**: `TEST_MODE=1` (по умолчанию в `.env`) физически ограничивает SQL-запрос `get_active_users()` одним `ADMIN_TG_ID`. Переключать на `TEST_MODE=0` только после ручной проверки.
8. **Встроенный scheduler в 01-bot**: bot.py запускает APScheduler параллельно с polling. По cron-расписанию запускает `02-notifier/notifier.py` как subprocess. По умолчанию рассылка настроена на 13:00 UTC (16:00 МСК).
9. **Admin relay с форвардингом и логированием**: `handlers/admin.py` перехватывает все входящие сообщения пользователей (текст, стикеры, документы, медиа). Функция `_log_incoming()` пишет JSONL-запись в `01-bot/messages.log` (поля: ts, tg_id, username, full_name, type, text, caption, sticker_emoji, file_name). Служебные события чата (new_chat_members, left_chat_member и др.) расшифровываются в читаемый текст. Ответ администратора через reply в боте пересылается обратно пользователю.
10. **Приём вакансий от пользователей**: `handlers/submit_vacancy.py` реализует FSM-флоу: текст вакансии → `vacancy_filter.py` → при неопределённости `vacancy_llm_filter.py` → карточка → подтверждение → при `VACANCY_AUTO_PUBLISH=true` сразу в `vacancies`, иначе модерация ADMIN_TG_ID. `vacancy_dedup.py` генерирует `dedup_key`. `telegraph.py` публикует полный текст. Статусы — в `vacancy_submissions` (pending/approved/rejected).
11. **Tribute.co вебхук (03-tribute-webhook)**: Vercel serverless `api/webhook.js` принимает POST от Tribute.co, проверяет подпись (TRIBUTE_WEBHOOK_SECRET), записывает донат в Turso (таблица `donations`), отправляет персональную благодарность донору через Telegram Bot API.

# Ecosystem Map

## Проекты
| Проект | Назначение | Стек | Входящие данные | Исходящие данные |
|--------|-----------|------|----------------|-----------------|
| `it-vacancies-base` | Сбор, фильтрация, обогащение и публикация IT-вакансий | Python (Telethon), OpenAI, SQLite/Turso, Telegraph | Посты из Telegram-каналов | Таблица `vacancies`, посты в Telegram, статьи Telegraph |
| `vacancy-bot` | Персонализированная рассылка вакансий соискателям + приём вакансий + обработка донатов через Tribute.co | Python (aiogram), Turso, Node.js (Vercel) | Таблица `vacancies` (Turso), вебхуки Tribute.co | Сообщения в Telegram, подтверждения оплаты |
| `outreach-system` | Поиск рекламодателей, контактов и автоматизация рассылок | Python, Telethon, OpenAI, Hunter.io, Turso | Telegram, сайты, Hunter.io, IT-ивенты | Google Sheets, Notion CRM, Email/TG рассылки |
| `tg-business-bot` | AI-автоответчик для бизнеса с интеграцией в CRM | Python (python-telegram-bot), Gemini CLI, Turso | Входящие сообщения в Telegram | Автоответы, медиакит, карточки лидов в Notion CRM |
| `task-distributor` | Транскрибация встреч и управление задач (Legacy/Scripts) | Bash, Python, Deepgram, Claude CLI | Аудио/видео записи встреч | Транскрипты и задачи в Notion / Google Drive |
| `meeting-tasks` | Автоматизированный сбор и трекинг задач из встреч | Python, SQLite | Транскрипты, сессии встреч | Статусы задач, отчеты |
| `notion-pm` | Полный цикл управления проектами (Capture → Detail → Plan → Execute) | Python (aiogram), Groq API + faster-whisper (fallback), Claude/Gemini CLI, Notion API | Голосовые и текстовые сообщения Telegram | Проекты, детальные планы и задачи в Notion |
| `mood-diary` | Дневник настроения с AI-аналитикой | TypeScript, Next.js, Turso, AI API | Записи пользователя (текст/голос) | Статистика, инсайты, графики |
| `agent-teams` | Оркестратор специализированных AI-агентов и навыков | Claude Code, Markdown-агенты, Python/JS Skills | Текстовые задачи, документы, URL | Ресёрч, отчёты, веб-артефакты, Google Sheets |
| `finance-tracker` | Telegram Mini App для управления финансами | React, Telegram Mini App API, CSS | Транзакции, доходы/расходы | Визуализация бюджета, графики |
| `meeting-transcription` | Транскрибация встреч с публикацией в Notion и Google Drive | Python (Flask), Deepgram (full mode) + Groq API + faster-whisper (quick mode), Claude CLI, Notion API, rclone | Аудио/видео файлы (Telegram или incoming/) | .docx транскрипт, саммари в Telegram, страница в Notion, файл в Google Drive |
| `content-brain` | AI-система генерации контента для Telegram-канала из личного дневника и YouTube | Python, aiogram 3.x, Telethon, Claude CLI, NotebookLM (nlm CLI), Groq API, Turso | mood-diary Turso (read-only), посты @nikbase (Telethon), YouTube-видео | Идеи постов в cb_ideas, готовые посты для Telegram-канала, Reels-сценарии |
| `audio-transcriber` | Telegram-бот транскрибации аудио (@assist_nik_bot) + Flask API для meeting-transcription | Python (aiogram), Groq API + faster-whisper (fallback) | Голосовые сообщения Telegram, аудио-файлы через API | Текстовый транскрипт в Telegram |
| `tekhnari-agent` | AI-система анализа сообщества и генерации контента в стиле Тимура | Python, Claude CLI, Deepgram, Telethon, APScheduler, SQLite, Node.js | Сообщения Telegram-чата сообщества, записи встреч, история канала | Еженедельный и ежемесячный отчёт (md/docx), идеи контента |
| `technarei-stats` | Сбор и визуализация статистики сообщества Текнари в Google Sheets | Python, Google Sheets API, Google Apps Script | Данные сообщества Текнари | Dashboard в Google Sheets |
| `weekly-digest` | Ежедневная и еженедельная рассылка контент-плана из Notion в Telegram (включая персональный дайджест для Тимура) | Python, Notion API, Telegram Bot API, cron | База данных Notion с контент-планом | Дайджест-сообщения в Telegram |
| `health-monitor` | Ежедневный мониторинг всех автоматизаций (cron + GitHub Actions) | Python, GitHub API, Telegram Bot API | crontab, логи, GitHub Actions runs | Отчёт о состоянии автоматизаций в Telegram |
| `client-content-assistant` | Персональный AI-ассистент для клиентов по созданию контента (онбординг, захват идей, анализ, ревью, синхронизация с Notion) | Python (aiogram), Claude CLI, Groq API (транскрибация), Notion API, SQLite (Turso replica) | Голосовые/текстовые сообщения клиента в Telegram, стратегия клиента (strategy.md) | Идеи и контент в Notion, аналитика и ревью в Telegram |

## Общие интеграции
Сервисы которые используются в нескольких проектах:

| Сервис | Используется в |
|--------|---------------|
| **Turso (libSQL cloud)** | `it-vacancies-base`, `vacancy-bot`, `mood-diary`, `outreach-system`, `content-brain`, `tg-business-bot` (referral replica), `client-content-assistant` |
| **Telegram API / Bot API** | `it-vacancies-base`, `vacancy-bot`, `outreach-system`, `tg-business-bot`, `notion-pm`, `finance-tracker`, `content-brain`, `audio-transcriber`, `tekhnari-agent`, `weekly-digest`, `health-monitor`, `client-content-assistant` |
| **Telethon (MTProto)** | `it-vacancies-base` (parser), `outreach-system` (parser/sender), `content-brain` (парсинг @nikbase), `tekhnari-agent` (импорт истории) |
| **OpenAI API** | `it-vacancies-base`, `outreach-system`, `vacancy-bot` (LLM-фильтрация вакансий) |
| **Notion API** | `outreach-system` (CRM), `notion-pm` (проекты), `tg-business-bot` (CRM), `task-distributor`, `meeting-transcription` (публикация встреч), `weekly-digest` (контент-план), `tekhnari-agent` (контент-календарь), `client-content-assistant` (синхронизация идей/контента) |
| **Google Sheets API** | `outreach-system` (база контактов), `agent-teams` (skill: google-sheets), `technarei-stats` (dashboard) |
| **Google Apps Script** | `vacancy-bot` (apps_script_dashboard.gs), `technarei-stats` (dashboard.gs, members_list.gs) |
| **Gemini CLI** | `tg-business-bot` (ответы), `notion-pm` (анализ идей) |
| **Claude CLI / Code** | `task-distributor` (саммари), `agent-teams` (основа), `notion-pm` (планирование), `content-brain` (анализ смыслов, генерация постов), `tekhnari-agent` (анализ сообщества, генерация контента), `client-content-assistant` (анализ и генерация контента) |
| **Groq API (whisper-large-v3)** | `claude-bot`, `audio-transcriber` (@assist_nik_bot), `notion-pm`, `meeting-transcription` (quick mode), `content-brain` (транскрипция голосовых @nikbase), `client-content-assistant` (транскрибация голосовых) — основной ASR, 1-й приоритет |
| **faster-whisper medium (Finland VPS)** | `claude-bot`, `audio-transcriber`, `notion-pm`, `meeting-transcription` (quick mode) — 2-й приоритет, fallback |
| **Deepgram** | `task-distributor` (ASR), `mood-diary` (голос), `notion-pm` (захват идей), `meeting-transcription` (основной ASR full mode), `tekhnari-agent` (транскрибация записей встреч) |
| **NotebookLM (nlm CLI)** | `content-brain` (семантический поиск по дневнику и каналу) |
| **GitHub API** | `health-monitor` (проверка статуса Actions) |
| **Vercel (Node.js serverless)** | `vacancy-bot` (03-tribute-webhook — обработка донатов Tribute.co) |

## Общие переменные окружения
| Переменная | Проекты |
|------------|---------|
| `TURSO_URL` / `TOKEN` | it-vacancies-base, vacancy-bot, outreach-system, mood-diary, tg-business-bot |
| `TURSO_MOOD_URL` / `TURSO_MOOD_TOKEN` | mood-diary, content-brain (read-only) |
| `TURSO_CONTENT_BRAIN_URL` / `TURSO_CONTENT_BRAIN_TOKEN` | content-brain |
| `TELEGRAM_API_ID` / `HASH` | it-vacancies-base, outreach-system, content-brain (33361321 / 67a7d...) |
| `TELEGRAM_BOT_TOKEN` | it-vacancies-base, vacancy-bot, tg-business-bot, notion-pm, finance-tracker, weekly-digest, client-content-assistant |
| `NOTION_TOKEN` | outreach-system, task-distributor, notion-pm, tg-business-bot, meeting-transcription, weekly-digest, tekhnari-agent, client-content-assistant |
| `GROQ_API_KEY` | claude-bot, audio-transcriber, notion-pm, meeting-transcription, content-brain, client-content-assistant |
| `DEEPGRAM_API_KEY` | task-distributor, meeting-transcription, tekhnari-agent |
| `GITHUB_TOKEN` | health-monitor |
| `OPENAI_API_KEY` | it-vacancies-base, vacancy-bot (LLM-фильтрация вакансий) |

## Связи между проектами

```
                        ┌─────────────────────┐
                        │   it-vacancies-base  │
                        │ (Parser→Filter→Pub)  │
                        └──────────┬──────────┘
                                   │ vacancies → Turso
                                   ▼
                        ┌─────────────────────┐
                        │     vacancy-bot      │
                        │ (Bot + Notifier +    │
                        │  Tribute Webhook)    │
                        └─────────────────────┘

 Входящий запрос (TG)              Поиск лидов
         │                               │
         ▼                               ▼
┌─────────────────────┐         ┌─────────────────────┐
│   tg-business-bot   │         │   outreach-system    │
│  (AI-автоответчик)  │         │ (Parser→Hunter→Send) │
└──────────┬──────────┘         └──────────┬──────────┘
           │ CRM entries                   │ контакты → Google Sheets
           └──────────────┐ ┌──────────────┘ синхронизация → Notion CRM
                          ▼ ▼
                   ┌──────────────┐
                   │  Notion Workspace │
                   │ (Projects/Tasks) │
                   └──────────────┘
                          ▲ ▲ ▲
           ┌──────────────┘ │ └──────────────┐
           │                │                │
┌──────────┴──────────┐     │    ┌───────────┴─────────┐
│      notion-pm      │     │    │   task-distributor  │
│ (Idea → Plan → Exec)│     │    │ (Audio → Summary    │
└─────────────────────┘     │    │  → Notion/Drive)    │
                            │    └─────────────────────┘
                   ┌────────┴────────┐
                   │  weekly-digest  │
                   │ (Notion → TG    │
                   │  дайджест +     │
                   │  Тимур digest)  │
                   └─────────────────┘

┌─────────────────────┐         ┌─────────────────────┐
│     agent-teams      │         │     mood-diary       │
│ (Deep Research,     │         │ (Next.js + AI Chat + │
│  Artifacts, Digest) │         │  Turso Analytics)    │
└─────────────────────┘         └──────────┬──────────┘
                                           │ entries + messages (read-only Turso)
                                           ▼
                                ┌─────────────────────┐
                                │   content-brain      │
                                │ KB→Analyzer→Bot      │
                                │ NotebookLM + Claude  │
                                │ YouTube import       │
                                └──────────┬──────────┘
                                           │ готовые идеи постов / Reels
                                           ▼
                                  Telegram @nikbase
                                  (публикация вручную)

                        ┌─────────────────────┐
                        │   finance-tracker   │
                        │ (Telegram Mini App) │
                        └─────────────────────┘

 Аудио/видео (Telegram или incoming/)
         │
         ▼
┌─────────────────────────┐       ┌─────────────────────┐
│  meeting-transcription  │──────▶│   meeting-tasks     │
│ (Deepgram→Notion→Drive) │       │ (трекинг задач)     │
└──────────┬──────────────┘       └─────────────────────┘
           │ страница встречи
           ▼
    Notion Workspace
    Google Drive

 Чат сообщества (TG) + записи встреч
         │
         ▼
┌─────────────────────────┐       ┌─────────────────────┐
│    tekhnari-agent       │       │  technarei-stats    │
│ Collector→Analyst→      │       │ (статистика →       │
│ Marketer (Claude CLI)   │       │  Google Sheets)     │
└──────────┬──────────────┘       └─────────────────────┘
           │ еженедельный/ежемесячный отчёт md/docx + Notion контент-план
           ▼
    Контент-план для Тимура

┌─────────────────────────┐
│    health-monitor       │
│ (crontab + GH Actions   │
│  → Telegram отчёт)      │
└─────────────────────────┘

 Голос/текст клиента (TG)
         │
         ▼
┌─────────────────────────┐
│  client-content-        │
│  assistant              │
│ Onboard→Capture→        │
│ Analyze→Review→Sync     │
└──────────┬──────────────┘
           │ идеи и контент
           ▼
    Notion (клиентское
    пространство)
```


## Инфраструктура транскрибации голоса

### Трёхуровневый fallback (реализован во всех ботах с голосом)

| Уровень | Сервис | Модель | Качество | Когда используется |
|---------|--------|--------|----------|-------------------|
| 1 (основной) | Groq API | whisper-large-v3 | Отличное | Всегда (если есть ключ и лимит не исчерпан) |
| 2 (запасной) | Finland VPS `2.26.85.234:5000` | faster-whisper medium INT8 | Хорошее | При Groq rate limit или ошибке |
| 3 (аварийный) | Локально на AWS | faster-whisper base/small/tiny INT8 | Среднее | Если Finland недоступен |

### Finland VPS — whisper-service
- **Сервис:** `/opt/whisper-service/app.py` (FastAPI + uvicorn, порт 5000)
- **Systemd:** `whisper-service.service`
- **Lazy load:** модель загружается при первом запросе, выгружается через 5 минут простоя
- **Chunking:** аудио >3 мин разбивается на куски по 180 сек (как в основном боте)
- **RAM в покое:** ~400 MB; при активной транскрипции: ~1.4 GB

### Боты с голосовыми сообщениями — статус

| Бот | Сервис | Fallback схема |
|-----|--------|---------------|
| `claude-bot` (@clacodabot) | `claude-bot.service` | ✅ Groq → Finland → local base |
| `audio-transcriber` (@assist_nik_bot) | `audio-transcriber.service` | ✅ Groq → Finland → local small |
| `notion-pm` | `pm-bot.service` | ✅ Groq → Finland → local tiny |
| `meeting-transcription` (quick mode) | `transcribe-server.service` | ✅ Groq → Finland → local small |
| `meeting-transcription` (full mode) | `transcribe-server.service` | Deepgram (без изменений — нужен диаризатор) |
| `mood-diary` | через `claude-bot` | ✅ Groq → Finland → local base |
| `tekhnari-agent` | разовый скрипт / Deepgram | Deepgram (без fallback — транскрибация встреч) |
| `content-brain` (01-knowledge-base) | разовый скрипт | Groq (без fallback — разовая индексация) |
| `client-content-assistant` | отдельный сервис | Groq (основной ASR для голосовых сообщений клиента) |

**Связь audio-transcriber и meeting-transcription:**
Оба используют токен @assist_nik_bot (`8380755935`). `audio-transcriber` — aiogram polling, принимает сообщения от пользователя. `transcribe-server` — Flask API на порту 5055, принимает файлы через API/incoming/ и отправляет результаты через тот же токен.

## Telegram-аккаунты (MTProto сессии)

Авторизованные личные аккаунты Telegram (Telethon). Используются для парсинга каналов и рассылок. Файлы сессий хранятся локально — повторная авторизация не нужна.

| Аккаунт | Телефон | Файл сессии | Используется в |
|---------|---------|-------------|----------------|
| Основной (парсинг/рассылка) | `+79111068325` | `outreach-system/01-parser/telegram_session.session` | Парсинг Telegram-каналов (01-parser) |
| Основной (парсинг/рассылка) | `+79111068325` | `outreach-system/03-sender/telegram_session.session` | Outreach-рассылка (03-sender) |
| Основной (парсинг/рассылка) | `+79111068325` | `it-vacancies-base/01-parser/telegram_session.session` | Парсинг вакансий (it-vacancies-base) |
| Кампейн (Точка Нетворк / content-brain) | `+79177386362` | `outreach-system/04-sheets-sender/campaign.session` | Рассылка по базе из Google Sheets (04-sheets-sender), парсинг @nikbase (content-brain) |
| content-brain (копия кампейн) | `+79177386362` | `content-brain/01-knowledge-base/telegram_session.session` | Парсинг @nikbase |
| tekhnari-agent (импорт истории) | — | `tekhnari-agent/data/tekhnari_history.session` | Однократный импорт истории Telegram-чата сообщества |

**Важно при создании нового проекта с Telethon:**
- Для номера `+79111068325` — можно скопировать `outreach-system/03-sender/telegram_session.session` рядом с новым скриптом (telethon работает с путём к файлу без расширения).
- Для номера `+79177386362` — брать `outreach-system/04-sheets-sender/campaign.session`.
- API_ID и API_HASH для обоих номеров: см. `outreach-system/04-sheets-sender/.env` (в репозиторий не коммитится).
- Если нужна новая авторизация: `python run.py --auth` (или аналог) — запросит SMS-код и создаст `.session` файл.

### Состояние реализации:
- **notion-pm**: Полностью развернуты модули от захвата (02-bot) до исполнения (05-executor). Использует `project_map.py` для синхронизации.
- **agent-teams**: Активная библиотека навыков: `web-artifacts-builder`, `slack-gif-creator`, `frontend-design`, `google-sheets`, `algorithmic-art`, `skill-creator`.
- **finance-tracker**: Создана дизайн-система (Fintrack Design System) и прототип интерфейса на React для Telegram Mini App.
- **it-vacancies-base**: Стабильный цикл парсинга и публикации (01-parser + 03-processor).
- **meeting-tasks**: Модуль для структурированного ведения задач из сессий встреч (collector + runner).
- **meeting-transcription**: Продакшн-сервер транскрибации (Flask, порт 5055). Принимает аудио/видео через Telegram или polling `incoming/`, публикует в Notion и Google Drive. Интегрирован с `meeting-tasks` (mode: tasks). Реализовано улучшенное извлечение задач (`improved_extraction`).
- **mood-diary**: Стабильная PWA/Telegram версия с глубокой аналитикой в папке `insights`.
- **content-brain**: Полностью развернута трёхэтапная система (01-knowledge-base + 02-analyzer + 03-bot). Индексировано 13 резюме + 670 сообщений дневника + 298 постов @nikbase. NotebookLM подключён (2 ноутбука: архив + fresh). Добавлен импорт YouTube-видео (`scripts/youtube_import.py`) и генерация Reels-сценариев (`prompts_reels.py`). Автообновление NLM по крону настроено.
- **tekhnari-agent**: Трёхмодульная система (collector + analyst + marketer). Боты запущены в чате сообщества и чате команды. Еженедельный запуск по APScheduler (воскресенье 20:00), ежемесячные отчёты (`marketer/monthly_report.py`). Deepgram для транскрибации встреч, Claude CLI для анализа, Node.js для генерации .docx отчётов. Контент-план публикуется в Notion.
- **technarei-stats**: Сбор статистики сообщества Текнари с выгрузкой в Google Sheets (03-sheets). Google Apps Script dashboard (`dashboard.gs`, `members_list.gs`) для визуализации и списка участников.
- **weekly-digest**: Четыре cron-скрипта для ежедневной и еженедельной рассылки контент-плана из Notion в Telegram (06:00 UTC ежедневно, 05:50 UTC по понедельникам). Включает персональный дайджест для Тимура (`timur_daily.py`, `timur_weekly.py`).
- **health-monitor**: Ежедневный мониторинг в 12:00 МСК. Сканирует crontab, проверяет логи и GitHub Actions, сравнивает с предыдущим состоянием (state.json), отправляет отчёт в Telegram.
- **vacancy-bot**: Три модуля: 01-bot (aiogram, Turso, LLM-фильтрация вакансий, приём вакансий, разовые скрипты анонса), 02-notifier (ежедневная рассылка всем notify_enabled=1 независимо от community_member, конкурентная отправка), 03-tribute-webhook (Vercel serverless Node.js — обработка вебхуков от Tribute.co).
- **tg-business-bot**: AI-автоответчик с Turso replica (referral_replica.db) для хранения реферальной базы. История диалогов сохраняется локально в JSON-файлах.
- **client-content-assistant**: Персональный AI-ассистент для клиентов (первый клиент — Тимур). Модули: онбординг, захват идей (текст/голос), анализ контента, ревью, синхронизация с персональным Notion-пространством клиента. Конфигурация клиентов хранится в `clients/<name>/notion_config.json` и `strategy.md`. Использует Turso replica для локального хранения сессий и истории.

## Известные особенности и ограничения
- Шаг синхронизации `04-sync` (it-vacancies-base → Turso) не реализован в репозитории — без него vacancies в Turso не появятся.
- Оба этапа 01-bot и 02-notifier используют один и тот же `TELEGRAM_BOT_TOKEN` — это нормально для aiogram, но нужно согласовывать обработчики.
- `stacks` хранится в `users` как JSON-строка `["Python","Backend"]` — при добавлении/удалении нужен парсинг на стороне бота.
- Использование `HTML` parse mode для форматирования сообщений с вакансиями.
- Фикс `AsyncIOScheduler`: корутина передается напрямую во избежание `RuntimeError: no running event loop`.
- `COMMUNITY_URL` захардкожен в `01-bot/handlers/stacks.py` как `https://boosty.to/ulbitv?utm_source=vac_bot` — при смене ссылки менять там. (Ранее был в `start.py` — перенесён в `stacks.py` при рефакторинге логики community_member.)
- Admin relay (`handlers/admin.py`) активен для всех входящих сообщений, не обработанных другими handlers. Форвардит оригинальное сообщение через `bot.forward_message()` — сохраняет медиа, стикеры, документы. Служебные события чата расшифровываются в текстовое описание и отправляются напрямую. Все входящие логируются в `01-bot/messages.log` (JSONL). `ADMIN_TG_ID` задаётся в `.env` — без него пересылка и логирование молча пропускаются.
- `/stats` доступна только пользователю с `ADMIN_TG_ID`. Данные берутся из таблицы `users` в Turso — агрегируются прямо в запросе.
- При `VACANCY_AUTO_PUBLISH=false` вакансии от пользователей уходят на модерацию к ADMIN_TG_ID: inline-кнопки "Одобрить" / "Отклонить" прямо в сообщении. Статус модерации отражается в `vacancy_submissions.status`.
- `vacancy_submitted_at` и `vacancy_submit_count` в `users` — денормализованные агрегаты из `vacancy_submissions` для быстрой фильтрации пользователей без JOIN.
- `02-notifier/db.py` включает `TEST_MODE` (по умолчанию `1`): при включённом режиме `get_active_users()` возвращает только `ADMIN_TG_ID` — реальные подписчики не получают рассылку. Устанавливать `TEST_MODE=0` только после ручной проверки.
- `sent_notifications` в схеме CLAUDE.md использует колонку `user_tg_id` (а не `tg_id`) — при изменении схемы или запросах использовать точное имя.

## История изменений
- 2026-07-01 — рассылка открыта всем пользователям: `notify_enabled` в `start.py` больше не меняется при смене статуса членства; добавлена колонка `community_member INTEGER DEFAULT 0` в `users` (обновляется при /start через `update_community_status()` в `db.py`); `02-notifier` не читает `community_member`; `handlers/stacks.py` после сохранения стека показывает разные сообщения в зависимости от `community_member` (члены — `COMMUNITY_THANKS_TEXT`, не-члены — `JOIN_COMMUNITY_TEXT` + кнопка-ссылка); исправлено сопоставление direction↔stack в `02-notifier/sender.py` — точное равенство через `STACK_TO_DIRECTION` вместо substring по title; переработана конкурентная отправка в `sender.py` (asyncio.gather + Semaphore + RateLimiter вместо последовательной); добавлены разовые скрипты анонса `announce_nonmembers.py` и `announce_nonmembers_nostack.py`.
- 2026-06-28 — приём вакансий от пользователей с трекингом статусов: новые файлы `vacancy_filter.py`, `vacancy_llm_filter.py`, `vacancy_formatter.py`, `vacancy_keywords.py`, `vacancy_dedup.py`, `telegraph.py`, `handlers/submit_vacancy.py`, `handlers/donate.py`; новая таблица `vacancy_submissions` (pending/approved/rejected); новые колонки `vacancy_submitted_at` и `vacancy_submit_count` в `users`; новые функции `log_vacancy_submission_pending()` и `update_vacancy_submission_status()` в `db.py`. Добавлен этап `03-tribute-webhook` (Vercel serverless Node.js): приём донатов от Tribute.co, запись в Turso, отправка благодарности донору.
- 2026-06-21 — мелкие улучшения надёжности: `weekly_digest.py` логирует результат отправки в stdout (`[UTC] sent: total=, active=, new_users=`); `handlers/admin.py` расшифровывает служебные события чата (new_chat_members, left_chat_member и др.) в текстовое описание вместо пустого форварда.
- 2026-06-14 — статистика и аналитика бота: команда `/stats` в `admin.py` (воронка, источники трафика, причины отключений), `weekly_digest.py` для еженедельного дайджеста метрик, `apps_script_dashboard.gs` для Google Sheets дашборда. Admin relay переведён на `bot.forward_message()` (поддержка нетекстовых сообщений) и логирование всех входящих в `01-bot/messages.log` (JSONL) через `_log_incoming()`.
- 2026-06-07 — добавлен admin relay (`01-bot/handlers/admin.py`): входящие сообщения пользователей пересылаются администратору (ADMIN_TG_ID), ответ через reply возвращается пользователю. Удалён `01-bot/.env.example`.
- 2026-06-02 — добавлена кнопка "🔒 Закрытое сообщество" в главное меню (`start.py`): persistent ReplyKeyboardButton + обработчик `cmd_community` с InlineKeyboardButton-ссылкой на Boosty (`COMMUNITY_URL`). Ссылка на сообщество также добавлена в `JOIN_COMMUNITY_TEXT` в `stacks.py`.
- 2026-05-17 — удаление специализации "PM" из списка доступных стеков в `01-bot/handlers/stacks.py`, очистка репозитория от `.pyc` файлов.
- 2026-05-10 — поддержка NOTIFY_MINUTE, переход на HTML parse mode, расширенные алиасы стеков, исправление инициализации AsyncIOScheduler.
- 2026-05-04 — первичная документация.
