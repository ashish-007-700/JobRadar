from app.services.job_detection import extract_apply_url, is_job_post, process_message


def make_message(text: str, message_id: int = 1, channel_username: str = "testchannel") -> dict:
    return {
        "message_id": message_id,
        "channel_id": -1001111111111,
        "channel_username": channel_username,
        "message_text": text,
        "message_date": "2026-09-15T09:00:00+00:00",
        "message_url": f"https://t.me/{channel_username}/{message_id}",
    }


NORMAL_JOB_POST = """\
\U0001f468‍\U0001f4bb Clarivate Off Campus 2026 Hiring Freshers – Associate STEM Content Analyst (Engineering)

\U0001f4cd Location: Chennai (Hybrid)
\U0001f393 Qualification: B.Sc/M.Sc - Mathematics, Physics, Computer Science, BCA/MCA
\U0001f4bc Experience: Freshers / 0–1 Year
\U0001f947 Batch: 2025 / 2026
\U0001f4b0 CTC: Up to ₹6 LPA
\U0001f517 Apply Now: https://www.fresheroffcampus.com/clarivate-off-campus/
"""


def test_normal_job_post_extracts_all_fields():
    job = process_message(make_message(NORMAL_JOB_POST))
    assert job is not None
    assert job["company"] == "Clarivate"
    assert job["title"] == "Associate STEM Content Analyst (Engineering)"
    assert job["location"] == "Chennai (Hybrid)"
    assert job["qualification"].startswith("B.Sc/M.Sc")
    assert job["experience"] == "Freshers / 0–1 Year"
    assert job["batch"] == "2025 / 2026"
    assert job["salary"] == "Up to ₹6 LPA"
    assert job["original_apply_url"] == "https://www.fresheroffcampus.com/clarivate-off-campus/"
    assert job["telegram_message_id"] == 1
    assert job["telegram_channel"] == "testchannel"


def test_job_post_missing_salary():
    text = NORMAL_JOB_POST.replace("\U0001f4b0 CTC: Up to ₹6 LPA\n", "")
    job = process_message(make_message(text))
    assert job is not None
    assert job["salary"] is None
    assert job["location"] == "Chennai (Hybrid)"


def test_job_post_missing_qualification():
    lines = [
        line
        for line in NORMAL_JOB_POST.splitlines()
        if "Qualification" not in line
    ]
    text = "\n".join(lines)
    job = process_message(make_message(text))
    assert job is not None
    assert job["qualification"] is None
    assert job["experience"] is not None


def test_multiple_links_prefers_apply_link():
    text = """\
XYZ Corp Hiring Software Developer

More jobs: https://xyzcorp.com/careers/all
Apply Now: https://xyzcorp.com/careers/apply/123
"""
    job = process_message(make_message(text))
    assert job is not None
    assert job["original_apply_url"] == "https://xyzcorp.com/careers/apply/123"


def test_whatsapp_telegram_and_apply_links():
    text = """\
ABC Solutions is hiring Backend Engineer

Join our WhatsApp group: https://chat.whatsapp.com/abc123
Join our Telegram: https://t.me/abcjobs
Apply here: https://abcsolutions.com/apply
"""
    job = process_message(make_message(text))
    assert job is not None
    assert job["original_apply_url"] == "https://abcsolutions.com/apply"


def test_apply_now_in_different_format():
    text = """\
DEF Ltd Hiring QA Engineer, Bangalore. Experience: 0-2 years.
\U0001f449 Apply: https://deflimited.com/qa-role
"""
    job = process_message(make_message(text))
    assert job is not None
    assert job["original_apply_url"] == "https://deflimited.com/qa-role"


def test_non_job_promotional_message_is_rejected():
    text = """\
\U0001f525 Join our WhatsApp group for more off campus updates!
https://chat.whatsapp.com/xxxxx
"""
    assert is_job_post(text) is False
    assert process_message(make_message(text)) is None


def test_channel_promo_without_job_signals_is_rejected():
    text = "Join our Telegram channel for daily job updates: https://t.me/xyz"
    assert is_job_post(text) is False


def test_emojis_and_unusual_spacing():
    text = """\
\U0001f4e2\U0001f4e2   GHI   Off   Campus   2026   Hiring    Freshers  –  Software Engineer

\U0001f4cd   Location  :   Hyderabad
\U0001f517 Apply Now:   https://ghi.example.com/apply
"""
    job = process_message(make_message(text))
    assert job is not None
    assert job["original_apply_url"] == "https://ghi.example.com/apply"


def test_multiple_potential_application_urls_picks_the_apply_one():
    text = """\
JKL Technologies Hiring Data Analyst

Read more about us: https://jkltech.com/about
Apply now here: https://jkltech.com/careers/data-analyst
"""
    assert extract_apply_url(text) == "https://jkltech.com/careers/data-analyst"


def test_ambiguous_company_title_extraction_does_not_crash():
    text = """\
Software Engineer Opening - Immediate Joining, Bangalore, 2-4 years experience.
Apply now: https://example.com/apply/software-engineer
"""
    job = process_message(make_message(text))
    assert job is not None
    assert job["title"]
    assert job["original_apply_url"] == "https://example.com/apply/software-engineer"


# Telegram edge cases: media-only / empty / whitespace-only messages must not crash --------


def test_media_only_message_with_no_text_is_not_a_job():
    message = make_message(None)
    assert process_message(message) is None


def test_empty_string_message_is_not_a_job():
    assert process_message(make_message("")) is None


def test_whitespace_only_message_is_not_a_job():
    assert process_message(make_message("   \n\t  ")) is None


def test_very_long_message_does_not_crash_detection():
    text = "Hiring Software Engineer. " * 500 + "Apply now: https://example.com/apply"
    job = process_message(make_message(text))
    assert job is not None
    assert job["original_apply_url"] == "https://example.com/apply"
