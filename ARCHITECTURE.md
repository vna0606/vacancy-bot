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
│   │   ├── start.py                — /start: регистрация, главное меню, обработчик "🔒 Закрытое сообщество"
│   │   ├── stacks.py               — /mystacks: просмотр и изменение стека
│   │   ├── settings.py             — /settings: управление уведомлениями
│   │   └── admin.py                — relay: пересылка сообщений пользователей админу, ответ через бота
│   ├── requirements.txt            — aiogram, httpx, apscheduler, python-dotenv
│   ├── .env                        — TELEGRAM_BOT_TOKEN, TURSO_URL, TURSO_TOKEN, NOTIFY_HOUR, NOTIFY_MINUTE, COMMUNITY_CHAT_ID, ADMIN_TG_ID
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
| Boosty | Ссылка на закрытое IT-сообщество "Технари" (inline URL-кнопка) | — (захардкожен COMMUNITY_URL в start.py) |

## Ключевые паттерны
1. **Turso как шина данных**: 01-bot пишет в `users`, 02-notifier читает `users` + `vacancies` (которые пишет it-vacancies-base). Прямой связи между этапами нет — только через Turso.
2. **Дедупликация через sent_notifications**: перед отправкой вакансии notifier проверяет таблицу `sent_notifications(tg_id, vacancy_id)` с UNIQUE constraint — одна вакансия никогда не отправляется пользователю дважды.
3. **Нечёткое сопоставление стека**: сравнение `vacancies.direction` с `users.stacks` через `LOWER() + LIKE` — регистронезависимое, позволяет найти "python" в "Python Backend". Используются расширенные алиасы для маппинга технологий.
4. **Встроенный scheduler в 01-bot**: bot.py запускает APScheduler параллельно с polling. По cron-расписанию `mon-fri hour=NOTIFY_HOUR, minute=NOTIFY_MINUTE` запускает `02-notifier/notifier.py` как subprocess. По умолчанию рассылка настроена на 13:00 UTC (16:00 MSK).
5. **Кнопка сообщества**: в главном меню добавлена persistent-кнопка "🔒 Закрытое сообщество". Обработчик `cmd_community` в `start.py` отвечает описанием и InlineKeyboardButton с URL `https://boosty.to/ulbitv?utm_source=vac_bot`.
6. **Admin relay**: `handlers/admin.py` перехватывает входящие сообщения от пользователей и пересылает их администратору (ADMIN_TG_ID). Ответ администратора через reply в боте пересылается обратно пользователю. Пересылка работает только в обе стороны — не создаёт дублирования с основными обработчиками.

# Ecosystem Map

## Проекты
| Проект | Назначение | Стек | Входящие данные | Исходящие данные |
|--------|-----------|------|----------------|-----------------|
| `it-vacancies-base` | Сбор, фильтрация, обогащение и публикация IT-вакансий | Python (Telethon), OpenAI, SQLite/Turso, Telegraph | Посты из Telegram-каналов | Таблица `vacancies`, посты в Telegram, статьи Telegraph |
| `vacancy-bot` | Персонализированная рассылка вакансий соискателям | Python (aiogram), Turso | Таблица `vacancies` (Turso) | Сообщения в Telegram |
| `outreach-system` | Поиск рекламодателей, контактов и автоматизация рассылок | Python, Telethon, OpenAI, Hunter.io, Turso | Telegram, сайты, Hunter.io | Google Sheets, Notion CRM, Email/TG рассылки |
| `tg-business-bot` | AI-автоответчик для бизнеса с интеграцией в CRM | Python (python-telegram-bot), Gemini CLI | Входящие сообщения в Telegram | Автоответы, медиакит, карточки лидов в Notion CRM |
| `task-distributor` | Транскрибация встреч и управление задач (Legacy/Scripts) | Bash, Python, Deepgram, Claude CLI | Аудио/видео записи встреч | Транскрипты и задачи в Notion / Google Drive |
| `meeting-tasks` | Автоматизированный сбор и трекинг задач из встреч | Python, SQLite | Транскрипты, сессии встреч | Статусы задач, отчеты |
| `notion-pm` | Полный цикл управления проектами (Capture → Detail → Plan → Execute) | Python (aiogram), Groq API + faster-whisper (fallback), Claude/Gemini CLI, Notion API | Голосовые и текстовые сообщения Telegram | Проекты, детальные планы и задачи в Notion |
| `mood-diary` | Дневник настроения с AI-аналитикой | TypeScript, Next.js, Turso, AI API | Записи пользователя (текст/голос) | Статистика, инсайты, графики |
| `agent-teams` | Оркестратор специализированных AI-агентов и навыков | Claude Code, Markdown-агенты, Python/JS Skills | Текстовые задачи, документы, URL | Ресёрч, отчёты, веб-артефакты, Google Sheets |
| `finance-tracker` | Telegram Mini App для управления финансами | React, Telegram Mini App API, CSS | Транзакции, доходы/расходы | Визуализация бюджета, графики |
| `meeting-transcription` | Транскрибация встреч с публикацией в Notion и Google Drive | Python (Flask), Deepgram (full mode) + Groq API + faster-whisper (quick mode), Claude CLI, Notion API, rclone | Аудио/видео файлы (Telegram или incoming/) | .docx транскрипт, саммари в Telegram, страница в Notion, файл в Google Drive |
| `content-brain` | AI-система генерации контента для Telegram-канала из личного дневника | Python, aiogram 3.x, Telethon, Claude CLI, NotebookLM (nlm CLI), Groq API, Turso | mood-diary Turso (read-only), посты @nikbase (Telethon) | Идеи постов в cb_ideas, готовые посты для Telegram-канала |
| `audio-transcriber` | Telegram-бот транскрибации аудио (@assist_nik_bot) + Flask API для meeting-transcription | Python (aiogram), Groq API + faster-whisper (fallback) | Голосовые сообщения Telegram, аудио-файлы через API | Текстовый транскрипт в Telegram |
| `tekhnari-agent` | AI-система анализа сообщества и генерации контента в стиле Тимура | Python, Claude CLI, Deepgram, Telethon, APScheduler, SQLite, Node.js | Сообщения Telegram-чата сообщества, записи встреч, история канала | Еженедельный отчёт (md/docx), идеи контента |
| `weekly-digest` | Ежедневная и еженедельная рассылка контент-плана из Notion в Telegram | Python, Notion API, Telegram Bot API, cron | База данных Notion с контент-планом | Дайджест-сообщения в Telegram |
| `health-monitor` | Ежедневный мониторинг всех автоматизаций (cron + GitHub Actions) | Python, GitHub API, Telegram Bot API | crontab, логи, GitHub Actions runs | Отчёт о состоянии автоматизаций в Telegram |

## Общие интеграции
Сервисы которые используются в нескольких проектах:

| Сервис | Используется в |
|--------|---------------|
| **Turso (libSQL cloud)** | `it-vacancies-base`, `vacancy-bot`, `mood-diary`, `outreach-system`, `content-brain` |
| **Telegram API / Bot API** | `it-vacancies-base`, `vacancy-bot`, `outreach-system`, `tg-business-bot`, `notion-pm`, `finance-tracker`, `content-brain`, `audio-transcriber`, `tekhnari-agent`, `weekly-digest`, `health-monitor` |
| **Telethon (MTProto)** | `it-vacancies-base` (parser), `outreach-system` (parser/sender), `content-brain` (парсинг @nikbase), `tekhnari-agent` (импорт истории) |
| **OpenAI API** | `it-vacancies-base`, `outreach-system` |
| **Notion API** | `outreach-system` (CRM), `notion-pm` (проекты), `tg-business-bot` (CRM), `task-distributor`, `meeting-transcription` (публикация встреч), `weekly-digest` (контент-план) |
| **Google Sheets API** | `outreach-system` (база контактов), `agent-teams` (skill: google-sheets) |
| **Gemini CLI** | `tg-business-bot` (ответы), `notion-pm` (анализ идей) |
| **Claude CLI / Code** | `task-distributor` (саммари), `agent-teams` (основа), `notion-pm` (планирование), `content-brain` (анализ смыслов, генерация постов), `tekhnari-agent` (анализ сообщества, генерация контента) |
| **Groq API (whisper-large-v3)** | `claude-bot`, `audio-transcriber` (@assist_nik_bot), `notion-pm`, `meeting-transcription` (quick mode), `content-brain` (транскрипция голосовых @nikbase) — основной ASR, 1-й приоритет |
| **faster-whisper medium (Finland VPS)** | `claude-bot`, `audio-transcriber`, `notion-pm`, `meeting-transcription` (quick mode) — 2-й приоритет, fallback |
| **Deepgram** | `task-distributor` (ASR), `mood-diary` (голос), `notion-pm` (захват идей), `meeting-transcription` (основной ASR full mode), `tekhnari-agent` (транскрибация записей встреч) |
| **NotebookLM (nlm CLI)** | `content-brain` (семантический поиск по дневнику и каналу) |
| **GitHub API** | `health-monitor` (проверка статуса Actions) |

## Общие переменные окружения
| Переменная | Проекты |
|------------|---------|
| `TURSO_URL` / `TOKEN` | it-vacancies-base, vacancy-bot, outreach-system, mood-diary |
| `TURSO_MOOD_URL` / `TURSO_MOOD_TOKEN` | mood-diary, content-brain (read-only) |
| `TURSO_CONTENT_BRAIN_URL` / `TURSO_CONTENT_BRAIN_TOKEN` | content-brain |
| `TELEGRAM_API_ID` / `HASH` | it-vacancies-base, outreach-system, content-brain (33361321 / 67a7d...) |
| `TELEGRAM_BOT_TOKEN` | it-vacancies-base, vacancy-bot, tg-business-bot, notion-pm, finance-tracker, weekly-digest |
| `NOTION_TOKEN` | outreach-system, task-distributor, notion-pm, tg-business-bot, meeting-transcription, weekly-digest |
| `GROQ_API_KEY` | claude-bot, audio-transcriber, notion-pm, meeting-transcription, content-brain |
| `DEEPGRAM_API_KEY` | task-distributor, meeting-transcription, tekhnari-agent |
| `GITHUB_TOKEN` | health-monitor |

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
                   │  дайджест)      │
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
                                └──────────┬──────────┘
                                           │ готовые идеи постов
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
┌─────────────────────────┐
│    tekhnari-agent       │
│ Collector→Analyst→      │
│ Marketer (Claude CLI)   │
└──────────┬──────────────┘
           │ отчёт md/docx
           ▼
    Еженедельный контент-
    план для Тимура

┌─────────────────────────┐
│    health-monitor       │
│ (crontab + GH Actions   │
│  → Telegram отчёт)      │
└─────────────────────────┘
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
- API_ID и API_HASH для обоих номеров: `33361321` / `67a7d1129883178f4bc0872a56bb5da5` (см. `outreach-system/04-sheets-sender/.env`).
- Если нужна новая авторизация: `python run.py --auth` (или аналог) — запросит SMS-код и создаст `.session` файл.

### Состояние реализации:
- **notion-pm**: Полностью развернуты модули от захвата (02-bot) до исполнения (05-executor). Использует `project_map.py` для синхронизации.
- **agent-teams**: Активная библиотека навыков: `web-artifacts-builder`, `slack-gif-creator`, `frontend-design`, `google-sheets`, `algorithmic-art`, `skill-creator`.
- **finance-tracker**: Создана дизайн-система (Fintrack Design System) и прототип интерфейса на React для Telegram Mini App.
- **it-vacancies-base**: Стабильный цикл парсинга и публикации (01-parser + 03-processor).
- **meeting-tasks**: Модуль для структурированного ведения задач из сессий встреч (collector + runner).
- **meeting-transcription**: Продакшн-сервер транскрибации (Flask, порт 5055). Принимает аудио/видео через Telegram или polling `incoming/`, публикует в Notion и Google Drive. Интегрирован с `meeting-tasks` (mode: tasks).
- **mood-diary**: Стабильная PWA/Telegram версия с глубокой аналитикой в папке `insights`.
- **content-brain**: Полностью развернута трёхэтапная система (01-knowledge-base + 02-analyzer + 03-bot). Индексировано 13 резюме + 670 сообщений дневника + 298 постов @nikbase. NotebookLM подключён (2 ноутбука: архив + fresh). Автообновление NLM по крону настроено. Требует ручного заполнения `strategy.md` и добавления бота в @nikbase как администратора.
- **tekhnari-agent**: Трёхмодульная система (collector + analyst + marketer). Боты запущены в чате сообщества и чате команды. Еженедельный запуск по APScheduler (воскресенье 20:00). Deepgram для транскрибации встреч, Claude CLI для анализа, Node.js для генерации .docx отчётов.
- **weekly-digest**: Четыре cron-скрипта для ежедневной и еженедельной рассылки контент-плана из Notion в Telegram (06:00 UTC ежедневно, 05:50 UTC по понедельникам).
- **health-monitor**: Ежедневный мониторинг в 12:00 МСК. Сканирует crontab, проверяет логи и GitHub Actions, сравнивает с предыдущим состоянием (state.json), отправляет отчёт в Telegram.

## Известные особенности и ограничения
- Шаг синхронизации `04-sync` (it-vacancies-base → Turso) не реализован в репозитории — без него vacancies в Turso не появятся.
- Оба этапа используют один и тот же `TELEGRAM_BOT_TOKEN` — это нормально для aiogram, но нужно согласовывать обработчики.
- `stacks` хранится в `users` как JSON-строка `["Python","Backend"]` — при добавлении/удалении нужен парсинг на стороне бота.
- Использование `HTML` parse mode для форматирования сообщений с вакансиями.
- Фикс `AsyncIOScheduler`: корутина передается напрямую во избежание `RuntimeError: no running event loop`.
- `COMMUNITY_URL` захардкожен в `01-bot/handlers/start.py` как `https://boosty.to/ulbitv?utm_source=vac_bot` — при смене ссылки менять там.
- Admin relay (`handlers/admin.py`) активен для всех входящих сообщений, не обработанных другими handlers. `ADMIN_TG_ID` задаётся в `.env` — без него пересылка молча игнорируется.

## История изменений
- 2026-06-07 — добавлен admin relay (`01-bot/handlers/admin.py`): входящие сообщения пользователей пересылаются администратору (ADMIN_TG_ID), ответ через reply возвращается пользователю. Удалён `01-bot/.env.example`.
- 2026-06-02 — добавлена кнопка "🔒 Закрытое сообщество" в главное меню (`start.py`): persistent ReplyKeyboardButton + обработчик `cmd_community` с InlineKeyboardButton-ссылкой на Boosty (`COMMUNITY_URL`). Ссылка на сообщество также добавлена в `JOIN_COMMUNITY_TEXT` в `stacks.py`.
- 2026-05-17 — удаление специализации "PM" из списка доступных стеков в `01-bot/handlers/stacks.py`, очистка репозитория от `.pyc` файлов.
- 2026-05-10 — поддержка NOTIFY_MINUTE, переход на HTML parse mode, расширенные алиасы стеков, исправление инициализации AsyncIOScheduler.
- 2026-05-04 — первичная документация.
