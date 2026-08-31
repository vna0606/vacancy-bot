import os
import json
import sqlite3
import httpx
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

TURSO_URL = os.getenv("TURSO_URL", "").replace("libsql://", "https://")
TURSO_TOKEN = os.getenv("TURSO_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {TURSO_TOKEN}", "Content-Type": "application/json"}
PIPELINE_URL = f"{TURSO_URL}/v2/pipeline"

# ВРЕМЕННЫЙ мост на время блокировки Turso (см. it-vacancies-base/CHANNELS.md).
LOCAL_DB_PATH = os.getenv(
    "LOCAL_DB_PATH",
    "/home/ubuntu/claude-bot/workspace/it-vacancies-base/vacancies.db",
)
_local_conn = None


def _get_local_conn():
    global _local_conn
    if _local_conn is None:
        _local_conn = sqlite3.connect(LOCAL_DB_PATH, check_same_thread=False)
        _local_conn.execute("PRAGMA journal_mode=WAL")
    return _local_conn


def _cell(value):
    if value is None:
        return {"type": "null", "value": None}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        return {"type": "float", "value": str(value)}
    return {"type": "text", "value": str(value)}


def _execute_local(sql: str, args: list = None):
    conn = _get_local_conn()
    cur = conn.execute(sql, args or [])
    if cur.description is not None:
        cols = [{"name": d[0]} for d in cur.description]
        rows = [[_cell(v) for v in row] for row in cur.fetchall()]
    else:
        cols, rows = [], []
        conn.commit()
    return {"cols": cols, "rows": rows}

# TEST_MODE=1 (по умолчанию) — рассылка физически ограничена одним ADMIN_TG_ID на уровне
# SQL-запроса в get_active_users(), чтобы тестовый прогон не мог задеть подписчиков.
TEST_MODE = os.getenv("TEST_MODE", "1") == "1"
ADMIN_TG_ID = int(os.getenv("ADMIN_TG_ID", "0"))

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=15)
    return _client


async def close_client():
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _arg(value):
    if value is None:
        return {"type": "null"}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    return {"type": "text", "value": str(value)}


async def execute(sql: str, args: list = None):
    if not (TURSO_URL and TURSO_TOKEN):
        return _execute_local(sql, args)
    payload = {"requests": [
        {"type": "execute", "stmt": {"sql": sql, "args": [_arg(a) for a in (args or [])]}},
        {"type": "close"},
    ]}
    client = _get_client()
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
    if TEST_MODE:
        result = await execute(
            "SELECT tg_id, full_name, stacks FROM users WHERE notify_enabled = 1 AND tg_id = ?",
            [ADMIN_TG_ID],
        )
    else:
        result = await execute(
            "SELECT tg_id, full_name, stacks FROM users WHERE notify_enabled = 1"
        )
    users = _rows_to_dicts(result)
    for u in users:
        u["tg_id"] = int(u["tg_id"])
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
    vacancies = _rows_to_dicts(result)
    for v in vacancies:
        v["id"] = int(v["id"])
    return vacancies


async def get_sent_map(vacancy_ids: list[int]) -> dict[int, set[int]]:
    """Одним запросом вместо запроса на каждого пользователя: кому что из
    сегодняшних вакансий уже отправлено."""
    if not vacancy_ids:
        return {}
    placeholders = ",".join("?" for _ in vacancy_ids)
    result = await execute(
        f"SELECT user_tg_id, vacancy_id FROM sent_notifications WHERE vacancy_id IN ({placeholders})",
        list(vacancy_ids),
    )
    out: dict[int, set[int]] = {}
    for row in _rows_to_dicts(result):
        out.setdefault(int(row["user_tg_id"]), set()).add(int(row["vacancy_id"]))
    return out


async def mark_sent_bulk(pairs: list[tuple[int, int]]):
    """Одна вставка вместо вставки на каждую отправленную вакансию."""
    if not pairs:
        return
    CHUNK = 200
    for i in range(0, len(pairs), CHUNK):
        chunk = pairs[i:i + CHUNK]
        values_sql = ",".join("(?, ?)" for _ in chunk)
        args = [x for pair in chunk for x in pair]
        await execute(
            f"INSERT OR IGNORE INTO sent_notifications (user_tg_id, vacancy_id) VALUES {values_sql}",
            args,
        )


async def disable_user(tg_id: int, reason: str = "blocked"):
    await execute(
        "UPDATE users SET notify_enabled = 0, disabled_reason = ? WHERE tg_id = ?",
        [reason, tg_id],
    )
