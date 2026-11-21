"""Opt-in acceptance checks for editing an upcoming pending request."""

from datetime import date, datetime, time, timedelta, timezone

import pytest

from after_hours import get_request_history, get_student_request, submit_request


CAMPUS_TIME = timezone(timedelta(hours=2))
STAY_DATE = date(2026, 12, 7)
START = datetime.combine(STAY_DATE, time(18), tzinfo=CAMPUS_TIME)
BEFORE_START = START - timedelta(minutes=1)


@pytest.fixture
def pending_request(tmp_path):
    database = tmp_path / "edit.sqlite3"
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


def test_owner_can_edit_room_and_history_records_the_change(pending_request):
    from after_hours import edit_request_room

    database, reference = pending_request
    edit_request_room(
        database, reference, student_id="student-a", room="Room 204", edited_at=BEFORE_START
    )

    saved = get_student_request(database, reference, student_id="student-a")
    assert saved["reference"] == reference
    assert saved["status"] == "Pending Approval"
    assert saved["room"] == "Room 204"
    assert saved["building"] == "Synthetic Science Building"
    history = get_request_history(database, reference, actor_role="facilities")
    assert len(history) == 1
    event = history[0]
    assert event["reference"] == reference
    assert event["actor_id"] == "student-a"
    assert event["decided_at"] == BEFORE_START
    assert event["from_status"] == event["to_status"] == "Pending Approval"
    assert event["old_room"] == "Room 101"
    assert event["new_room"] == "Room 204"


@pytest.mark.parametrize(
    ("student_id", "edited_at", "room", "error"),
    [
        pytest.param("student-b", BEFORE_START, "Room 204", PermissionError, id="another-student"),
        pytest.param("student-a", START, "Room 204", ValueError, id="at-start"),
        pytest.param("student-a", START + timedelta(minutes=1), "Room 204", ValueError, id="after-start"),
        pytest.param("student-a", BEFORE_START, "   ", ValueError, id="blank-room"),
    ],
)
def test_invalid_edit_preserves_original_room_and_history(
    pending_request, student_id, edited_at, room, error
):
    from after_hours import edit_request_room

    database, reference = pending_request
    with pytest.raises(error):
        edit_request_room(database, reference, student_id=student_id, room=room, edited_at=edited_at)

    saved = get_student_request(database, reference, student_id="student-a")
    assert saved["room"] == "Room 101"
    assert saved["status"] == "Pending Approval"
    assert get_request_history(database, reference, actor_role="facilities") == []
