"""Acceptance checks for submitting and validating a single-day request."""

import sqlite3
from contextlib import closing
from datetime import date, datetime, time, timezone, timedelta
from importlib.util import find_spec

import pytest


def test_single_day_request_is_saved_with_a_unique_pending_reference(tmp_path):
    if find_spec("after_hours") is None:
        pytest.fail("AH-T01 requires an after_hours module with submit_request and get_request.")

    from after_hours import get_request, submit_request

    store_path = tmp_path / "after-hours.sqlite3"
    submitted_at = datetime(2026, 12, 1, 10, 0, tzinfo=timezone(timedelta(hours=2)))
    fields = {
        "stay_date": date(2026, 12, 7),
        "start_time": time(18, 0),
        "expected_departure_time": time(20, 0),
        "building": "Synthetic Science Building",
        "room": "Room 101",
        "reason": "Group project meeting",
    }

    receipt = submit_request(
        store_path, student_id="student-a", submitted_at=submitted_at, **fields
    )

    reference = receipt["reference"]
    assert isinstance(reference, str) and reference.strip()
    assert receipt["status"] == "Pending Approval"

    saved = get_request(store_path, reference)
    assert saved is not None
    assert saved["reference"] == reference
    assert saved["student_id"] == "student-a"
    assert saved["submitted_at"] == submitted_at
    assert saved["status"] == "Pending Approval"
    for field, expected in fields.items():
        assert saved[field] == expected, field

    next_date = date(2026, 12, 8)
    second = submit_request(
        store_path,
        student_id="student-a",
        submitted_at=submitted_at,
        **{**fields, "stay_date": next_date},
    )

    assert second["reference"] != reference
    assert get_request(store_path, reference)["stay_date"] == fields["stay_date"]
    assert get_request(store_path, second["reference"])["stay_date"] == next_date


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        pytest.param("room", "", id="missing-room"),
        pytest.param("reason", "   ", id="missing-reason"),
        pytest.param("stay_date", "2026-02-30", id="nonexistent-date"),
        pytest.param("expected_departure_time", time(17, 0), id="departure-before-start"),
    ],
)
def test_invalid_request_reports_the_field_and_saves_no_record(tmp_path, field, invalid_value):
    from after_hours import submit_request

    store_path = tmp_path / "after-hours.sqlite3"
    fields = {
        "student_id": "student-a",
        "submitted_at": datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc),
        "stay_date": date(2026, 12, 7),
        "start_time": time(18, 0),
        "expected_departure_time": time(20, 0),
        "building": "Synthetic Science Building",
        "room": "Room 101",
        "reason": "Group project meeting",
    }
    existing = submit_request(store_path, **fields)

    with pytest.raises(ValueError, match=field):
        submit_request(store_path, **{**fields, field: invalid_value})

    with closing(sqlite3.connect(store_path)) as connection:
        assert connection.execute("SELECT reference FROM requests").fetchall() == [
            (existing["reference"],)
        ]


@pytest.fixture
def pending_request(tmp_path):
    from after_hours import submit_request

    store_path = tmp_path / "after-hours.sqlite3"
    receipt = submit_request(
        store_path,
        student_id="student-a",
        submitted_at=datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc),
        stay_date=date(2026, 12, 7),
        start_time=time(18, 0),
        expected_departure_time=time(20, 0),
        building="Synthetic Science Building",
        room="Room 101",
        reason="Group project meeting",
    )
    return store_path, receipt["reference"]


def test_facilities_approves_a_pending_request(pending_request):
    from after_hours import approve_request, get_request, list_pending_requests

    store_path, reference = pending_request
    pending = list_pending_requests(store_path, actor_role="facilities")
    assert [request["reference"] for request in pending] == [reference]

    approve_request(store_path, reference, actor_role="facilities")

    assert get_request(store_path, reference)["status"] == "Approved"
    assert list_pending_requests(store_path, actor_role="facilities") == []


def test_student_cannot_review_or_approve_a_pending_request(pending_request):
    from after_hours import approve_request, get_request, list_pending_requests

    store_path, reference = pending_request
    with pytest.raises(PermissionError):
        list_pending_requests(store_path, actor_role="student")
    with pytest.raises(PermissionError):
        approve_request(store_path, reference, actor_role="student")
    assert get_request(store_path, reference)["status"] == "Pending Approval"
