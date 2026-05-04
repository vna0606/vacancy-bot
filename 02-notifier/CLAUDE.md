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

Поле `direction` — строка, сравниваем с элементами массива `users.stacks` через LOWER + LIKE.

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
    tg_id       INTEGER NOT NULL,
    vacancy_id  INTEGER NOT NULL,
    sent_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tg_id, vacancy_id)
);
```

### Telegram: сообщения пользователям

Отправляет `formatted_post` из таблицы vacancies (уже готовый текст),
дополненный заголовком вида "Новые вакансии для тебя (N)".
При ошибке отправки (бот заблокирован) — устанавливает `notify_enabled = 0` для этого пользователя.

## Структура файлов

```
02-notifier/
  notifier.py         — точка входа; можно запускать напрямую (cron) или через APScheduler
  scheduler.py        — настройка APScheduler (если используется, а не чистый cron)
  db/
    turso.py          — клиент Turso, запросы к vacancies / users / sent_notifications
    schema.py         — DDL для sent_notifications
  matcher.py          — логика сопоставления direction ↔ stacks пользователя
  sender.py           — отправка сообщений через aiogram Bot или httpx (Telegram Bot API)
  .env                — секреты (не в git)
  .env.example        — шаблон
  requirements.txt
```

## Принципы реализации

- Запуск: либо `python notifier.py` по cron (проще), либо APScheduler внутри процесса
- Рекомендуется cron-запуск: каждый день в 09:00 UTC (или настраивается через .env)
- Сопоставление direction ↔ stacks: регистронезависимое, нечёткое (содержит подстроку)
  Пример: direction="Python Backend" совпадает со stack="Python"
- Батчинг: если у пользователя > 5 вакансий — отправить несколькими сообщениями по 5
- Rate limiting: пауза 50ms между отправками, чтобы не упереться в лимиты Telegram
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
NOTIFY_HOUR=9          # час отправки (UTC), если используется APScheduler
VACANCIES_LOOKBACK_HOURS=24
```
