"""Opt-in acceptance checks for recurring stays."""

from datetime import date, datetime, time, timezone

import pytest


def recurring_fields():
    return {
        "student_id": "student-a",
        "submitted_at": datetime(2026, 12, 1, 10, tzinfo=timezone.utc),
        "start_date": date(2026, 12, 7),
        "end_date": date(2026, 12, 14),
        "weekdays": (0, 2),
        "start_time": time(18),
        "expected_departure_time": time(20),
        "building": "Synthetic Science Building",
        "room": "Room 101",
        "reason": "Group project meeting",
    }


def test_recurring_stay_saves_a_private_series_and_separate_occurrences(tmp_path):
    from after_hours import (
        approve_request, get_recurring_request, list_pending_requests, submit_recurring_request,
    )

    database = tmp_path / "recurring.sqlite3"
    fields = recurring_fields()

    receipt = submit_recurring_request(database, **fields)
    reference = receipt["reference"]
    assert isinstance(reference, str) and reference.strip()
    assert receipt["status"] == "Pending Approval"

    saved = get_recurring_request(database, reference, student_id="student-a")
    assert saved["reference"] == reference
    assert saved["status"] == "Pending Approval"
    assert saved["start_date"] == fields["start_date"]
    assert saved["end_date"] == fields["end_date"]
    occurrences = saved["occurrences"]
    assert [item["stay_date"] for item in occurrences] == [
        date(2026, 12, 7), date(2026, 12, 9), date(2026, 12, 14)
    ]
    assert len({item["reference"] for item in occurrences}) == 3
    for item in occurrences:
        assert item["reference"] != reference
        assert item["parent_reference"] == reference
        assert item["status"] == "Pending Approval"
        for key in ("building", "room", "start_time", "expected_departure_time"):
            assert item[key] == fields[key]

    assert get_recurring_request(database, reference, student_id="student-b") is None
    assert list_pending_requests(database, actor_role="facilities") == []
    for recurring_reference in (reference, occurrences[0]["reference"]):
        approve_request(
            database, recurring_reference, actor_role="facilities",
            actor_id="reviewer-a", decided_at=fields["submitted_at"],
        )
    assert get_recurring_request(database, reference, student_id="student-a") == saved


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"end_date": date(2026, 12, 6)}, id="reversed-range"),
        pytest.param({"weekdays": ()}, id="no-weekdays"),
        pytest.param({"end_date": date(2026, 12, 7), "weekdays": (2,)}, id="no-matching-date"),
    ],
)
def test_recurring_stay_rejects_invalid_schedules(tmp_path, changes):
    from after_hours import submit_recurring_request

    with pytest.raises(ValueError):
        submit_recurring_request(tmp_path / "recurring.sqlite3", **{**recurring_fields(), **changes})
