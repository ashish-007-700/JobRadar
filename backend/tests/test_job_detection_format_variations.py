"""Section 11 quality review: the deterministic detector must not depend on one
exact Telegram message format. Each case below uses a distinct, realistic
phrasing for the same underlying "this is a job post" signal."""

import pytest

from app.services.job_detection import is_job_post

JOB_FORMAT_VARIATIONS = {
    "hiring_freshers": (
        "ABC Corp Hiring Freshers for Software Developer role. Location: Pune. "
        "Apply now: https://abc.com/apply"
    ),
    "we_are_hiring": (
        "We Are Hiring! Data Analyst position at XYZ Ltd, Mumbai. "
        "Apply here: https://xyz.com/careers"
    ),
    "walk_in_drive": (
        "Walk-in Drive for Customer Support Executive, Chennai. Walk-in with resume. "
        "Apply: https://walkin.com/jobs"
    ),
    "off_campus_drive": (
        "TCS Off Campus Drive 2026 for Freshers. Batch 2025/2026. "
        "Apply now: https://tcs.com/careers/apply"
    ),
    "campus_hiring": (
        "Infosys Campus Hiring for BE/BTech graduates. Apply here: https://infosys.com/apply"
    ),
    "recruitment_drive": (
        "Wipro Recruitment Drive for Software Engineers, Bangalore. "
        "Apply now: https://wipro.com/jobs/apply"
    ),
    "internship_program": (
        "Summer Internship Program 2026 for Computer Science students, Remote. "
        "Apply now: https://startup.com/intern/apply"
    ),
    "graduate_trainee_program": (
        "Graduate Trainee Program - HCL Technologies, Noida. Apply here: https://hcl.com/gtp/apply"
    ),
    "software_engineer_with_fields": (
        "Software Engineer - Startup Inc\n"
        "Location: Hyderabad\n"
        "Experience: 2-4 years\n"
        "Apply Now: https://startupinc.com/apply"
    ),
    "developer_hiring": (
        "Backend Developer Hiring - Remote, Full-time. Apply now: https://remote.io/jobs/apply"
    ),
}


@pytest.mark.parametrize("text", JOB_FORMAT_VARIATIONS.values(), ids=JOB_FORMAT_VARIATIONS.keys())
def test_realistic_job_format_variations_are_detected(text):
    assert is_job_post(text) is True


NON_JOB_VARIATIONS = {
    "channel_growth_announcement": (
        "🎉 We just crossed 100k subscribers! Thank you all for being part of this journey."
    ),
    "generic_motivational_post": (
        "Success doesn't come overnight. Keep pushing towards your goals every single day!"
    ),
    "unrelated_advertisement": (
        "50% OFF on all courses this week only! Enroll now: https://coursesite.com/sale"
    ),
    "pure_social_link": ("Follow us on Instagram for more updates: https://instagram.com/ourchannel"),
}


@pytest.mark.parametrize("text", NON_JOB_VARIATIONS.values(), ids=NON_JOB_VARIATIONS.keys())
def test_obvious_non_job_posts_are_not_misclassified(text):
    assert is_job_post(text) is False
