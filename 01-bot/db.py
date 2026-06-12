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


async def log_event(tg_id: int, event: str, payload: str = None):
    await execute(
        "INSERT INTO user_events (tg_id, event, payload) VALUES (?, ?, ?)",
        [tg_id, event, payload],
    )


async def init_analytics_schema():
    for col_sql in [
        "ALTER TABLE users ADD COLUMN last_seen_at TIMESTAMP",
        "ALTER TABLE users ADD COLUMN disabled_reason TEXT",
        "ALTER TABLE users ADD COLUMN stacks_set_at TIMESTAMP",
        "ALTER TABLE users ADD COLUMN ref_source TEXT",
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
