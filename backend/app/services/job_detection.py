import logging
import re
from dataclasses import asdict, dataclass
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

HIRING_KEYWORDS = [
    "hiring",
    "vacancy",
    "vacancies",
    "recruitment",
    "recruiting",
    "walk-in",
    "walk in",
    "off campus",
    "off-campus",
    "job opening",
    "job opportunity",
    "we are hiring",
    "career opportunity",
    "immediate joining",
]

ROLE_KEYWORDS = [
    "developer",
    "engineer",
    "intern",
    "fresher",
    "associate",
    "analyst",
    "manager",
    "executive",
    "consultant",
    "officer",
    "specialist",
    "trainee",
]

APPLY_KEYWORDS = [
    "apply now",
    "apply here",
    "click here to apply",
    "apply:",
    "apply -",
    "apply link",
    "official apply",
    "register now",
    "registration link",
    "application link",
]

FIELD_PATTERNS = {
    "location": re.compile(r"(?:location|place|venue)\s*[:\-]\s*(.+)", re.I),
    "experience": re.compile(r"(?:experience|exp)\s*[:\-]\s*(.+)", re.I),
    "qualification": re.compile(r"(?:qualification|eligibility|education)\s*[:\-]\s*(.+)", re.I),
    "batch": re.compile(r"(?:batch|pass\s*out)\s*[:\-]\s*(.+)", re.I),
    "salary": re.compile(r"(?:salary|ctc|package|stipend)\s*[:\-]\s*(.+)", re.I),
}

SKILLS_PATTERN = re.compile(r"(?:skills?|tech\s*stack|technologies)\s*[:\-]\s*(.+)", re.I)

EMPLOYMENT_TYPE_KEYWORDS = [
    ("internship", "Internship"),
    ("intern", "Internship"),
    ("full-time", "Full-time"),
    ("full time", "Full-time"),
    ("part-time", "Part-time"),
    ("part time", "Part-time"),
    ("contract", "Contract"),
    ("walk-in", "Walk-in"),
    ("walk in", "Walk-in"),
]

URL_PATTERN = re.compile(r"(https?://[^\s)>\]]+)")

SOCIAL_DOMAINS = [
    "whatsapp.com",
    "t.me",
    "telegram.me",
    "telegram.org",
    "facebook.com",
    "fb.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "youtu.be",
    "twitter.com",
    "x.com",
]

TITLE_PATTERNS = [
    re.compile(
        r"^(?P<company>.+?)\s+off[\s-]*campus\b(?:\s+\d{4})?\s*(?:hiring)?\s*"
        r"(?:freshers?|graduates?)?\s*[–\-:]\s*(?P<title>.+)$",
        re.I,
    ),
    re.compile(r"^(?P<company>.+?)\s+is\s+hiring\b\s*(?:for)?\s*[:\-]?\s*(?P<title>.+)$", re.I),
    re.compile(r"^(?P<company>.+?)\s+recruit(?:ing|ment)\b.*?[–\-:]\s*(?P<title>.+)$", re.I),
    re.compile(r"^(?P<company>.+?)\s+hiring\b\s*(?:for)?\s*[:\-]?\s*(?P<title>.+)$", re.I),
]

JOB_SCORE_THRESHOLD = 4


@dataclass
class ExtractedJob:
    company: str | None
    title: str | None
    location: str | None
    experience: str | None
    qualification: str | None
    batch: str | None
    salary: str | None
    skills: list[str] | None
    employment_type: str | None
    original_apply_url: str | None
    telegram_message_id: int
    telegram_channel: str
    telegram_message_url: str
    posted_at: str

    def to_dict(self) -> dict:
        return asdict(self)


def extract_urls(text: str) -> list[str]:
    return URL_PATTERN.findall(text)


def _is_social_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(domain in host for domain in SOCIAL_DOMAINS)


def score_message(text: str) -> tuple[int, dict]:
    lower = text.lower()
    signals = {}

    hiring_hit = any(keyword in lower for keyword in HIRING_KEYWORDS)
    role_hit = any(keyword in lower for keyword in ROLE_KEYWORDS)
    apply_hit = any(keyword in lower for keyword in APPLY_KEYWORDS) or bool(
        re.search(r"\bapply\b", lower)
    )
    field_hits = sum(1 for pattern in FIELD_PATTERNS.values() if pattern.search(text))
    urls = extract_urls(text)
    has_url = bool(urls)

    score = 0
    score += 2 if hiring_hit else 0
    score += 1 if role_hit else 0
    score += 1 if apply_hit else 0
    score += field_hits
    score += 1 if has_url else 0

    if has_url and field_hits == 0 and not role_hit and all(_is_social_url(u) for u in urls):
        score -= 2

    signals.update(
        hiring_keyword=hiring_hit,
        role_keyword=role_hit,
        apply_keyword=apply_hit,
        structured_fields=field_hits,
        has_url=has_url,
        score=score,
    )
    return score, signals


def is_job_post(text: str) -> bool:
    if not text or not text.strip():
        return False
    score, signals = score_message(text)
    logger.debug("job-detection score=%s signals=%s", score, signals)
    return score >= JOB_SCORE_THRESHOLD


def _strip_leading_symbols(line: str) -> str:
    return re.sub(r"^[^A-Za-z0-9]+", "", line).strip()


def extract_company_and_title(text: str) -> tuple[str | None, str | None]:
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    cleaned = _strip_leading_symbols(first_line)
    if not cleaned:
        return None, None

    for pattern in TITLE_PATTERNS:
        match = pattern.match(cleaned)
        if match:
            company = match.group("company").strip() or None
            title = match.group("title").strip() or None
            return company, title

    for sep in (" – ", " - ", ": "):
        if sep in cleaned:
            left, right = cleaned.split(sep, 1)
            if len(left.split()) <= 5:
                return left.strip() or None, right.strip() or None
            break

    return None, cleaned


def extract_apply_url(text: str) -> str | None:
    urls = extract_urls(text)
    non_social = [url for url in urls if not _is_social_url(url)]
    if not non_social:
        return None
    if len(non_social) == 1:
        return non_social[0]

    for line in text.splitlines():
        lower_line = line.lower()
        if any(keyword in lower_line for keyword in APPLY_KEYWORDS) or re.search(
            r"\bapply\b", lower_line
        ):
            line_urls = [url for url in extract_urls(line) if not _is_social_url(url)]
            if line_urls:
                return line_urls[0]

    return non_social[0]


def _extract_field(text: str, pattern: re.Pattern) -> str | None:
    match = pattern.search(text)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def extract_skills(text: str) -> list[str] | None:
    match = SKILLS_PATTERN.search(text)
    if not match:
        return None
    parts = re.split(r"[,/|]", match.group(1).strip())
    skills = [part.strip() for part in parts if part.strip()]
    return skills or None


def extract_employment_type(text: str) -> str | None:
    lower = text.lower()
    for keyword, label in EMPLOYMENT_TYPE_KEYWORDS:
        if keyword in lower:
            return label
    return None


def process_message(message: dict) -> dict | None:
    text = message.get("message_text") or ""
    if not is_job_post(text):
        return None

    company, title = extract_company_and_title(text)

    job = ExtractedJob(
        company=company,
        title=title,
        location=_extract_field(text, FIELD_PATTERNS["location"]),
        experience=_extract_field(text, FIELD_PATTERNS["experience"]),
        qualification=_extract_field(text, FIELD_PATTERNS["qualification"]),
        batch=_extract_field(text, FIELD_PATTERNS["batch"]),
        salary=_extract_field(text, FIELD_PATTERNS["salary"]),
        skills=extract_skills(text),
        employment_type=extract_employment_type(text),
        original_apply_url=extract_apply_url(text),
        telegram_message_id=message["message_id"],
        telegram_channel=message["channel_username"],
        telegram_message_url=message["message_url"],
        posted_at=message["message_date"],
    )
    return job.to_dict()
