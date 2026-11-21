import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, date, time

def _get_db(store_path):
    conn = sqlite3.connect(store_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS requests (
                    reference TEXT PRIMARY KEY,
                    student_id TEXT,
                    submitted_at TIMESTAMP,
                    stay_date DATE,
                    start_time TIME,
                    expected_departure_time TIME,
                    building TEXT,
                    room TEXT,
                    reason TEXT,
                    status TEXT,
                    decision_maker_id TEXT,
                    decided_at TIMESTAMP,
                    rejection_reason TEXT,
                    parent_reference TEXT,
                    end_date DATE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS student_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT,
                    reference TEXT,
                    status TEXT
                )
                """
            )
            columns = {column[1] for column in conn.execute("PRAGMA table_info(requests)")}
            if "decision_maker_id" not in columns:
                conn.execute("ALTER TABLE requests ADD COLUMN decision_maker_id TEXT")
            if "decided_at" not in columns:
                conn.execute("ALTER TABLE requests ADD COLUMN decided_at TIMESTAMP")
            if "rejection_reason" not in columns:
                conn.execute("ALTER TABLE requests ADD COLUMN rejection_reason TEXT")
            if "parent_reference" not in columns:
                conn.execute("ALTER TABLE requests ADD COLUMN parent_reference TEXT")
            if "end_date" not in columns:
                conn.execute("ALTER TABLE requests ADD COLUMN end_date DATE")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS request_history (
                    reference TEXT,
                    actor_id TEXT,
                    decided_at TIMESTAMP,
                    from_status TEXT,
                    to_status TEXT,
                    old_room TEXT,
                    new_room TEXT
                )
                """
            )
            history_columns = {column[1] for column in conn.execute("PRAGMA table_info(request_history)")}
            if "old_room" not in history_columns:
                conn.execute("ALTER TABLE request_history ADD COLUMN old_room TEXT")
            if "new_room" not in history_columns:
                conn.execute("ALTER TABLE request_history ADD COLUMN new_room TEXT")
    except Exception:
        conn.close()
        raise
    return conn

def _validate_request(stay_date, start_time, expected_departure_time, room, reason):
    if not isinstance(room, str) or not room.strip():
        raise ValueError("room")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("reason")
    if expected_departure_time <= start_time:
        raise ValueError("expected_departure_time")
    
    if isinstance(stay_date, str):
        try:
            date.fromisoformat(stay_date)
        except ValueError:
            raise ValueError("stay_date")
    elif not isinstance(stay_date, date):
        raise ValueError("stay_date")

def submit_request(store_path, *, student_id, submitted_at, stay_date, start_time, expected_departure_time, building, room, reason):
    _validate_request(stay_date, start_time, expected_departure_time, room, reason)
    
    reference = str(uuid.uuid4())
    status = "Pending Approval"
    
    if isinstance(stay_date, str):
        stay_date_val = date.fromisoformat(stay_date)
    else:
        stay_date_val = stay_date
    
    conn = _get_db(store_path)
    conn.execute(
        "INSERT INTO requests (reference, student_id, submitted_at, stay_date, start_time, expected_departure_time, building, room, reason, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (reference, student_id, submitted_at.isoformat(), stay_date_val.isoformat(), 
         start_time.isoformat(), expected_departure_time.isoformat(), building, room, reason, status)
    )
    conn.commit()
    conn.close()
    
    return {"reference": reference, "status": status}

def get_request(store_path, reference):
    conn = _get_db(store_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM requests WHERE reference = ?", (reference,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    result = dict(row)
    # Convert back to types
    result["submitted_at"] = datetime.fromisoformat(result["submitted_at"])
    result["stay_date"] = date.fromisoformat(result["stay_date"])
    result["start_time"] = time.fromisoformat(result["start_time"])
    result["expected_departure_time"] = time.fromisoformat(result["expected_departure_time"])
    if result.get("decided_at"):
        result["decided_at"] = datetime.fromisoformat(result["decided_at"])
    
    return result

def submit_recurring_request(store_path, *, student_id, submitted_at, start_date, end_date, weekdays, start_time, expected_departure_time, building, room, reason):
    _validate_request(start_date, start_time, expected_departure_time, room, reason)
    if end_date < start_date:
        raise ValueError("Invalid range")
    weekdays = set(weekdays)
    if any(type(day) is not int or not 0 <= day <= 6 for day in weekdays):
        raise ValueError("Invalid weekday")
    if not weekdays:
        raise ValueError("Empty weekday selection")

    dates = []
    current = start_date
    while current <= end_date:
        if current.weekday() in weekdays:
            dates.append(current)
        if current == end_date:
            break
        current = date.fromordinal(current.toordinal() + 1)

    if not dates:
        raise ValueError("No matching date")

    parent_reference = str(uuid.uuid4())
    status = "Pending Approval"

    with closing(_get_db(store_path)) as conn, conn:
        # Parent row
        conn.execute(
            "INSERT INTO requests (reference, student_id, submitted_at, status, start_time, expected_departure_time, building, room, reason, stay_date, end_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (parent_reference, student_id, submitted_at.isoformat(), status, start_time.isoformat(), expected_departure_time.isoformat(), building, room, reason, start_date.isoformat(), end_date.isoformat())
        )
        # Occurrences
        for d in dates:
            conn.execute(
                "INSERT INTO requests (reference, student_id, submitted_at, stay_date, start_time, expected_departure_time, building, room, reason, status, parent_reference) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), student_id, submitted_at.isoformat(), d.isoformat(), start_time.isoformat(), expected_departure_time.isoformat(), building, room, reason, status, parent_reference)
            )
    return {"reference": parent_reference, "status": status}

def get_recurring_request(store_path, reference, *, student_id):
    conn = _get_db(store_path)
    conn.row_factory = sqlite3.Row
    parent = conn.execute("SELECT * FROM requests WHERE reference = ? AND student_id = ? AND end_date IS NOT NULL AND parent_reference IS NULL", (reference, student_id)).fetchone()
    if not parent:
        conn.close()
        return None

    occurrences = conn.execute("SELECT * FROM requests WHERE parent_reference = ? ORDER BY stay_date", (reference,)).fetchall()
    conn.close()

    res = dict(parent)
    res["start_date"] = date.fromisoformat(res["stay_date"])
    res["end_date"] = date.fromisoformat(res["end_date"])

    res_occurrences = []
    for occ in occurrences:
        o = dict(occ)
        o["stay_date"] = date.fromisoformat(o["stay_date"])
        o["start_time"] = time.fromisoformat(o["start_time"])
        o["expected_departure_time"] = time.fromisoformat(o["expected_departure_time"])
        res_occurrences.append(o)

    res["occurrences"] = res_occurrences
    return res

def list_pending_requests(store_path, *, actor_role):
    if actor_role != "facilities":
        raise PermissionError("Unauthorized")
    
    conn = _get_db(store_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM requests WHERE status = 'Pending Approval' AND parent_reference IS NULL AND end_date IS NULL")
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        result = dict(row)
        result["submitted_at"] = datetime.fromisoformat(result["submitted_at"])
        result["stay_date"] = date.fromisoformat(result["stay_date"])
        result["start_time"] = time.fromisoformat(result["start_time"])
        result["expected_departure_time"] = time.fromisoformat(result["expected_departure_time"])
        results.append(result)
    return results

def approve_request(store_path, reference, *, actor_role, actor_id, decided_at):
    if actor_role != "facilities":
        raise PermissionError("Unauthorized")
    
    conn = _get_db(store_path)
    
    cursor = conn.execute(
        "UPDATE requests SET status = 'Approved', decision_maker_id = ?, decided_at = ? "
        "WHERE reference = ? AND status = 'Pending Approval' AND parent_reference IS NULL AND end_date IS NULL",
        (actor_id, decided_at.isoformat(), reference),
    )
    
    if cursor.rowcount > 0:
        conn.execute(
            "INSERT INTO request_history (reference, actor_id, decided_at, from_status, to_status) "
            "VALUES (?, ?, ?, ?, ?)",
            (reference, actor_id, decided_at.isoformat(), "Pending Approval", "Approved")
        )
        # Fetch student_id from current row instead of reopening connection
        cursor = conn.execute("SELECT student_id FROM requests WHERE reference = ?", (reference,))
        student_id = cursor.fetchone()[0]
        conn.execute(
            "INSERT INTO student_notifications (student_id, reference, status) VALUES (?, ?, ?)",
            (student_id, reference, "Approved")
        )
        
    conn.commit()
    conn.close()

def cancel_request(store_path, reference, *, student_id, cancelled_at):
    if cancelled_at.utcoffset() is None:
        raise ValueError("Cancellation time must be timezone-aware")

    with closing(_get_db(store_path)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT student_id, status, stay_date, start_time FROM requests WHERE reference = ? AND parent_reference IS NULL AND end_date IS NULL",
            (reference,),
        ).fetchone()
        if row is None:
            return
        if row["student_id"] != student_id:
            raise PermissionError("Unauthorized")
        if row["status"] not in ("Pending Approval", "Approved"):
            return

        start = datetime.combine(
            date.fromisoformat(row["stay_date"]),
            time.fromisoformat(row["start_time"]),
            tzinfo=cancelled_at.tzinfo,
        )
        if cancelled_at >= start:
            raise ValueError("Cannot cancel at or after start time")

        conn.execute("UPDATE requests SET status = 'Cancelled' WHERE reference = ?", (reference,))
        conn.execute(
            "INSERT INTO request_history (reference, actor_id, decided_at, from_status, to_status) "
            "VALUES (?, ?, ?, ?, ?)",
            (reference, student_id, cancelled_at.isoformat(), row["status"], "Cancelled"),
        )


def reject_request(store_path, reference, *, actor_role, actor_id, decided_at, reason):
    if actor_role != "facilities":
        raise PermissionError("Unauthorized")
    
    conn = _get_db(store_path)
    cursor = conn.execute(
        "UPDATE requests SET status = 'Rejected', decision_maker_id = ?, decided_at = ?, rejection_reason = ? "
        "WHERE reference = ? AND status = 'Pending Approval' AND parent_reference IS NULL AND end_date IS NULL",
        (actor_id, decided_at.isoformat(), reason, reference),
    )
    
    if cursor.rowcount > 0:
        conn.execute(
            "INSERT INTO request_history (reference, actor_id, decided_at, from_status, to_status) "
            "VALUES (?, ?, ?, ?, ?)",
            (reference, actor_id, decided_at.isoformat(), "Pending Approval", "Rejected")
        )
        # Fetch student_id from current row instead of reopening connection
        cursor = conn.execute("SELECT student_id FROM requests WHERE reference = ?", (reference,))
        student_id = cursor.fetchone()[0]
        conn.execute(
            "INSERT INTO student_notifications (student_id, reference, status) VALUES (?, ?, ?)",
            (student_id, reference, "Rejected")
        )
        
    conn.commit()
    conn.close()

def edit_request_room(store_path, reference, *, student_id, room, edited_at):
    if not isinstance(room, str) or not room.strip():
        raise ValueError("room")
    if edited_at.utcoffset() is None:
        raise ValueError("Edit time must be timezone-aware")

    with closing(_get_db(store_path)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT student_id, room, status, stay_date, start_time FROM requests WHERE reference = ? AND parent_reference IS NULL AND end_date IS NULL",
            (reference,),
        ).fetchone()

        if row is None:
            return
        if row["student_id"] != student_id:
            raise PermissionError("Unauthorized")
        if row["status"] != "Pending Approval":
            return

        start = datetime.combine(
            date.fromisoformat(row["stay_date"]),
            time.fromisoformat(row["start_time"]),
            tzinfo=edited_at.tzinfo,
        )
        if edited_at >= start:
            raise ValueError("Edit at or after start")

        old_room = row["room"]
        conn.execute("UPDATE requests SET room = ? WHERE reference = ?", (room, reference))
        conn.execute(
            "INSERT INTO request_history (reference, actor_id, decided_at, from_status, to_status, old_room, new_room) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (reference, student_id, edited_at.isoformat(), "Pending Approval", "Pending Approval", old_room, room),
        )

def get_request_history(store_path, reference, *, actor_role):
    if actor_role != "facilities":
        raise PermissionError("Unauthorized")
        
    conn = _get_db(store_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM request_history WHERE reference = ?", (reference,)).fetchall()
    conn.close()
    
    results = []
    for row in rows:
        result = dict(row)
        result["decided_at"] = datetime.fromisoformat(result["decided_at"])
        results.append(result)
    return results

def list_student_notifications(store_path, *, student_id):
    conn = _get_db(store_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT reference, status FROM student_notifications WHERE student_id = ?", (student_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def list_student_requests(store_path, *, student_id):
    conn = _get_db(store_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM requests WHERE student_id = ? AND parent_reference IS NULL AND end_date IS NULL", (student_id,))
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        result = dict(row)
        result.pop("rejection_reason", None)
        result["submitted_at"] = datetime.fromisoformat(result["submitted_at"])
        result["stay_date"] = date.fromisoformat(result["stay_date"])
        result["start_time"] = time.fromisoformat(result["start_time"])
        result["expected_departure_time"] = time.fromisoformat(result["expected_departure_time"])
        results.append(result)
    return results

def get_student_request(store_path, reference, *, student_id):
    conn = _get_db(store_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM requests WHERE reference = ? AND student_id = ? AND parent_reference IS NULL AND end_date IS NULL", (reference, student_id))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    result = dict(row)
    result.pop("rejection_reason", None)
    result["submitted_at"] = datetime.fromisoformat(result["submitted_at"])
    result["stay_date"] = date.fromisoformat(result["stay_date"])
    result["start_time"] = time.fromisoformat(result["start_time"])
    result["expected_departure_time"] = time.fromisoformat(result["expected_departure_time"])
    
    return result
