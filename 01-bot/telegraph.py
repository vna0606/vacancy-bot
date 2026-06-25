"""
Создание Telegraph-страницы с полным текстом вакансии.

Async-версия (httpx) it-vacancies-base/03-processor/telegraph.py — портированы только
text_to_telegraph_nodes() и create_telegraph_page(), используемые в этом боте.
"""

import re
import json
import logging

import httpx

logger = logging.getLogger(__name__)

TELEGRAPH_API = "https://api.telegra.ph/createPage"

# Emojis that mark section headers in the template
_HEADER_EMOJIS = re.compile(r"^[🕹🖥]")
_SPECIAL_FIELDS = [
    (re.compile(r"^Компания:\s*", re.IGNORECASE), "Компания:"),
    (re.compile(r"^Формат:\s*", re.IGNORECASE), "Формат:"),
    (re.compile(r"^Уровень ЗП:\s*", re.IGNORECASE), "Уровень ЗП:"),
    (re.compile(r"^Занятость:\s*", re.IGNORECASE), "Занятость:"),
]


def _p(children: list) -> dict:
    return {"tag": "p", "children": children}


def _strong(text: str) -> dict:
    return {"tag": "strong", "children": [text]}


def _h3(text: str) -> dict:
    return {"tag": "h3", "children": [text]}


def _ul(items: list) -> dict:
    return {"tag": "ul", "children": [{"tag": "li", "children": [i]} for i in items]}


def text_to_telegraph_nodes(text: str, title: str = "") -> list:
    """Convert formatted vacancy text to Telegraph node tree."""
    lines = [l.replace("\r", "").strip() for l in text.split("\n")]
    nodes = []
    list_buffer = []

    def flush_list():
        if list_buffer:
            nodes.append(_ul(list(list_buffer)))
            list_buffer.clear()

    for line in lines:
        if not line:
            continue
        if title and line == title:
            continue

        if line.startswith("- "):
            item = re.sub(r"^-+\s*", "", line).strip()
            list_buffer.append(item)
            continue

        if list_buffer:
            flush_list()

        if _HEADER_EMOJIS.match(line):
            nodes.append(_h3(line))
            continue

        matched = False
        for pattern, label in _SPECIAL_FIELDS:
            if pattern.match(line):
                value = pattern.sub("", line).strip()
                nodes.append(_p([_strong(label), " ", value]))
                matched = True
                break
        if matched:
            continue

        if line == "—":
            nodes.append({"tag": "hr"})
            continue

        nodes.append(_p([line]))

    flush_list()
    return nodes


async def create_telegraph_page(
    title: str,
    content_text: str,
    access_token: str,
    author_name: str = "IT Вакансии",
) -> tuple[str | None, str | None]:
    """Create a Telegraph page. Returns (url, None) on success, (None, error_reason) on failure."""
    nodes = text_to_telegraph_nodes(content_text, title)
    if not nodes:
        logger.warning("Telegraph: empty content for title=%r", title)
        return None, "пустой контент вакансии после форматирования"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                TELEGRAPH_API,
                json={
                    "access_token": access_token,
                    "title": title[:256],  # Telegraph title limit
                    "author_name": author_name,
                    "content": json.dumps(nodes),
                },
            )
            data = resp.json()
        if data.get("ok"):
            return data["result"]["url"], None
        logger.error("Telegraph API error: %s", data.get("error"))
        return None, f"Telegraph API error: {data.get('error')}"
    except Exception as e:
        logger.error("Telegraph request failed: %s", e)
        return None, str(e)
