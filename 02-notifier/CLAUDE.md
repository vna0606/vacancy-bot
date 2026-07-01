# 02-notifier — Ежедневная рассылка вакансий

## Зона ответственности

Ежедневный планировщик, который:
1. Читает из Turso всех пользователей с `notify_enabled = 1`
2. Читает вакансии из Turso, добавленные за последние 24 часа
3. Для каждого пользователя фильтрует вакансии по его стекам
4. Отправляет каждому пользователю подборку через Telegram Bot API
5. Фиксирует отправленные уведомления в `sent_notifications` (дедупликация)

Этот этап НЕ занимается регистрацией пользователей и управлением профилями.

## Входные контракты (Turso)

### Таблица `vacancies` (пишет it-vacancies-base)

```sql
-- Читаем только:
SELECT id, title, formatted_post, company_name, recruiter_contact,
       direction, salary, work_format, created_at
FROM vacancies
WHERE created_at >= datetime('now', '-1 day')
```

Поле `direction` — канонический enum (`backend/frontend/fullstack/mobile/qa/devops/data/ml/
security/embedded/other`), одинаковый у обоих писателей (`vacancy_formatter.py` в 01-bot и
it-vacancies-base используют идентичный список). Сравниваем ТОЧНЫМ равенством через
`STACK_TO_DIRECTION` (`sender.py`), а не подстрокой и не по `title` — подстрочный поиск по
`title` ложно матчил, например, "QA Fullstack" вакансии (direction=qa) пользователям со
стеком FullStack.

### Таблица `users` (пишет 01-bot)

```sql
-- Читаем только:
SELECT tg_id, username, stacks
FROM users
WHERE notify_enabled = 1
```

Поле `stacks` — JSON-строка: `["Python","Backend"]`.

## Выходной контракт

### Таблица `sent_notifications` (пишет и читает только этот этап)

```sql
CREATE TABLE IF NOT EXISTS sent_notifications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_tg_id  INTEGER NOT NULL,   -- колонка называется user_tg_id, не tg_id
    vacancy_id  INTEGER NOT NULL,
    sent_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_tg_id, vacancy_id)
);
```

### Telegram: сообщения пользователям

Отправляет `formatted_post` из таблицы vacancies (уже готовый текст),
дополненный заголовком вида "Новые вакансии для тебя (N)".
При ошибке отправки (бот заблокирован) — устанавливает `notify_enabled = 0` для этого пользователя.

## Структура файлов

```
02-notifier/
  notifier.py         — точка входа: python notifier.py --now (разово) или APScheduler-цикл
  db.py               — клиент Turso (httpx, один переиспользуемый AsyncClient),
                         запросы к vacancies / users / sent_notifications
  sender.py           — матчинг direction↔stacks, конкурентная отправка, rate limiting
  .env                — секреты (не в git)
  .env.example        — шаблон
  requirements.txt
```

(Файлов `scheduler.py`, `db/turso.py`, `db/schema.py`, `matcher.py` не существует —
всё в `db.py` и `sender.py`, это исправлено в документе.)

## Принципы реализации

- Запуск: `python notifier.py --now` (разовый прогон) или без флага — APScheduler,
  cron-триггер на `NOTIFY_HOUR:NOTIFY_MINUTE` UTC (сейчас 13:00 UTC = 16:00 МСК)
- Сопоставление direction ↔ stacks: точное равенство через `STACK_TO_DIRECTION` в `sender.py`
  (direction — канонический enum, а не свободный текст) — НЕ substring, НЕ по `title`
- Отправка КОНКУРЕНТНАЯ (`asyncio.gather` + `Semaphore(CONCURRENCY)`), а не по одному
  пользователю последовательно — при 1000+ активных пользователях последовательная отправка
  с sleep(0.3) между каждым сообщением растягивается на часы (был инцидент 2026-07-01:
  прогон не уложился за 6.5 часов). Общая скорость отправки в Telegram ограничена
  `RateLimiter` (`MSG_PER_SEC` в `sender.py`, ~20 msg/сек суммарно на всех получателей,
  с запасом от лимита Telegram ~30 msg/сек в разные чаты) — а не per-user паузой
- `TelegramRetryAfter` (429) обязательно перехватывается и обрабатывается повтором после
  `retry_after` секунд (`_send_with_retry`) — при повышенной скорости отправки это
  реалистичный сценарий, необработанный он уронит весь прогон через `asyncio.gather`
- Ошибка одного пользователя (кроме `TelegramForbiddenError`/`TelegramBadRequest`) не должна
  ронять прогон для остальных — ловится `except Exception` на уровне `process_user`
- Дедупликация — БАТЧЕМ: один запрос `get_sent_map()` на весь прогон вместо запроса на
  каждого пользователя, запись через `mark_sent_bulk()` (одна INSERT-пачка на ~200 пар),
  а не INSERT на каждую отправленную вакансию
- `TEST_MODE=1` (по умолчанию, `.env`) — `get_active_users()` физически ограничивает
  SQL-запрос одним `ADMIN_TG_ID`, остальные пользователи не попадают в выборку. Переключать
  на `TEST_MODE=0` только после ручной проверки тестового прогона на своём аккаунте
- При TelegramForbiddenError (бот заблокирован): UPDATE users SET notify_enabled=0

## СТРОГИЕ ЗАПРЕТЫ

- НЕ читай файлы из `01-bot/`
- НЕ реализуй команды бота или регистрацию пользователей здесь
- НЕ пиши напрямую в таблицу `users` (кроме `notify_enabled = 0` при блокировке)
- НЕ меняй схему таблицы `vacancies` — она принадлежит it-vacancies-base
- НЕ меняй схему таблицы `users` без обновления корневого CLAUDE.md

## Переменные окружения (.env)

```
TELEGRAM_BOT_TOKEN=...
TURSO_URL=libsql://...
TURSO_TOKEN=...
NOTIFY_HOUR=13          # час отправки (UTC = MSK-3), если используется APScheduler
NOTIFY_MINUTE=0
VACANCIES_LOOKBACK_HOURS=24
TEST_MODE=1             # 1 — слать только ADMIN_TG_ID; 0 — слать всем notify_enabled=1
ADMIN_TG_ID=...          # тестовый получатель при TEST_MODE=1
```
