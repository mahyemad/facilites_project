import sqlite3
import uuid
from datetime import datetime, date, time

def _get_db(store_path):
    conn = sqlite3.connect(store_path)
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
            status TEXT
        )
        """
    )
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
    
    # Ensure stay_date is a date object for database insertion
    # The test passes '2026-02-30' (string) when testing invalid dates,
    # but the logic above validates it. For normal cases it's a date object.
    if isinstance(stay_date, str):
        stay_date_val = date.fromisoformat(stay_date)
    else:
        stay_date_val = stay_date
    
    conn = _get_db(store_path)
    conn.execute(
        "INSERT INTO requests VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
    
    return result
