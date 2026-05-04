import os
import json
import httpx
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

TURSO_URL = os.getenv("TURSO_URL", "").replace("libsql://", "https://")
TURSO_TOKEN = os.getenv("TURSO_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {TURSO_TOKEN}", "Content-Type": "application/json"}
PIPELINE_URL = f"{TURSO_URL}/v2/pipeline"


def _arg(value):
    if value is None:
        return {"type": "null"}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    return {"type": "text", "value": str(value)}


async def execute(sql: str, args: list = None):
    payload = {"requests": [
        {"type": "execute", "stmt": {"sql": sql, "args": [_arg(a) for a in (args or [])]}},
        {"type": "close"},
    ]}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(PIPELINE_URL, headers=HEADERS, json=payload)
        resp.raise_for_status()
        data = resp.json()
        result = data["results"][0]
        if result["type"] == "error":
            raise RuntimeError(f"Turso error: {result['error']}")
        return result["response"]["result"]


def _rows_to_dicts(result):
    cols = [c["name"] for c in result["cols"]]
    out = []
    for row in result.get("rows", []):
        d = {}
        for col, cell in zip(cols, row):
            d[col] = None if cell["type"] == "null" else cell["value"]
        out.append(d)
    return out


async def get_active_users():
    result = await execute(
        "SELECT tg_id, full_name, stacks FROM users WHERE notify_enabled = 1"
    )
    users = _rows_to_dicts(result)
    for u in users:
        try:
            u["stacks"] = json.loads(u["stacks"]) if u["stacks"] else []
        except Exception:
            u["stacks"] = []
    return users


async def get_fresh_vacancies(lookback_hours: int):
    since = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).strftime("%Y-%m-%d %H:%M:%S")
    result = await execute(
        "SELECT id, title, formatted_post, company_name, recruiter_contact, "
        "direction, salary, work_format, telegraph_url "
        "FROM vacancies WHERE created_at >= ?",
        [since],
    )
    return _rows_to_dicts(result)


async def get_sent_ids(user_tg_id: int):
    result = await execute(
        "SELECT vacancy_id FROM sent_notifications WHERE user_tg_id = ?",
        [user_tg_id],
    )
    return {row["vacancy_id"] for row in _rows_to_dicts(result)}


async def mark_sent(user_tg_id: int, vacancy_id: int):
    await execute(
        "INSERT OR IGNORE INTO sent_notifications (user_tg_id, vacancy_id) VALUES (?, ?)",
        [user_tg_id, vacancy_id],
    )


async def disable_user(tg_id: int):
    await execute("UPDATE users SET notify_enabled = 0 WHERE tg_id = ?", [tg_id])
