import urllib.parse
from datetime import datetime, time, timezone
from http.cookies import SimpleCookie
from secrets import token_urlsafe
import after_hours
import html

def request_form(error=None):
    message = f'<p role="alert">{html.escape(error)}</p>' if error else ""
    return (
        '<h1>New after-hours request</h1>' + message +
        '<form method="POST">Date:<input type="date" name="stay_date"><br>Start:<input type="time" name="start_time"><br>End:<input type="time" name="expected_departure_time"><br>Bldg:<input name="building"><br>Room:<input name="room"><br>Reason:<input name="reason"><br><button>Submit</button></form>'
        '<p><a href="/requests">My Requests</a></p>'
    )


def create_app(store_path):
    accounts = {"student-a": "student", "student-b": "student", "reviewer-a": "facilities"}
    sessions = {}

    def app(environ, start_response):
        path = environ.get("PATH_INFO", "/")
        method = environ.get("REQUEST_METHOD", "GET")
        
        cookie = SimpleCookie(environ.get("HTTP_COOKIE", ""))
        session = cookie.get("session")
        user_id = sessions.get(session.value) if session else None
        role = accounts.get(user_id)

        if path == "/login":
            if method == "POST":
                size = int(environ.get("CONTENT_LENGTH", 0) or 0)
                data = urllib.parse.parse_qs(environ["wsgi.input"].read(size).decode())
                account = data.get("account", [""])[0]
                if account in accounts:
                    if session:
                        sessions.pop(session.value, None)
                    token = token_urlsafe(32)
                    sessions[token] = account
                    destination = "/facilities" if accounts[account] == "facilities" else "/requests"
                    start_response("303 See Other", [
                        ("Set-Cookie", f"session={token}; Path=/; HttpOnly; SameSite=Lax"),
                        ("Location", destination),
                        ("Content-Type", "text/html; charset=utf-8"),
                    ])
                    return [b""]
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return [b"""<h1>After-Hours Access</h1>
                <form method="post"><label>Demo account <select name="account">
                <option value="student-a">Student A</option>
                <option value="student-b">Student B</option>
                <option value="reviewer-a">Facilities reviewer</option>
                </select></label><button>Sign in</button></form>"""]

        if not user_id:
            start_response("302 Found", [("Location", "/login"), ("Content-Type", "text/html")])
            return [b""]

        if path == "/requests" or path.startswith("/requests/"):
            if role != "student":
                start_response("403 Forbidden", [("Content-Type", "text/html")])
                return [b"Forbidden"]

        if path == "/requests/new" and method == "GET":
            start_response("200 OK", [("Content-Type", "text/html")])
            return [request_form().encode()]

        if path == "/requests/new" and method == "POST":
            size = int(environ.get("CONTENT_LENGTH", 0) or 0)
            data = urllib.parse.parse_qs(environ["wsgi.input"].read(size).decode())
            field = "start_time"
            try:
                start = time.fromisoformat(data.get(field, [""])[0])
                field = "expected_departure_time"
                end = time.fromisoformat(data.get(field, [""])[0])
                if not data.get("building", [""])[0].strip():
                    raise ValueError("building")
                res = after_hours.submit_request(
                    store_path,
                    student_id=user_id,
                    submitted_at=datetime.now(timezone.utc),
                    stay_date=data.get("stay_date", [""])[0],
                    start_time=start,
                    expected_departure_time=end,
                    building=data.get("building", [""])[0],
                    room=data.get("room", [""])[0],
                    reason=data.get("reason", [""])[0],
                )
                start_response("303 See Other", [("Location", f"/requests/{res['reference']}"), ("Content-Type", "text/html")])
                return [b""]
            except ValueError as error:
                known_fields = {"stay_date", "building", "room", "reason", "expected_departure_time"}
                invalid = str(error) if str(error) in known_fields else field
                start_response("400 Bad Request", [("Content-Type", "text/html")])
                return [request_form(f"Check {invalid.replace('_', ' ')} and try again.").encode()]

        if path.startswith("/requests/"):
            parts = path.split("/")
            if len(parts) > 2:
                ref = parts[2]
                req = after_hours.get_student_request(store_path, ref, student_id=user_id)
                if not req:
                    start_response("404 Not Found", [("Content-Type", "text/html")])
                    return [b"Not found"]
                start_response("200 OK", [("Content-Type", "text/html")])
                return [f'<h1>Request {html.escape(ref)}</h1><p>Status: {html.escape(req["status"])}</p>'
                        '<a href="/requests">My Requests</a> | <a href="/login">Switch account</a>'.encode()]

        if path == "/requests":
            reqs = after_hours.list_student_requests(store_path, student_id=user_id)
            links = "".join(
                f'<li><a href="/requests/{r["reference"]}">{r["reference"]}</a> '
                f'{html.escape(r["status"])}</li>' for r in reqs
            )
            body = ('<h1>My Requests</h1><a href="/requests/new">New request</a> | '
                    f'<a href="/login">Switch account</a><ul>{links}</ul>').encode()
            start_response("200 OK", [("Content-Type", "text/html")])
            return [body]

        if path == "/facilities":
            if role != "facilities":
                start_response("403 Forbidden", [("Content-Type", "text/html")])
                return [b"Forbidden"]
            reqs = after_hours.list_pending_requests(store_path, actor_role=role)
            forms = "".join(
                f'<form method="post" action="/facilities/{r["reference"]}/approve">'
                f'<p>{r["reference"]}: {html.escape(r["building"])} / {html.escape(r["room"])} '
                f'<button>Approve</button></p></form>' for r in reqs
            )
            body = ('<h1>Facilities pending requests</h1><a href="/login">Switch account</a>'
                    + (forms or "<p>No pending requests.</p>")).encode()
            start_response("200 OK", [("Content-Type", "text/html")])
            return [body]

        if path.startswith("/facilities/") and path.endswith("/approve"):
            ref = path.split("/")[2]
            if role != "facilities":
                start_response("403 Forbidden", [("Content-Type", "text/html")])
                return [b"Forbidden"]
            if method != "POST":
                start_response("405 Method Not Allowed", [("Allow", "POST"), ("Content-Type", "text/html")])
                return [b"Use the approval form."]
            after_hours.approve_request(store_path, ref, actor_role=role, actor_id=user_id, decided_at=datetime.now(timezone.utc))
            start_response("303 See Other", [("Location", "/facilities"), ("Content-Type", "text/html")])
            return [b""]

        start_response("404 Not Found", [("Content-Type", "text/html")])
        return [b"Not found"]
    return app

if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    app = create_app("demo.sqlite3")
    httpd = make_server("127.0.0.1", 8000, app)
    print("Open http://127.0.0.1:8000/login", flush=True)
    httpd.serve_forever()
