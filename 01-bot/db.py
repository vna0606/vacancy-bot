import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

TURSO_URL = os.getenv("TURSO_URL", "").replace("libsql://", "https://")
TURSO_TOKEN = os.getenv("TURSO_TOKEN", "")

HEADERS = {
    "Authorization": f"Bearer {TURSO_TOKEN}",
    "Content-Type": "application/json",
}

PIPELINE_URL = f"{TURSO_URL}/v2/pipeline"


def _arg(value):
    if value is None:
        return {"type": "null"}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    return {"type": "text", "value": str(value)}


async def execute(sql: str, args: list = None):
    payload = {
        "requests": [
            {
                "type": "execute",
                "stmt": {
                    "sql": sql,
                    "args": [_arg(a) for a in (args or [])],
                },
            },
            {"type": "close"},
        ]
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(PIPELINE_URL, headers=HEADERS, json=payload)
        resp.raise_for_status()
        data = resp.json()
        result = data["results"][0]
        if result["type"] == "error":
            raise RuntimeError(f"Turso error: {result['error']}")
        return result["response"]["result"]


async def get_user(tg_id: int):
    result = await execute(
        "SELECT tg_id, username, full_name, stacks, notify_enabled, notify_hour FROM users WHERE tg_id = ?",
        [tg_id],
    )
    rows = result.get("rows", [])
    if not rows:
        return None
    row = rows[0]
    cols = [c["name"] for c in result["cols"]]
    user = dict(zip(cols, [v["value"] if v["type"] != "null" else None for v in row]))
    if user.get("stacks"):
        try:
            user["stacks"] = json.loads(user["stacks"])
        except Exception:
            user["stacks"] = []
    else:
        user["stacks"] = []
    return user


async def upsert_user(tg_id: int, username: str, full_name: str, ref_source: str = None):
    await execute(
        """INSERT INTO users (tg_id, username, full_name, stacks, notify_enabled, notify_hour, ref_source)
           VALUES (?, ?, ?, '[]', 1, 9, ?)
           ON CONFLICT(tg_id) DO UPDATE SET
               username = excluded.username,
               full_name = excluded.full_name""",
        [tg_id, username, full_name, ref_source],
    )


async def update_stacks(tg_id: int, stacks: list):
    await execute(
        "UPDATE users SET stacks = ?, stacks_set_at = CURRENT_TIMESTAMP WHERE tg_id = ?",
        [json.dumps(stacks, ensure_ascii=False), tg_id],
    )


async def update_notify(tg_id: int, enabled: int, reason: str = None):
    if reason is not None:
        await execute(
            "UPDATE users SET notify_enabled = ?, disabled_reason = ? WHERE tg_id = ?",
            [enabled, reason, tg_id],
        )
    else:
        await execute(
            "UPDATE users SET notify_enabled = ? WHERE tg_id = ?",
            [enabled, tg_id],
        )


async def update_notify_hour(tg_id: int, hour: int):
    await execute(
        "UPDATE users SET notify_hour = ? WHERE tg_id = ?",
        [hour, tg_id],
    )


async def update_last_seen(tg_id: int):
    await execute(
        "UPDATE users SET last_seen_at = CURRENT_TIMESTAMP WHERE tg_id = ?",
        [tg_id],
    )


async def insert_vacancy(
    title: str, company: str, hr_contact: str, salary: str,
    work_format: str, telegraph_url: str, direction: str, category: str,
    dedup_key: str,
):
    # raw_post_id=0 не существует в raw_posts (FK на эту таблицу) — для вакансий из бота
    # FK-проверку нужно отключить на время INSERT, как и в it-vacancies-base/admin_bot.py.
    # dedup_key — тот же алгоритм, что у it-vacancies-base (vacancy_dedup.py), чтобы автопайплайн
    # видел вакансии, добавленные через бота, при своей проверке на дубликаты.
    args = [title, company, hr_contact, salary, work_format, telegraph_url, direction, category, dedup_key]
    payload = {
        "requests": [
            {"type": "execute", "stmt": {"sql": "PRAGMA foreign_keys = OFF"}},
            {
                "type": "execute",
                "stmt": {
                    "sql": (
                        "INSERT INTO vacancies "
                        "(raw_post_id, title, company_name, recruiter_contact, "
                        "salary, work_format, telegraph_url, direction, category, dedup_key) "
                        "VALUES (0, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                    ),
                    "args": [_arg(a) for a in args],
                },
            },
            {"type": "execute", "stmt": {"sql": "PRAGMA foreign_keys = ON"}},
            {"type": "close"},
        ]
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(PIPELINE_URL, headers=HEADERS, json=payload)
        resp.raise_for_status()
        data = resp.json()
        for result in data["results"]:
            if result["type"] == "error":
                raise RuntimeError(f"Turso error: {result['error']}")


async def find_duplicate_vacancy(dedup_key: str, days: int = 7):
    """Возвращает последнюю вакансию с тем же dedup_key за {days} дней, либо None."""
    result = await execute(
        "SELECT id, title, telegraph_url FROM vacancies "
        "WHERE dedup_key = ? AND created_at >= datetime('now', ?) "
        "ORDER BY id DESC LIMIT 1",
        [dedup_key, f"-{days} days"],
    )
    rows = result.get("rows", [])
    if not rows:
        return None
    cols = [c["name"] for c in result["cols"]]
    return dict(zip(cols, [v["value"] if v["type"] != "null" else None for v in rows[0]]))


async def log_event(tg_id: int, event: str, payload: str = None):
    await execute(
        "INSERT INTO user_events (tg_id, event, payload) VALUES (?, ?, ?)",
        [tg_id, event, payload],
    )


async def log_vacancy_submission_pending(tg_id: int) -> int:
    """Записывает заявку на вакансию со статусом 'pending' и обновляет счётчик в users.
    Возвращает id строки в vacancy_submissions."""
    payload = {
        "requests": [
            {
                "type": "execute",
                "stmt": {
                    "sql": "INSERT INTO vacancy_submissions (tg_id, status) VALUES (?, 'pending')",
                    "args": [_arg(tg_id)],
                },
            },
            {
                "type": "execute",
                "stmt": {"sql": "SELECT last_insert_rowid()"},
            },
            {
                "type": "execute",
                "stmt": {
                    "sql": (
                        "UPDATE users SET "
                        "vacancy_submitted_at = COALESCE(vacancy_submitted_at, CURRENT_TIMESTAMP), "
                        "vacancy_submit_count = vacancy_submit_count + 1 "
                        "WHERE tg_id = ?"
                    ),
                    "args": [_arg(tg_id)],
                },
            },
            {"type": "close"},
        ]
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(PIPELINE_URL, headers=HEADERS, json=payload)
        resp.raise_for_status()
        data = resp.json()
        for result in data["results"]:
            if result["type"] == "error":
                raise RuntimeError(f"Turso error: {result['error']}")
        rowid_result = data["results"][1]["response"]["result"]
        return int(rowid_result["rows"][0][0]["value"])


async def update_vacancy_submission_status(submission_db_id: int, status: str):
    await execute(
        "UPDATE vacancy_submissions SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        [status, submission_db_id],
    )


async def init_analytics_schema():
    for col_sql in [
        "ALTER TABLE users ADD COLUMN last_seen_at TIMESTAMP",
        "ALTER TABLE users ADD COLUMN disabled_reason TEXT",
        "ALTER TABLE users ADD COLUMN stacks_set_at TIMESTAMP",
        "ALTER TABLE users ADD COLUMN ref_source TEXT",
        "ALTER TABLE users ADD COLUMN vacancy_submitted_at TIMESTAMP",
        "ALTER TABLE users ADD COLUMN vacancy_submit_count INTEGER NOT NULL DEFAULT 0",
    ]:
        try:
            await execute(col_sql)
        except Exception:
            pass  # column already exists
    await execute(
        """CREATE TABLE IF NOT EXISTS user_events (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id      INTEGER NOT NULL,
            event      TEXT NOT NULL,
            payload    TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    await execute(
        """CREATE TABLE IF NOT EXISTS vacancy_submissions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id        INTEGER NOT NULL,
            status       TEXT NOT NULL,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    )
