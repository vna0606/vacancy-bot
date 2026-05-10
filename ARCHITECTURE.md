# Vacancy Bot — Telegram-бот для соискателей IT-вакансий

## Назначение
Telegram-бот для соискателей: пользователи регистрируются, указывают стек технологий, и ежедневно получают персонализированную подборку подходящих вакансий из базы it-vacancies-base. Система состоит из двух изолированных этапов, взаимодействующих через Turso cloud.

## Стек
- Язык: Python 3.12
- Основные библиотеки: aiogram 3.7.0 (Telegram Bot framework), httpx (HTTP-клиент для Turso), apscheduler 3.10.4 (планировщик рассылки), python-dotenv
- Runtime / окружение: Linux, два постоянных процесса (01-bot polling + 02-notifier scheduler), Turso как шина данных

## Структура файлов
vacancy-bot/
├── CLAUDE.md                       — архитектурный документ: контракты Turso, схемы таблиц
├── 01-bot/
│   ├── bot.py                      — точка входа: aiogram polling + APScheduler (ежедневный дайджест)
│   ├── db.py                       — работа с Turso: CRUD пользователей (users)
│   ├── handlers/
│   │   ├── start.py                — /start: регистрация пользователя
│   │   ├── stacks.py               — /mystacks: просмотр и изменение стека
│   │   └── settings.py             — /settings: управление уведомлениями
│   ├── requirements.txt            — aiogram, httpx, apscheduler, python-dotenv
│   ├── .env.example                — TELEGRAM_BOT_TOKEN, TURSO_URL, TURSO_TOKEN, NOTIFY_HOUR, NOTIFY_MINUTE
│   ├── CLAUDE.md                   — граница ответственности этапа
│   └── run.sh                      — скрипт запуска
└── 02-notifier/
    ├── notifier.py                 — читает vacancies + users из Turso, отправляет подборки
    ├── sender.py                   — форматирование и отправка сообщений в Telegram (HTML mode)
    ├── db.py                       — запрос вакансий и пользователей, запись sent_notifications
    ├── requirements.txt            — aiogram, httpx, apscheduler, python-dotenv
    ├── .env.example                — TELEGRAM_BOT_TOKEN, TURSO_URL, TURSO_TOKEN, NOTIFY_HOUR, NOTIFY_MINUTE, VACANCIES_LOOKBACK_HOURS
    ├── CLAUDE.md                   — граница ответственности этапа
    └── run.sh                      — скрипт запуска

## Интеграции и внешние сервисы
| Сервис | Для чего используется | Переменная окружения |
|--------|----------------------|---------------------|
| Telegram Bot API | Получение команд, отправка вакансий пользователям | TELEGRAM_BOT_TOKEN |
| Turso (libSQL cloud) | Шина данных: таблицы users, vacancies, sent_notifications | TURSO_URL, TURSO_TOKEN |

## Ключевые паттерны
1. **Turso как шина данных**: 01-bot пишет в `users`, 02-notifier читает `users` + `vacancies` (которые пишет it-vacancies-base). Прямой связи между этапами нет — только через Turso.
2. **Дедупликация через sent_notifications**: перед отправкой вакансии notifier проверяет таблицу `sent_notifications(tg_id, vacancy_id)` с UNIQUE constraint — одна вакансия никогда не отправляется пользователю дважды.
3. **Нечёткое сопоставление стека**: сравнение `vacancies.direction` с `users.stacks` через `LOWER() + LIKE` — регистронезависимое, позволяет найти "python" в "Python Backend". Используются расширенные алиасы для маппинга технологий.
4. **Встроенный scheduler в 01-bot**: bot.py запускает APScheduler параллельно с polling. По cron-расписанию `mon-fri hour=NOTIFY_HOUR, minute=NOTIFY_MINUTE` запускает `02-notifier/notifier.py` как subprocess. По умолчанию рассылка настроена на 13:00 UTC (16:00 MSK).

## Связи с другими проектами
- **it-vacancies-base**: главный поставщик данных. Таблица `vacancies` заполняется it-vacancies-base pipeline и читается этим ботом через Turso. Для синхронизации нужен 04-sync шаг в it-vacancies-base.
- **outreach-system**: смежный проект по работе с IT-каналом, но другая аудитория (рекламодатели vs соискатели).

# Ecosystem Map

## Проекты
| Проект | Назначение | Стек | Входящие данные | Исходящие данные |
|--------|-----------|------|----------------|-----------------|
| `it-vacancies-base` | Сбор, фильтрация, обогащение и публикация IT-вакансий | Python (Telethon), OpenAI, SQLite/Turso, Telegraph | Посты из Telegram-каналов | Таблица `vacancies`, посты в Telegram, статьи Telegraph |
| `vacancy-bot` | Персонализированная рассылка вакансий соискателям | Python (aiogram), Turso | Таблица `vacancies` (Turso) | Сообщения в Telegram |
| `outreach-system` | Поиск рекламодателей, контактов и автоматизация рассылок | Python, Telethon, OpenAI, Hunter.io, Turso | Telegram, сайты, Hunter.io | Google Sheets, Notion CRM, Email/TG рассылки |
| `tg-business-bot` | AI-автоответчик для бизнеса с интеграцией в CRM | Python (python-telegram-bot), Gemini CLI | Входящие сообщения в Telegram | Автоответы, медиакит, карточки лидов в Notion CRM |
| `task-distributor` | Транскрибация встреч и управление задачами | Bash, Python, Deepgram, Claude CLI | Аудио/видео записи встреч | Транскрипты и задачи в Notion / Google Drive |
| `mood-diary` | Дневник настроения с AI-аналитикой | TypeScript, Next.js, Turso, AI API | Записи пользователя (текст/голос) | Статистика, инсайты, графики |
| `agent-teams` | Оркестратор специализированных AI-агентов и навыков | Claude Code, Markdown-агенты, Python/JS Skills | Текстовые задачи, документы, URL | Ресёрч, отчёты, веб-артефакты, Google Sheets |
| `notion-pm` | Полный цикл управления проектами (Capture → Detail → Plan → Execute) | Python (aiogram), faster-whisper, Claude/Gemini CLI, Notion API | Голосовые и текстовые сообщения Telegram | Проекты, детальные планы и задачи в Notion |

## Общие интеграции
Сервисы которые используются в нескольких проектах:

| Сервис | Используется в |
|--------|---------------|
| **Turso (libSQL cloud)** | `it-vacancies-base`, `vacancy-bot`, `mood-diary`, `outreach-system` |
| **Telegram API / Bot API** | `it-vacancies-base`, `vacancy-bot`, `outreach-system`, `tg-business-bot`, `task-distributor`, `notion-pm` |
| **Telethon (MTProto)** | `it-vacancies-base` (parser), `outreach-system` (parser) |
| **OpenAI API** | `it-vacancies-base` (extractor), `outreach-system` (classification) |
| **Notion API** | `outreach-system` (CRM), `task-distributor` (задачи), `notion-pm` (проекты), `tg-business-bot` (CRM) |
| **Google Sheets API** | `outreach-system` (база контактов), `agent-teams` (skill: google-sheets) |
| **Gemini CLI** | `tg-business-bot` (ответы), `notion-pm` (анализ идей) |
| **Claude CLI / Code** | `task-distributor` (саммари), `agent-teams` (основа), `notion-pm` (планирование) |
| **n8n** | `task-distributor`, `outreach-system`, `it-vacancies-base` (автоматизация) |
| **Deepgram / Whisper** | `task-distributor` (ASR), `mood-diary` (голос), `notion-pm` (захват идей) |

## Общие переменные окружения
| Переменная | Проекты |
|------------|---------|
| `TURSO_URL` / `TURSO_AUTH_TOKEN` | it-vacancies-base, vacancy-bot, outreach-system, mood-diary |
| `TELEGRAM_API_ID` / `HASH` | it-vacancies-base, outreach-system |
| `TELEGRAM_BOT_TOKEN` | it-vacancies-base, vacancy-bot, tg-business-bot, notion-pm |
| `OPENAI_API_KEY` | it-vacancies-base, outreach-system |
| `NOTION_TOKEN` | outreach-system, task-distributor, notion-pm, tg-business-bot |

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
                        │ (Bot + Notifier)     │
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
                          ▲ ▲
           ┌──────────────┘ └──────────────┐
           │                               │
┌──────────┴──────────┐         ┌──────────┴──────────┐
│      notion-pm      │         │   task-distributor  │
│ (Idea → Plan → Exec)│         │ (Audio → Summary    │
└─────────────────────┘         │  → Notion/Drive)    │
                                └─────────────────────┘

┌─────────────────────┐         ┌─────────────────────┐
│     agent-teams      │         │     mood-diary       │
│ (Deep Research,     │         │ (Next.js + AI Chat + │
│  Artifacts, Digest) │         │  Turso Analytics)    │
└─────────────────────┘         └─────────────────────┘
```

## Известные особенности и ограничения
- Шаг синхронизации `04-sync` (it-vacancies-base → Turso) не реализован в репозитории — без него vacancies в Turso не появятся.
- Оба этапа используют один и тот же `TELEGRAM_BOT_TOKEN` — это нормально для aiogram, но нужно согласовывать обработчики.
- `stacks` хранится в `users` как JSON-строка `["Python","Backend"]` — при добавлении/удалении нужен парсинг на стороне бота.
- Использование `HTML` parse mode для форматирования сообщений с вакансиями.
- Фикс `AsyncIOScheduler`: корутина передается напрямую во избежание `RuntimeError: no running event loop`.

## История изменений
- 2026-05-10 — поддержка NOTIFY_MINUTE, переход на HTML parse mode, расширенные алиасы стеков, исправление инициализации AsyncIOScheduler.
- 2026-05-04 — первичная документация.
