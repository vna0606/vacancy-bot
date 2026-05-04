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
│   ├── .env.example                — TELEGRAM_BOT_TOKEN, TURSO_URL, TURSO_TOKEN
│   ├── CLAUDE.md                   — граница ответственности этапа
│   └── run.sh                      — скрипт запуска
└── 02-notifier/
    ├── notifier.py                 — читает vacancies + users из Turso, отправляет подборки
    ├── sender.py                   — форматирование и отправка сообщений в Telegram
    ├── db.py                       — запрос вакансий и пользователей, запись sent_notifications
    ├── requirements.txt            — aiogram, httpx, apscheduler, python-dotenv
    ├── .env.example                — TELEGRAM_BOT_TOKEN, TURSO_URL, TURSO_TOKEN, NOTIFY_HOUR, VACANCIES_LOOKBACK_HOURS
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
3. **Нечёткое сопоставление стека**: сравнение `vacancies.direction` с `users.stacks` через `LOWER() + LIKE` — регистронезависимое, позволяет найти "python" в "Python Backend".
4. **Встроенный scheduler в 01-bot**: bot.py запускает APScheduler параллельно с polling. По cron-расписанию `mon-fri hour=NOTIFY_HOUR` запускает `02-notifier/notifier.py` как subprocess — избегает отдельного cron-демона.

## Связи с другими проектами
- **it-vacancies-base**: главный поставщик данных. Таблица `vacancies` заполняется it-vacancies-base pipeline и читается этим ботом через Turso. Для синхронизации нужен 04-sync шаг в it-vacancies-base.
- **outreach-system**: смежный проект по работе с IT-каналом, но другая аудитория (рекламодатели vs соискатели)

## Известные особенности и ограничения
- Шаг синхронизации `04-sync` (it-vacancies-base → Turso) не реализован в репозитории — без него vacancies в Turso не появятся
- Оба этапа используют один и тот же `TELEGRAM_BOT_TOKEN` — это нормально для aiogram, но нужно согласовывать обработчики
- `stacks` хранится в `users` как JSON-строка `["Python","Backend"]` — при добавлении/удалении нужен парсинг на стороне бота
- APScheduler запускает notifier только по будням (mon-fri) — изменить в `bot.py` при необходимости

## История изменений
- 2026-05-04 — первичная документация
