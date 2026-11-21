import sqlite3
import uuid
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
                    decided_at TIMESTAMP
                )
                """
            )
            columns = {column[1] for column in conn.execute("PRAGMA table_info(requests)")}
            if "decision_maker_id" not in columns:
                conn.execute("ALTER TABLE requests ADD COLUMN decision_maker_id TEXT")
            if "decided_at" not in columns:
                conn.execute("ALTER TABLE requests ADD COLUMN decided_at TIMESTAMP")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS request_history (
                    reference TEXT,
                    actor_id TEXT,
                    decided_at TIMESTAMP,
                    from_status TEXT,
                    to_status TEXT
                )
                """
            )
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

def list_pending_requests(store_path, *, actor_role):
    if actor_role != "facilities":
        raise PermissionError("Unauthorized")
    
    conn = _get_db(store_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM requests WHERE status = 'Pending Approval'")
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
        "WHERE reference = ? AND status = 'Pending Approval'",
        (actor_id, decided_at.isoformat(), reference),
    )
    
    if cursor.rowcount > 0:
        conn.execute(
            "INSERT INTO request_history VALUES (?, ?, ?, ?, ?)",
            (reference, actor_id, decided_at.isoformat(), "Pending Approval", "Approved")
        )
        
    conn.commit()
    conn.close()

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

def list_student_requests(store_path, *, student_id):
    conn = _get_db(store_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM requests WHERE student_id = ?", (student_id,))
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

def get_student_request(store_path, reference, *, student_id):
    conn = _get_db(store_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM requests WHERE reference = ? AND student_id = ?", (reference, student_id))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    result = dict(row)
    result["submitted_at"] = datetime.fromisoformat(result["submitted_at"])
    result["stay_date"] = date.fromisoformat(result["stay_date"])
    result["start_time"] = time.fromisoformat(result["start_time"])
    result["expected_departure_time"] = time.fromisoformat(result["expected_departure_time"])
    
    return result
