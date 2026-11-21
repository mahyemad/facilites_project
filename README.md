# Facilities Project · After-Hours Access

The Deliverable 1 demo covers a single-day after-hours request. A student submits a request, a Facilities reviewer approves it, and the student sees the saved decision in My Requests. The local demo uses synthetic accounts and SQLite.

## Run the demo

From the repository root, run the following with Python 3.9 or newer. The app uses the Python standard library.

```sh
python3 app.py
```

Open [After-Hours Access](http://127.0.0.1:8000/login). The server listens on your computer and saves requests to `demo.sqlite3` in the current directory. A fresh checkout starts with an empty database. Use **Ctrl+C** to stop the server.

1. Sign in as **Student A** and select **New request**. Enter a future date, start and departure times, a building, a room, and a reason. Submit the form and confirm the status is **Pending Approval**.
2. Select **Switch account**, sign in as **Facilities reviewer**, and expand the request in the pending queue, review the details, and approve it.
3. Switch back to **Student A** and open the request in **My Requests**. Confirm the status is **Approved**.
4. Switch to **Student B** to check that the request is absent from their list. Opening Student A's request URL as Student B returns **404**.

## Run the checks

From the repository root, install pytest in a virtual environment and run the checks.

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install pytest
python3 -m pytest -q tests acceptance/ah_t*.py
```

The full command runs 29 checks. To run the 12 checks for the D1 demo and its supporting service, use:

```sh
python3 -m pytest -q tests
```

Both suites use temporary SQLite databases and synthetic records. The browser workflow check exercises the app's HTTP interface without starting a server.

## Scope and project files

- The browser demo covers submission, validation, review, approval, and owner-only request access. Approval records the reviewer, time, and status change.
- The service also supports rejection, private decision notifications, cancellation, pending-request room edits, and recurring stays. Their browser controls are pending. The approval policy for recurring requests and the same-day submission policy are open. The demo rejects past calendar dates and uses Africa/Cairo for campus schedules and newly recorded timestamps.
- `app.py` contains the local demo. `after_hours.py` handles the SQLite service.
- The [D1 task specs](D1-After-Hours-Tasks.md) trace each task to a requirement and list its acceptance check. The [D1 agent work log](D1-Agent-Work-Log.md) records the Lab 6 work, review outcomes, and usage.
