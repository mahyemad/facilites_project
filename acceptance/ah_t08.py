"""Opt-in acceptance checks for cancelling a single-day request."""

from datetime import date, datetime, time, timedelta, timezone

import pytest

from after_hours import approve_request, get_request, get_request_history, get_student_request, submit_request


CAMPUS_TIME = timezone(timedelta(hours=2))
STAY_DATE = date(2026, 12, 7)
START = datetime.combine(STAY_DATE, time(18), tzinfo=CAMPUS_TIME)
BEFORE_START = START - timedelta(minutes=1)


@pytest.fixture
def pending_request(tmp_path):
    database = tmp_path / "cancellation.sqlite3"
    receipt = submit_request(
        database,
        student_id="student-a",
        submitted_at=START - timedelta(days=1),
        stay_date=STAY_DATE,
        start_time=START.time(),
        expected_departure_time=time(20),
        building="Synthetic Science Building",
        room="Room 101",
        reason="Group project meeting",
    )
    return database, receipt["reference"]


@pytest.mark.parametrize("prior_status", ["Pending Approval", "Approved"])
def test_owner_can_cancel_before_start_and_history_records_the_action(pending_request, prior_status):
    from after_hours import cancel_request

    database, reference = pending_request
    approved_at = START - timedelta(hours=1)
    if prior_status == "Approved":
        approve_request(
            database, reference, actor_role="facilities", actor_id="reviewer-a",
            decided_at=approved_at,
        )
    prior_history = get_request_history(database, reference, actor_role="facilities")
    cancel_request(database, reference, student_id="student-a", cancelled_at=BEFORE_START)

    assert get_student_request(database, reference, student_id="student-a")["status"] == "Cancelled"
    if prior_status == "Approved":
        saved = get_request(database, reference)
        assert saved["decided_at"] == approved_at
        assert saved["decision_maker_id"] == "reviewer-a"
    history = get_request_history(database, reference, actor_role="facilities")
    assert len(history) == len(prior_history) + 1
    assert history[:-1] == prior_history
    event = history[-1]
    assert event["reference"] == reference
    assert event["actor_id"] == "student-a"
    assert event["decided_at"] == BEFORE_START
    assert event["from_status"] == prior_status
    assert event["to_status"] == "Cancelled"


@pytest.mark.parametrize(
    ("student_id", "cancelled_at", "error"),
    [
        pytest.param("student-b", BEFORE_START, PermissionError, id="another-student"),
        pytest.param("student-a", START, ValueError, id="at-start"),
        pytest.param("student-a", START + timedelta(minutes=1), ValueError, id="after-start"),
    ],
)
def test_invalid_cancellation_keeps_status_and_history(pending_request, student_id, cancelled_at, error):
    from after_hours import cancel_request

    database, reference = pending_request
    with pytest.raises(error):
        cancel_request(database, reference, student_id=student_id, cancelled_at=cancelled_at)

    assert get_student_request(database, reference, student_id="student-a")["status"] == "Pending Approval"
    assert get_request_history(database, reference, actor_role="facilities") == []
