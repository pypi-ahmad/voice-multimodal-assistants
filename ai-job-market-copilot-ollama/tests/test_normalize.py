from __future__ import annotations

from job_market_copilot.processing.normalize import deduplicate_records, normalize_records


def test_normalize_and_deduplicate_records() -> None:
    remotive_jobs = [
        {
            "id": 1,
            "title": "Senior Machine Learning Engineer",
            "company_name": "Acme AI",
            "url": "https://example.com/jobs/1",
            "publication_date": "2026-06-10T10:00:00+00:00",
            "candidate_required_location": "Anywhere",
            "category": "Software Development",
            "description": "Build ML systems",
            "salary": "$120k-$160k",
            "job_type": "Full-time",
            "tags": ["python", "ml"],
        }
    ]

    wwr_jobs = [
        {
            "id": "abc",
            "company": "Acme AI",
            "title": "Senior Machine Learning Engineer",
            "url": "https://example.com/jobs/1?utm=wwr",
            "published": "Wed, 10 Jun 2026 10:00:00 GMT",
            "location": "Anywhere",
            "category": "Back-End Programming",
            "employment_type": "Full-Time",
            "description": "Build ML systems",
            "tags": ["python", "ml"],
        }
    ]

    normalized = normalize_records(remotive_jobs, wwr_jobs)
    deduped = deduplicate_records(normalized)

    assert normalized.height == 2
    assert deduped.height == 1
    assert deduped[0, "title"] == "Senior Machine Learning Engineer"
