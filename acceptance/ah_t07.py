"""Opt-in acceptance check for submission receipts and decision notifications."""

from datetime import date, datetime, time, timezone

from after_hours import approve_request, submit_request


def test_submission_receipts_and_decision_notifications_are_private(tmp_path):
    from after_hours import list_student_notifications, reject_request

    database = tmp_path / "notifications.sqlite3"
    submitted_at = datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc)
    decided_at = datetime(2026, 12, 2, 9, 30, tzinfo=timezone.utc)
    references = []
    for stay_date in (date(2026, 12, 7), date(2026, 12, 8)):
        receipt = submit_request(
            database,
            student_id="student-a",
            submitted_at=submitted_at,
            stay_date=stay_date,
            start_time=time(18, 0),
            expected_departure_time=time(20, 0),
            building="Synthetic Science Building",
            room="Room 101",
            reason="Group project meeting",
        )
        assert isinstance(receipt["reference"], str) and receipt["reference"].strip()
        assert receipt["status"] == "Pending Approval"
        references.append(receipt["reference"])

    approved, rejected = references
    assert approved != rejected
    reviewer = {"actor_role": "facilities", "actor_id": "reviewer-a", "decided_at": decided_at}
    approve_request(database, approved, **reviewer)
    reject_request(database, rejected, reason="Room unavailable", **reviewer)

    notifications = list_student_notifications(database, student_id="student-a")
    decisions = [
        (notification["reference"], notification["status"])
        for notification in notifications
        if notification["status"] in {"Approved", "Rejected"}
    ]
    assert sorted(decisions) == sorted([(approved, "Approved"), (rejected, "Rejected")])
    assert list_student_notifications(database, student_id="student-b") == []
