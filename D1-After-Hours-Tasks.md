# Deliverable 1 · After-Hours Access task specs

Source: [After-Hours Access Management Requirements](After_Hours_Access_Management_Requirements.pdf). The IDs below are assigned for this project. Must and Should are proposed backlog priorities based on the module draft.

**D1 vertical slice:** A student submits a single-day request, authorized Facilities staff approve it, and the student sees the saved decision. Tasks AH-T01 through AH-T05 make up the slice. AH-T06 through AH-T10 are specified for the backlog.

**Acceptance test convention:** File names below are suggested paths by responsibility because the workspace currently contains only PDFs. Each check specifies the fixture, action, and assertions for one automated acceptance scenario. `./scripts/check-after-hours AH-T01` illustrates the proposed runner interface for an individual task and `./scripts/check-after-hours` is the proposed clean-checkout command for the implemented D1 slice. The runnable AH-T01 through AH-T05 service checks are linked below. The shared runner and remaining automated checks are pending. Use synthetic student and Facilities accounts, a synthetic campus location, and a fixed test clock in the university's local time zone.

| Requirement | Priority | Expected behavior | Source section |
| --- | --- | --- | --- |
| AH-R01 | Must | Authenticated students submit single-day requests with account-derived identity, schedule, building and room or area, and reason. Each request receives a unique reference and starts pending. | §§3–4, 7A, 13 |
| AH-R02 | Must | Validate required fields and reject invalid dates and time ranges. | §§4, 13 |
| AH-R03 | Must | Authorized Facilities staff can review and approve pending requests. | §§3, 6, 10 |
| AH-R04 | Must | Students can view their own request history and decision status. Access is restricted by role and ownership. | §§5, 10, 13 |
| AH-R05 | Must | Record the decision maker and decision time and retain a history of staff actions. | §§6, 13 |
| AH-R06 | Must | Authorized Facilities staff can reject pending requests. | §§6, 8, 10 |
| AH-R07 | Must | Students receive acknowledgement on submission and a notification after a decision. | §11 |
| AH-R08 | Must | Students can cancel their own requests before the stay begins. | §§3, 5, 7C, 10 |
| AH-R09 | Must | Students can edit their own upcoming requests. Changes are auditable. | §§3, 7C, 10, 13 |
| AH-R10 | Should | Students can request recurring dates using a range and selected weekdays, with separate occurrences. The draft makes recurrence conditional for the initial release. | §§3–5, 7B, 15 |

## D1 vertical slice

### AH-T01 — Submit and save a single-day request · AH-R01

- **Goal** — Provide a student form and persist the submitted request with identity from the signed-in account, a unique reference, a timestamp, and the status Pending Approval.
- **Likely files** — `after-hours/student-form`, `after-hours/requests`, `db/after-hours`, `tests/acceptance/after-hours`.
- **Out of scope** — University identity integration for the prototype, recurring dates, and notifications.
- **Acceptance check** — Sign in as synthetic Student A and submit a future date, 18:00–20:00, a building and room, and a reason. Assert the receipt shows a reference and Pending Approval. Read the saved record and assert the reference, account-derived owner, location, hours, reason, and submission timestamp. Submit a second valid request for a distinct date and assert it receives a different reference.

- **Run the service check** — `python3 -m pytest -q tests/test_after_hours.py` from the repository root. The check exercises submission and persistence. Browser form and signed-in identity wiring will be exercised in the full slice.
- **Service interface for the lab agent** — Provide `after_hours.py` with `submit_request(store_path, *, student_id, submitted_at, stay_date, start_time, expected_departure_time, building, room, reason)` and `get_request(store_path, reference)`. Return a mapping with `reference` and `status` from submission. The retrieved mapping includes these and the submitted fields. Use the authenticated account ID when the form is wired to this service. Use a file-backed SQLite store and preserve Python date, time, and timezone-aware datetime values at the service boundary.

### AH-T02 — Validate a request before saving · AH-R02

- **Goal** — Reject missing required fields and invalid dates or time ranges on the server and show actionable errors on the form.
- **Likely files** — `after-hours/student-form`, `after-hours/request-validation`, `tests/acceptance/after-hours`.
- **Out of scope** — Same-day submission policy, overnight stays, and overlap policy.
- **Acceptance check** — For an otherwise valid request, omit the room, omit the reason, supply a nonexistent date, and reverse same-day start and end times in separate submissions. Assert a field error for each case and verify that none creates a record.

- **Run the service check** — `python3 -m pytest -q tests/test_after_hours.py` from the repository root. This also runs the AH-T01 regression check.
- **Service contract** — For invalid submissions, raise `ValueError` with the failing field name in the message before inserting a row. The test uses empty or whitespace-only text for missing fields, `"2026-02-30"` as an invalid date input, and an earlier departure time. Preserve the AH-T01 interface for valid inputs. Form error display comes with the browser form.

### AH-T03 — Review and approve a pending request · AH-R03

- **Goal** — Show pending requests in a Facilities review queue and allow authorized staff to approve one from its details.
- **Likely files** — `after-hours/facilities-queue`, `after-hours/decisions`, `tests/acceptance/after-hours`.
- **Out of scope** — Rejection, queue filters, and recurring approvals.
- **Acceptance check** — Submit a request as Student A, open it from the pending queue as Facilities staff, and approve it. Reload and assert it is Approved and absent from the pending queue. Attempt approval of a separate pending request as Student A and assert access is denied and the request remains pending.

- **Run the service check** — `python3 -m pytest -q tests/test_after_hours.py`. The service check uses synthetic roles. The Facilities browser queue and session-derived staff role come with the app.
- **Service contract** — Add `list_pending_requests(store_path, *, actor_role)` and `approve_request(store_path, reference, *, actor_role, actor_id, decided_at)` in `after_hours.py`. Return pending request mappings from the list and persist an Approved status on approval. In these service tests, `"facilities"` is the authorized role and `"student"` is denied both operations with `PermissionError`. The future app must derive the role from the authenticated session.

### AH-T04 — Show the owner's saved decision · AH-R04

- **Goal** — Show the student's request and current status in My Requests and enforce ownership on both list and detail reads.
- **Likely files** — `after-hours/my-requests`, `after-hours/requests`, `tests/acceptance/after-hours`.
- **Out of scope** — Notifications and administrative reporting.
- **Acceptance check** — As Student A, submit a request and see Pending Approval in My Requests. Approve it as Facilities, sign back in as A, and assert the same reference now shows Approved after reload. Sign in as Student B and assert A's request is absent from the list and its direct detail URL returns no request data.

- **Run the service check** — `python3 -m pytest -q tests/test_after_hours.py`. The browser view and authenticated session come with the app.
- **Service contract** — Add `list_student_requests(store_path, *, student_id)` and `get_student_request(store_path, reference, *, student_id)`. Return only records owned by the supplied student ID, with the current saved status. Return `None` from the detail function for unknown references and references owned by another student. The app must supply the signed-in student's ID from the session. Preserve the existing internal service functions.

### AH-T05 — Audit a Facilities approval · AH-R05

- **Goal** — Save the approving staff identity and decision time with the approval and retain the status transition in history.
- **Likely files** — `after-hours/decisions`, `after-hours/history`, `db/after-hours`, `tests/acceptance/after-hours`.
- **Out of scope** — Audit export and analytics.
- **Acceptance check** — Approve a pending request as a synthetic Facilities reviewer at a fixed test time. Read the saved decision and history. Assert the reviewer, timestamp, request reference, previous status Pending Approval, and new status Approved match the action.

- **Run the service check** — `python3 -m pytest -q tests/test_after_hours.py`.
- **Service contract** — Extend approval to accept the reviewer's `actor_id` and a timezone-aware `decided_at`. After a successful pending-to-approved transition, `get_request` returns `decision_maker_id` and `decided_at`. Add `get_request_history(store_path, reference, *, actor_role)` for Facilities only. Return event mappings with `reference`, `actor_id`, `decided_at`, `from_status`, and `to_status`. Save the decision and event in one database transaction. Duplicate approval attempts must preserve the first decision and create no extra event. Existing SQLite databases must retain their requests when upgraded.

### AH-BROWSER — Connect the D1 browser workflow · AH-R01 through AH-R05

- **Goal** — Build a local-only demo with Python's standard library. Use server-rendered HTML, the existing SQLite service, and three synthetic demo accounts. Supply sign-in and account-switch controls so a reviewer can complete the flow manually.
- **Files** — Implement `app.py` with `create_app(store_path)` returning a WSGI app. Make `python3 app.py` start the app on loopback. Verify with `python3 -m pytest -q`.
- **Routes** — Provide a sign-in page at GET `/login` and select an account at POST `/login` using the `account` field. Use `student-a`, `student-b`, and `reviewer-a`. Set a session cookie and respond with 303. Derive user ID and role from the session. Use GET and POST `/requests/new` for the student form, redirect successful submissions with 303 to `/requests/<reference>`, and show the owner’s list at GET `/requests`. At GET `/facilities`, show the pending queue with a form posting to `/facilities/<reference>/approve`. Give successful approvals a 303 response. Use the signed-in reviewer's ID and a timezone-aware server timestamp. Return 403 for a student's approval attempt and 404 when a student requests another student's record.
- **Form fields** — `stay_date`, `start_time`, `expected_departure_time`, `building`, `room`, and `reason`. Validate on the server and redisplay field errors. Show a reference and explicit status. Escape user-supplied content in HTML and render useful links for navigating between the applicable pages.
- **Out of scope** — University authentication, production deployment, recurring requests, and departure tracking.
- **Implementation notes** — For WSGI compliance include a Content-Type header on redirects. Parse form times into Python time objects before calling the service. Use an opaque random session token with a server-side account lookup, then use the existing owner-scoped service functions. Protect approval with a POST form and give the reviewer a direct link to the pending queue.
- **Acceptance check** — `python3 -m pytest -q tests/test_after_hours_app.py` exercises separate browser sessions. The owner submits a request, the reviewer approves it, and the owner sees Approved. A second student cannot access the record.

## Additional backlog tasks

### AH-T06 — Reject a pending request · AH-R06

- **Goal** — Give Facilities a rejection action that records a reason and shows Rejected to the request owner.
- **Likely files** — `after-hours/facilities-queue`, `after-hours/decisions`, `after-hours/my-requests`, `tests/acceptance/after-hours`.
- **Out of scope** — Rejection reason categories and the policy for when reasons must appear to students.
- **Acceptance check** — Reject a pending request as Facilities with a synthetic reason. Assert the persisted decision contains the reason, reviewer, and timestamp, and the owner sees Rejected. Attempt rejection on a separate pending request as a student and assert it remains pending.

### AH-T07 — Acknowledge submissions and notify students of decisions · AH-R07

- **Goal** — Acknowledge submission with its reference and deliver a private status notification when Facilities approves or rejects a request. Use in-app delivery for the prototype.
- **Likely files** — `after-hours/requests`, `after-hours/decisions`, `notifications`, `tests/acceptance/after-hours`.
- **Out of scope** — Email, reminders, and rejection reason disclosure policy.
- **Acceptance check** — Submit two requests as Student A and assert each acknowledgement includes its reference. Approve one and reject the other as Facilities. Assert Student A receives an in-app notification for each decision with the correct reference and status, and Student B has neither notification.

### AH-T08 — Cancel an upcoming request · AH-R08

- **Goal** — Allow the owner to cancel their own request before the scheduled start and record the action.
- **Likely files** — `after-hours/my-requests`, `after-hours/cancellations`, `after-hours/history`, `tests/acceptance/after-hours`.
- **Out of scope** — Cancelling individual occurrences and staff override policy.
- **Acceptance check** — As Student A, cancel A's future request and assert Cancelled plus a history entry with A as actor. Attempt to cancel another student's future request and A's own already-started request, and assert both statuses stay unchanged.

### AH-T09 — Edit an upcoming pending request · AH-R09

- **Goal** — Allow the owner to edit a pending request before its start, validate the change, and save the prior and new values in history.
- **Likely files** — `after-hours/my-requests`, `after-hours/request-validation`, `after-hours/history`, `tests/acceptance/after-hours`.
- **Out of scope** — Edits to approved requests until Facilities confirms the reapproval policy, and edits to recurring series.
- **Acceptance check** — As Student A, change the room on A's future pending request. Assert its reference and pending status are preserved, the new room appears after reload, and history contains both rooms, actor, and timestamp. Attempt the change as Student B and on an already-started request as its owner, and assert the original room is preserved in both cases.

### AH-T10 — Create recurring stay occurrences · AH-R10

- **Goal** — Save one parent request and a separate pending occurrence for each selected weekday within the submitted date range.
- **Likely files** — `after-hours/student-form`, `after-hours/recurrence`, `db/after-hours`, `tests/acceptance/after-hours`.
- **Out of scope** — Series versus occurrence approval policy, actual departure records, and Security integration.
- **Acceptance check** — Submit a range from Monday 7 December through Monday 14 December 2026 inclusive, selecting Mondays and Wednesdays. Assert that exactly three distinct occurrences exist for 7, 9, and 14 December under one parent request. Assert each occurrence retains the submitted location and hours and appears separately in the student's view.
