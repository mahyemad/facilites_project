"""Opt-in acceptance checks for the pending rejection feature."""

from datetime import date, datetime, time, timezone

import pytest

from after_hours import get_request, get_student_request, list_student_requests, submit_request


DECIDED_AT = datetime(2026, 12, 2, 9, 30, tzinfo=timezone.utc)


@pytest.fixture
def pending_request(tmp_path):
    database = tmp_path / "rejection.sqlite3"
    receipt = submit_request(
        database,
        student_id="student-a",
        submitted_at=datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc),
        stay_date=date(2026, 12, 7),
        start_time=time(18, 0),
        expected_departure_time=time(20, 0),
        building="Synthetic Science Building",
        room="Room 101",
        reason="Group project meeting",
    )
    return database, receipt["reference"]


def test_facilities_rejection_is_persisted_and_visible_to_owner(pending_request):
    from after_hours import reject_request

    database, reference = pending_request
    reason = "Room is unavailable"
    reject_request(
        database, reference, actor_role="facilities", actor_id="reviewer-a",
        decided_at=DECIDED_AT, reason=reason,
    )

    saved = get_request(database, reference)
    assert saved["status"] == "Rejected"
    assert saved["rejection_reason"] == reason
    assert saved["decision_maker_id"] == "reviewer-a"
    assert saved["decided_at"] == DECIDED_AT
    student_view = get_student_request(database, reference, student_id="student-a")
    assert student_view["status"] == "Rejected"
    assert "rejection_reason" not in student_view
    assert "rejection_reason" not in list_student_requests(database, student_id="student-a")[0]
    assert get_student_request(database, reference, student_id="student-b") is None


def test_student_cannot_reject_even_their_own_request(pending_request):
    from after_hours import reject_request

    database, reference = pending_request
    with pytest.raises(PermissionError):
        reject_request(
            database, reference, actor_role="student", actor_id="student-a",
            decided_at=DECIDED_AT, reason="Attempted student decision",
        )

    assert get_request(database, reference)["status"] == "Pending Approval"
