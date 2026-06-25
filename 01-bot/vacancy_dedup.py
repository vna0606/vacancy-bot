"""
Дедуп-ключ для повторных вакансий — портировано из
it-vacancies-base/03-processor/db_processor.py (_compute_dedup_key, _extract_tg_handle),
чтобы вакансии, присланные через бота, и вакансии автопайплайна дедупились по одной схеме.
"""

import re
import hashlib

_HANDLE_RE = re.compile(r'@([a-z0-9_]{3,})', re.IGNORECASE)
_TG_LINK_RE = re.compile(r't\.me/([a-z0-9_]{3,})', re.IGNORECASE)


def _extract_tg_handle(contact: str) -> str:
    """Extract the first @handle or t.me/handle from a contact string, ignoring emails."""
    no_emails = re.sub(r'\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b', '', contact or '', flags=re.IGNORECASE)
    m = _HANDLE_RE.search(no_emails)
    if m:
        return m.group(1).lower()
    m = _TG_LINK_RE.search(no_emails)
    if m:
        return m.group(1).lower()
    return ""


def compute_dedup_key(company_name: str, recruiter_contact: str, title: str) -> str:
    """
    Fingerprint for formatted-vacancy dedup.
    Primary anchor = @handle extracted from contact (stable across slight LLM rephrasing).
    Fallback = normalized company name when no handle present.
    Secondary = first 5 normalized words of title.
    """
    def norm(s: str) -> str:
        s = (s or "").lower()
        s = re.sub(r'[^\w\s]', '', s)
        return re.sub(r'\s+', ' ', s).strip()

    handle = _extract_tg_handle(recruiter_contact)
    company = norm(company_name)
    title_words = " ".join(norm(title).split()[:5])

    anchor = handle if handle else company
    raw = f"{anchor}|{title_words}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]
