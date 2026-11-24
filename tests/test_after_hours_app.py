"""Exercise the demo through its HTTP interface using separate sessions."""

from datetime import datetime, timedelta
from io import BytesIO
from urllib.parse import urlencode
from wsgiref.util import setup_testing_defaults
from wsgiref.validate import validator


def send(app, path, *, form=None, cookie=None):
    body = b"" if form is None else urlencode(form).encode("ascii")
    environ = {
        "PATH_INFO": path,
        "SCRIPT_NAME": "",
        "QUERY_STRING": "",
        "REQUEST_METHOD": "GET" if form is None else "POST",
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": "application/x-www-form-urlencoded",
        "wsgi.input": BytesIO(body),
    }
    if cookie:
        environ["HTTP_COOKIE"] = cookie
    setup_testing_defaults(environ)
    response = {}

    def start_response(status, headers, exc_info=None):
        response.update(status=int(status.split()[0]), headers=dict(headers))

    chunks = app(environ, start_response)
    try:
        response["body"] = b"".join(chunks).decode("utf-8")
    finally:
        if hasattr(chunks, "close"):
            chunks.close()
    return response


def sign_in(app, account):
    response = send(app, "/login", form={"account": account})
    assert response["status"] == 303
    return response["headers"]["Set-Cookie"].split(";", 1)[0]


def test_student_request_appears_approved_only_to_its_owner(tmp_path):
    from after_hours import CAMPUS_TIME
    from app import create_app

    app = validator(create_app(tmp_path / "demo.sqlite3"))
    student = sign_in(app, "student-a")
    other_student = sign_in(app, "student-b")
    reviewer = sign_in(app, "reviewer-a")

    form = send(app, "/requests/new", cookie=student)
    assert form["status"] == 200
    assert "<form" in form["body"]

    today = datetime.now(CAMPUS_TIME).date()
    future_date = (today + timedelta(days=7)).isoformat()
    fields = {
        "stay_date": future_date,
        "start_time": "18:00",
        "expected_departure_time": "20:00",
        "building": "Synthetic Science Building",
        "room": "Room 101",
        "reason": "Group project meeting <test>",
    }
    invalid = send(
        app, "/requests/new", cookie=student,
        form={**fields, "stay_date": (today - timedelta(days=7)).isoformat()},
    )
    assert invalid["status"] == 400
    assert "Check stay date" in invalid["body"]
    assert "Group project meeting &lt;test&gt;" in invalid["body"]
    submission = send(app, "/requests/new", cookie=student, form=fields)
    assert submission["status"] == 303
    detail_path = submission["headers"]["Location"]
    assert detail_path.startswith("/requests/")
    reference = detail_path.rsplit("/", 1)[1]
    assert reference
    pending = send(app, detail_path, cookie=student)
    assert pending["status"] == 200
    assert "Pending Approval" in pending["body"]

    queue = send(app, "/facilities", cookie=reviewer)
    approval_path = f"/facilities/{reference}/approve"
    assert queue["status"] == 200
    assert approval_path in queue["body"]
    for detail in (future_date, "18:00", "20:00", "student-a", "Group project meeting &lt;test&gt;"):
        assert detail in queue["body"]
    get_approval = send(app, approval_path, cookie=reviewer)
    assert get_approval["status"] == 405
    assert get_approval["headers"]["Allow"] == "POST"
    assert send(app, approval_path, form={}, cookie=student)["status"] == 403
    assert "Pending Approval" in send(app, detail_path, cookie=student)["body"]
    assert send(app, approval_path, form={}, cookie=reviewer)["status"] == 303

    saved = send(app, detail_path, cookie=student)
    assert saved["status"] == 200
    assert "Approved" in saved["body"]
    assert "Pending Approval" not in saved["body"]
    assert reference in send(app, "/requests", cookie=student)["body"]
    assert send(app, detail_path, cookie=other_student)["status"] == 404
    assert reference not in send(app, "/requests", cookie=other_student)["body"]
    assert send(app, approval_path, form={}, cookie=reviewer)["status"] == 409


def test_reviewer_can_reject_pending_request_with_internal_reason(tmp_path):
    from after_hours import CAMPUS_TIME, get_request
    from app import create_app

    store_path = tmp_path / "demo.sqlite3"
    app = validator(create_app(store_path))
    student = sign_in(app, "student-a")
    reviewer = sign_in(app, "reviewer-a")
    submission = send(app, "/requests/new", cookie=student, form={
        "stay_date": (datetime.now(CAMPUS_TIME).date() + timedelta(days=7)).isoformat(),
        "start_time": "18:00",
        "expected_departure_time": "20:00",
        "building": "Science Building",
        "room": "Room 101",
        "reason": "Group project",
    })
    assert submission["status"] == 303
    detail_path = submission["headers"]["Location"]
    reference = detail_path.rsplit("/", 1)[1]
    reject_path = f"/facilities/{reference}/reject"
    queue = send(app, "/facilities", cookie=reviewer)["body"]
    assert reject_path in queue and "<button>Reject</button>" in queue

    reason = "Room unavailable"
    assert send(app, reject_path, cookie=reviewer)["status"] == 405
    assert send(app, reject_path, form={"reason": reason}, cookie=student)["status"] == 403
    assert send(app, reject_path, form={"reason": "  "}, cookie=reviewer)["status"] == 400
    assert "Pending Approval" in send(app, detail_path, cookie=student)["body"]
    assert send(app, reject_path, form={"reason": reason}, cookie=reviewer)["status"] == 303
    assert reject_path not in send(app, "/facilities", cookie=reviewer)["body"]
    detail = send(app, detail_path, cookie=student)["body"]
    assert "Rejected" in detail
    assert reason not in detail
    saved = get_request(store_path, reference)
    assert saved["rejection_reason"] == reason
    assert saved["decision_maker_id"] == "reviewer-a"
    assert send(app, reject_path, form={"reason": "Other reason"}, cookie=reviewer)["status"] == 409
