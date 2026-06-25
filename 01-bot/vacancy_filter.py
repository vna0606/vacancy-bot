"""
Быстрый regex-фильтр технических IT-вакансий (без сети).

Портировано из it-vacancies-base/02-filter/rule_filter.py.
classify() возвращает "relevant" / "irrelevant" / "uncertain" — uncertain
уходит на дополнительную проверку через vacancy_llm_filter.
"""

import re

from vacancy_keywords import (
    SPECIAL_CHAR_KEYWORDS, SPECIFIC_RE, GENERAL_RE, normalize,
)

# External http links (not t.me) are a weak signal of an ad.
# Not immediately irrelevant (a vacancy can have an apply link),
# but goes to uncertain so LLM can decide.
_EXTERNAL_URL_RE = re.compile(r"https?://(?!t\.me)[^\s)>\]]+", re.IGNORECASE)

# t.me link as a Telegram contact signal
_TG_LINK_RE = re.compile(r"t\.me/[a-z0-9_]{3,}", re.IGNORECASE)

# Phrases indicating "reply in DM" (no explicit handle needed)
_REPLY_IN_DM_RE = re.compile(
    r"в\s+личку|в\s+лс\b|в\s+direct|в\s+директ|в\s+дм\b"
    r"|откликнуться\s+в\s+лич|писать\s+в\s+лич|напиш\w*\s+в\s+лич",
    re.IGNORECASE,
)

# --- Relevant patterns ---

VACANCY_KEYWORDS = [
    "вакансия", "ищем", "требуется", "нанимаем", "открыта позиция",
    "job", "hiring", "we're hiring", "we are hiring",
    "#вакансия", "#vacancy", "#job", "#hiring", "#работа",
    # resume/cv send phrases
    "резюме присылать", "резюме отправлять", "резюме на", "резюме в",
    "cv присылать", "cv отправлять", "cv на", "cv в",
    "отправьте резюме", "пришлите резюме",
    # extra vacancy hashtags and phrases
    "#вакансии", "открыта вакансия", "открываем вакансию",
]


RECRUITER_CONTACT_WORDS = re.compile(
    r"резюме|cv|откликнуться|писать|контакт|hr|рекрутер",
    re.IGNORECASE,
)

TELEGRAM_HANDLE = re.compile(r"@[a-z0-9_]{3,}", re.IGNORECASE)

# --- Irrelevant patterns ---

ROLE_WORDS = re.compile(
    r"разработчик|developer|engineer|аналитик|дизайнер|менеджер|тимлид|devops|qa|data",
    re.IGNORECASE,
)

NEWS_PATTERNS = re.compile(
    r"#новость|#мем|дайджест|подборка статей|ссылка дня",
    re.IGNORECASE,
)

# Boundary helpers:
#   \b  works reliably for Latin; for Cyrillic use explicit lookbehind/lookahead.
_CYR = r"[а-яёА-ЯЁa-zA-Z]"   # any letter — used as word-boundary marker for Cyrillic
_CB  = rf"(?<!{_CYR[1:-1]})"  # Cyrillic-safe left boundary  (lookbehind)
_CE  = rf"(?!{_CYR[1:-1]})"   # Cyrillic-safe right boundary (lookahead)

# Non-IT creative / management roles — not published
NON_IT_ROLES = re.compile(
    # --- animators ---
    rf"{_CB}аниматор{_CE}|\banimator\b"

    # --- game art / environment ---
    r"|\blevel\s+artist\b|\benvironment\s+artist\b"
    r"|\bconcept\s+artist\b|\bvfx\s+artist\b"
    r"|\b2d[\s/]?3d\s*artist\b|\b2d\s+artist\b|\b3d\s+artist\b"   # 2D/3D artist
    r"|\bgeneralist\s+artist\b|\bcharacter\s+artist\b"             # character/generalist artist
    r"|\btechnical\s+artist\b"                                     # technical artist (gamedev)
    r"|\bai\s+artist\b"                                            # AI artist
    + rf"|{_CB}художник\s+спецэффектов{_CE}"

    # --- level / game design ---
    r"|\bgame[\s\-]designer\b|\blevel[\s\-]designer\b|\blevel[\s\-]design\b"
    + rf"|{_CB}гейм[\s\-]дизайнер{_CE}|{_CB}геймдизайнер{_CE}"
    + rf"|{_CB}игровой[\s\-]дизайнер{_CE}"

    # --- typography ---
    r"|\btypographer\b|\bfont\s+designer\b"
    + rf"|{_CB}типограф{_CE}"

    # --- affiliate marketing ---
    r"|\baffiliate\s+manager\b"
    + rf"|{_CB}аффилиат{_CE}"

    # --- delivery / CDO ---
    r"|\bcdo\b|\bchief\s+delivery\b|\bdelivery\s+manager\b"

    # --- copywriting ---
    r"|\bcopywriter\b"
    + rf"|{_CB}копирайтер{_CE}"

    r"|\bproject\s+writer\b"

    # --- motion / content / graphic design ---
    r"|\bmotion[\s\-]designer\b"
    + rf"|{_CB}моушн[\s\-]дизайнер{_CE}"
    r"|\bcontent\s+market|\bgraphic[\s\-]designer\b"
    + rf"|{_CB}контент[\s\-]маркетолог{_CE}|{_CB}контент\s+маркетолог{_CE}"
    + rf"|{_CB}графический[\s\-]дизайнер{_CE}"

    # --- sales / traffic / UA / B2B sales ---
    + rf"|{_CB}менеджер\s+по\s+продажам{_CE}"
    r"|\bsales\s+manager\b|\btraffic[\s\-]?manager\b"
    + rf"|{_CB}трафик[\s\-]менеджер{_CE}"
    r"|\buser\s+acquisition\b|\bua[\s\-]manager\b"
    + rf"|{_CB}ua[\s\-]менеджер{_CE}"
    + rf"|{_CB}руководитель\s+b2b{_CE}"
    r"|\bb2b\s+sales\s+(?:manager|lead|director)\b"

    # --- art direction ---
    r"|\bart[\s\-]director\b"
    + rf"|{_CB}арт[\s\-]директор{_CE}"

    # --- producer ---
    r"|\bproducer(?!.*developer)\b"
    + rf"|{_CB}продюсер{_CE}"

    # --- travel / visa manager ---
    r"|\btravel[\s\-]manager\b|\bvisa[\s\-]manager\b"

    # --- project manager ---
    r"|\bproject[\s\-]manager\b"
    + rf"|{_CB}проджект[\s\-]менеджер{_CE}"

    # --- integration manager ---
    r"|\bintegration\s+manager\b"
    + rf"|{_CB}интеграционный\s+менеджер{_CE}"

    # --- support helpdesk (not support engineer) ---
    r"|\btechnical\s+support\s+agent\b|\bsupport\s+agent\b"
    r"|\bit\s+support\s+specialist\b|\bsupport\s+specialist\b|\bhelpdesk\b|\bhelp\s+desk\b"

    # --- HR / people ---
    r"|\bhr\s+manager\b|\bhr\s+generalist\b|\brecruiter\b"
    r"|\bhead\s+of\s+people\b"
    + rf"|{_CB}рекрутер{_CE}"
    + rf"|{_CB}руководитель\s+по\s+людям{_CE}"

    # --- office manager ---
    r"|\boffice\s+manager\b"

    # --- other gamedev non-IT ---
    r"|\bsound\s+designer\b|\bnarrative\s+designer\b"
    + rf"|{_CB}нарративный[\s\-]дизайнер{_CE}"
    r"|\bui[\s/]?ux\s+artist\b|\bcompositor\b"

    # --- UI/UX designer ---
    r"|\bui[\s/]?ux?\s+designer\b|\bui\s+designer\b|\bux\s+designer\b"

    # --- marketing (non-technical) ---
    r"|\bproduct\s+marketing\s+manager\b|\bmarketing\s+manager\b|\bmarketing\s+director\b"

    # --- SEO as primary role ---
    r"|\bseo[\s\-]lead\b|\bseo[\s\-]specialist\b|\bseo[\s\-]manager\b"
    + rf"|{_CB}seo[\s\-]менеджер{_CE}|{_CB}seo[\s\-]специалист{_CE}"

    # --- ops/operations assistant ---
    r"|\bops\s+assistant\b"
    + rf"|{_CB}помощник\s+операционной{_CE}"

    # --- performance manager (non-technical) ---
    + rf"|{_CB}менеджер\s+по\s+производительности{_CE}"

    # --- financial analyst / finance operations / finance specialist ---
    r"|\bfinancial\s+analyst\b|\bfinance\s+analyst\b|\bfinance\s+operations\b"
    r"|\bfinance\s+specialist\b|\bfinancial\s+specialist\b"
    + rf"|{_CB}финансовый\s+аналитик{_CE}"

    # --- compliance manager (non-IT) ---
    r"|\bregulatory\s+compliance\b|\bcompliance\s+manager\b"
    + rf"|{_CB}комплаенс[\s\-]менеджер{_CE}"

    # --- 3D modeler (architectural, non-IT) ---
    r"|\b3d[\s\-]?modell?er\b"
    + rf"|{_CB}3d[\s\-]?модел[ьл]ер{_CE}",

    re.IGNORECASE | re.UNICODE,
)

# Advertising markers — any match → irrelevant immediately
AD_PATTERNS = re.compile(
    r"\berid\b|erid:"                          # Russian ad labeling (обязательная маркировка)
    r"|utm_source|utm_medium|utm_campaign"     # UTM-параметры в ссылках
    r"|ИНН\s*\d{10,12}"                        # ИНН с цифрами — только в рекламных дисклеймерах
    r"|\bреклама\b"                            # слово «реклама» (маркировка)
    r"|\bпромокод\b|\bпромо\b"                # промо-посты
    r"|\bООО\s+[«\"A-ZА-ЯЁ]",               # «ООО Название» в дисклеймере
    re.IGNORECASE | re.UNICODE,
)


def _has_telegram_contact(text: str) -> bool:
    """Returns True if the text contains a Telegram handle (@username) or t.me/ link."""
    return bool(TELEGRAM_HANDLE.search(text)) or bool(_TG_LINK_RE.search(text))


def _has_reply_in_dm(text: str) -> bool:
    """Returns True if the text contains phrases like 'в личку', 'в лс', 'в директ', etc."""
    return bool(_REPLY_IN_DM_RE.search(text))


def _has_vacancy_keyword(text_lower: str) -> bool:
    for kw in VACANCY_KEYWORDS:
        if kw.lower() in text_lower:
            return True
    return False


def _has_it_roles(text: str) -> bool:
    """
    Returns True if the text contains enough IT-role signals.
    Two-tier: specific keywords count freely; general role words
    (инженер, аналитик, architect…) count only if at least one
    specific keyword is also present.
    """
    norm = normalize(text)

    # Count specific keyword matches (word boundary regex)
    specific_matches = len(SPECIFIC_RE.findall(norm))

    # Count exact substring matches for keywords with special chars (c++, .net, 1с…)
    special_matches = sum(1 for kw in SPECIAL_CHAR_KEYWORDS if kw in norm)

    total_specific = specific_matches + special_matches

    if total_specific >= 2:
        return True

    if total_specific >= 1:
        # Allow one general role word as the second signal
        general_matches = len(GENERAL_RE.findall(norm))
        if general_matches >= 1:
            return True

    return False


def _has_recruiter_contact(text: str) -> bool:
    for match in TELEGRAM_HANDLE.finditer(text):
        start = max(0, match.start() - 200)
        end = min(len(text), match.end() + 200)
        window = text[start:end]
        if RECRUITER_CONTACT_WORDS.search(window):
            return True
    return False


def classify(text: str, sender_username: str | None = None) -> tuple[str, str]:
    """
    Returns (label, reason) where label is 'relevant', 'irrelevant', or 'uncertain'.

    sender_username — username отправителя в боте, используется как fallback-контакт,
    когда текст содержит фразу "в личку"/"в лс" без явного @handle (тогда откликаться
    предполагается тому, кто прислал вакансию).
    """
    if not text:
        return "irrelevant", "пустой текст"

    # --- Irrelevant checks first ---
    if len(text) < 100:
        return "irrelevant", f"текст слишком короткий ({len(text)} символов)"

    if not ROLE_WORDS.search(text) and not _has_it_roles(text):
        return "irrelevant", "нет IT-ролей (разработчик, engineer, qa и т.д.)"

    if NEWS_PATTERNS.search(text):
        return "irrelevant", "новость/дайджест (#новость, дайджест и т.д.)"

    if NON_IT_ROLES.search(text):
        m = NON_IT_ROLES.search(text)
        return "irrelevant", f"нетехническая/творческая роль: «{m.group()}»"

    if AD_PATTERNS.search(text):
        m = AD_PATTERNS.search(text)
        return "irrelevant", f"рекламная маркировка: «{m.group()}»"

    # --- Relevant checks ---
    text_norm = normalize(text)

    has_external_url = bool(_EXTERNAL_URL_RE.search(text))

    # Contact check: explicit TG handle/link, or DM-reply phrase (sender acts as contact)
    has_tg_contact = _has_telegram_contact(text)
    has_dm_reply = _has_reply_in_dm(text)
    has_contact = has_tg_contact or (has_dm_reply and sender_username is not None)

    def _result(has_ext_url: bool, trigger: str) -> tuple[str, str]:
        if has_ext_url:
            return "uncertain", f"{trigger} + внешняя ссылка → на проверку LLM"
        return "relevant", trigger

    if _has_vacancy_keyword(text_norm):
        if not has_contact:
            return "irrelevant", "есть ключевое слово вакансии, но нет контакта (TG handle / t.me / фраза 'в личку')"
        return _result(has_external_url, "ключевое слово вакансии + контакт найден")

    if _has_it_roles(text):
        if not has_contact:
            return "irrelevant", "есть IT-роль/стек, но нет контакта рекрутера"
        return _result(has_external_url, "IT-роль/стек + контакт найден")

    if _has_recruiter_contact(text):
        if not has_contact:
            return "irrelevant", "контакт рекрутера есть, но нет TG handle рядом"
        return _result(has_external_url, "контакт рекрутера + TG handle найден")

    return "uncertain", "не попало ни под одно правило → на проверку LLM"
