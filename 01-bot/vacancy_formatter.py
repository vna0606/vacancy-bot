"""
LLM-форматирование текста вакансии по шаблону + классификация category/direction.

Портировано из it-vacancies-base/03-processor/formatter.py, адаптировано под AsyncOpenAI.
"""

import os
import json
import re
import logging

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "openai/gpt-4o")

VALID_CATEGORIES = {
    "frontend", "backend", "fullstack", "mobile", "data", "ml_ai",
    "devops", "qa", "product", "design", "security", "analytics",
    "other",
}

VALID_DIRECTIONS = {
    "backend", "frontend", "fullstack", "mobile", "qa", "devops",
    "data", "ml", "security", "embedded", "other",
}

PROMPT_TEMPLATE = """Ты — профессиональный редактор вакансий.
Твоя задача — определить, является ли текст вакансией, и если да — оформить её по шаблону.
Верни ответ строго в формате JSON. Никаких комментариев, пояснений или markdown-обёртки.

Если текст НЕ является вакансией — верни:
{{"is_vacancy": false}}

Если текст является вакансией — верни JSON с пятью полями (все обязательны):
{{
  "is_vacancy": true,
  "category": "одно значение из списка категорий",
  "direction": "одно значение из списка направлений",
  "title": "краткое название должности",
  "content": "оформленный текст вакансии по шаблону"
}}

Допустимые значения category (строго одно из):
- frontend — Frontend, React, Vue, Angular, Next.js, TypeScript/JS разработчик
- backend — Backend, Python, Java, Go, C++, PHP, .NET, Ruby, Node.js разработчик
- fullstack — Fullstack разработчик
- mobile — iOS, Android, Flutter, React Native, Swift, Kotlin
- data — Data Engineer, Data Analyst, BI-аналитик, ETL
- ml_ai — ML Engineer, AI, NLP, CV, MLOps, Data Scientist
- devops — DevOps, SRE, Cloud Engineer, Platform Engineer, Infra
- qa — QA Engineer, Тестировщик, Automation QA, SDET
- product — Product Manager, Product Owner, Scrum Master
- design — UI/UX Designer, Product Designer
- security — InfoSec, AppSec, Cybersecurity, Pentester
- analytics — System Analyst, Business Analyst
- other — всё остальное, включая Engineering Manager, CTO без явного технического домена

Важно: для ролей Tech Lead и Team Lead — определяй категорию по техническому домену, которым они руководят (AI Tech Lead → ml_ai, Infrastructure/DevOps Team Lead → devops, Frontend Team Lead → frontend, Backend Team Lead → backend, Team Lead со стеком frontend+backend или Node.js+React или аналогичным fullstack-стеком → fullstack и т.д.). Если технический домен неясен — other.

Допустимые значения direction (строго одно из):
- backend — Backend, Python, Java, Go, PHP, .NET, Ruby, Node.js разработчик
- frontend — Frontend, React, Vue, Angular, Next.js, TypeScript/JS разработчик
- fullstack — Fullstack разработчик
- mobile — iOS, Android, Flutter, React Native, Swift, Kotlin
- qa — QA Engineer, Тестировщик, Automation QA, SDET
- devops — DevOps, SRE, Cloud Engineer, Platform Engineer, Infra
- data — Data Engineer, Data Analyst, BI-аналитик, ETL
- ml — ML Engineer, AI, NLP, CV, MLOps, Data Scientist
- security — InfoSec, AppSec, Cybersecurity, Pentester
- embedded — Embedded, Firmware, RTOS, C/C++ для железа
- other — всё остальное (Product, Design, Management и т.д.)
Выбери одно значение из списка выше, основываясь на названии роли и тексте вакансии. Если направление не ясно — other.

Шаблон оформления вакансии (соблюдай структуру и отступы):

[Точное название роли/должности из текста]

[Короткая выжимка 2-3 предложения: что за роль, компания, ключевые условия]
Компания: [название компании; если названия нет, но понятен сектор/деятельность — краткое описание до 5 слов; если совсем ничего неизвестно — —]
Формат: [remote / office / hybrid / —]
Уровень ЗП: [цифры или диапазон из текста; если не указано — —]
Занятость: [full-time / part-time / contract / —]

🖥 Формат
[Город или «Удалённая» — из текста; если не указано — —]

🕹 Работодатель
[Название компании и 1-2 предложения о том, чем занимается. Если названия нет, но понятен сектор/деятельность — краткое описание до 5 слов. Если совсем ничего неизвестно — —]

🕹 Список обязанностей:
[Что кандидат будет делать. Каждый пункт на новой строке, начиная с тире —. Если не указано — —]

🕹 Требования к кандидату:
[Технический стек, опыт, навыки. Каждый пункт на новой строке, начиная с тире —. Если не указано — —]

🕹 Примерный уровень ЗП:
[Цифры или диапазон из текста. Если не указано — —]

🕹 Условия работы:
[ТОЛЬКО: график (full-time/part-time), тип контракта, льготы (ДМС, оборудование, отпуск, бонусы). НЕ включать сюда технические требования, стек или обязанности. Если не указано — —]

🕹 Контакты:
[Только @username или t.me/username (конвертировать в @username). Email — не контакт. Если нет TG-контакта — —]

Правила оформления:
— Пустые секции: если данных нет — ставь прочерк —, не пропускай секцию
— Компания без названия: — (краткое описание сектора/деятельности до 5 слов); если совсем ничего — просто —
— Контакты: t.me/username → @username; email (word@domain) — не контакт, в разделе Контакты ставь —
— Списки: каждый пункт на новой строке, начиная с тире —
— Эмодзи: удали все эмодзи из оригинала; оставь только 🖥 и 🕹 из шаблона
— Условия работы: только график/контракт/льготы — не смешивать с обязанностями и требованиями

Исходный текст:
{text}"""


def _parse_json(raw: str) -> dict | None:
    """Parse JSON from LLM response, handling markdown code blocks."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def _validate(result: dict) -> bool:
    """Validate parsed LLM response."""
    if not isinstance(result, dict):
        return False
    if not result.get("is_vacancy"):
        return "is_vacancy" in result
    required = {"is_vacancy", "category", "direction", "title", "content"}
    if not required.issubset(result.keys()):
        return False
    if result["category"] not in VALID_CATEGORIES:
        logger.warning("Unknown category %r, replacing with 'other'", result["category"])
        result["category"] = "other"
    if result["direction"] not in VALID_DIRECTIONS:
        logger.warning("Unknown direction %r, replacing with 'other'", result["direction"])
        result["direction"] = "other"
    return True


async def format_vacancy(text: str) -> tuple[dict | None, str | None]:
    """
    Classify and format a post via LLM.

    Returns (result, error):
        ({"is_vacancy": False}, None)                                                              — not a vacancy
        ({"is_vacancy": True, "category": str, "direction": str, "title": str, "content": str}, None) — vacancy
        (None, error_reason)                                                                       — LLM error or invalid JSON
    """
    client = AsyncOpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
    prompt = PROMPT_TEMPLATE.format(text=text)

    last_error = "модель не вернула валидный JSON"
    for attempt_kwargs in ({}, {"temperature": 0}):
        try:
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                **attempt_kwargs,
            )
            raw = response.choices[0].message.content
            result = _parse_json(raw)
            if result is not None and _validate(result):
                return result, None
            logger.warning("Invalid JSON from LLM: %r", (raw or "")[:200])
            last_error = f"модель вернула невалидный JSON: {(raw or '')[:200]!r}"
        except Exception as e:
            logger.error("LLM request failed: %s", e)
            last_error = str(e)

    return None, last_error
