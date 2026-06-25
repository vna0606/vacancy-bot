"""
LLM-проверка технической релевантности вакансии (только для "uncertain" из vacancy_filter).

Портировано из it-vacancies-base/02-filter/llm_filter.py, адаптировано под один текст
(вместо батча) и под AsyncOpenAI.
"""

import os
import json
import logging

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "openai/gpt-4o")

_PROMPT = (
    "Ты — фильтр IT-вакансий. Определи, является ли этот пост объявлением о вакансии "
    "на техническую IT-роль.\n\n"
    "РЕЛЕВАНТНЫЕ роли (relevant):\n"
    "- Разработчик/Developer (backend, frontend, fullstack, mobile, embedded)\n"
    "- QA / тестировщик\n"
    "- DevOps / SRE / инфраструктура\n"
    "- Аналитик данных / Data Scientist / ML Engineer\n"
    "- Системный архитектор / Tech Lead\n"
    "- DBA / Database Administrator\n"
    "- Технический Product Manager (с явным техническим стеком)\n\n"
    "НЕРЕЛЕВАНТНЫЕ роли (irrelevant):\n"
    "- Менеджеры без технического стека (Project Manager, CRM Manager, Delivery Manager)\n"
    "- Дизайнеры (графические, UX/UI без кода, арт-директора, 3D-художники)\n"
    "- Продюсеры, контент-менеджеры, маркетологи\n"
    "- HR, рекрутеры\n"
    "- Юристы, финансисты, бухгалтеры\n"
    "- Административные роли (Office Manager, Travel Manager, Visa Manager)\n\n"
    "Если роль описана расплывчато и непонятно — отмечай как irrelevant.\n\n"
    'Ответь строго в формате JSON: {{"label": "relevant"}} или {{"label": "irrelevant"}}.\n\n'
    "Пост:\n{text}"
)


async def classify_uncertain(text: str) -> str:
    """
    Returns "relevant" or "irrelevant". On any LLM/parsing error defaults to "irrelevant"
    (как и в batch-версии: отсутствие ответа от LLM трактуется как отказ, не как пропуск).
    """
    client = AsyncOpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": _PROMPT.format(text=text)}],
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        label = json.loads(raw).get("label")
        return label if label in ("relevant", "irrelevant") else "irrelevant"
    except Exception as e:
        logger.error("vacancy_llm_filter failed, defaulting to irrelevant: %s", e)
        return "irrelevant"
