import sqlite3
import threading
import json
from typing import Tuple, List, Dict, Any

DB_FILE = "AUBus.db"  # Database file name
db_lock = threading.RLock()  # Reentrant lock prevents nested DB operations from deadlocking

 
def init_db():
    """Create the users table if it doesn't exist."""
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()

        # Create user table storing all user details
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,                          -- unique username
            name TEXT NOT NULL,                                 -- full name
            email TEXT UNIQUE,                                  -- unique email
            password TEXT NOT NULL,                             -- hashed password
            area TEXT,                                          -- area / location
            is_driver INTEGER NOT NULL DEFAULT 0,               -- 1 = driver, 0 = passenger
            min_passenger_rating REAL NOT NULL DEFAULT 0.0,     -- minimum rating allowed for passengers

            driver_rating REAL NOT NULL DEFAULT 5.0,            -- driver's rating average
            driver_rating_count INTEGER NOT NULL DEFAULT 1,     -- driver rating count
            pending_requests TEXT NOT NULL DEFAULT '[]',        -- JSON list of pending ride requests
            passenger_rating REAL NOT NULL DEFAULT 5.0,         -- passenger rating average
            passenger_rating_count INTEGER NOT NULL DEFAULT 1,  -- passenger rating count
    
            mon_commute TEXT DEFAULT '[]',
            tue_commute TEXT DEFAULT '[]',
            wed_commute TEXT DEFAULT '[]',
            thu_commute TEXT DEFAULT '[]',
            fri_commute TEXT DEFAULT '[]',
            sat_commute TEXT DEFAULT '[]',
            sun_commute TEXT DEFAULT '[]',                      -- daily commute schedules stored as JSON arrays
            active_rides TEXT NOT NULL DEFAULT '[]',
            completed_rides TEXT NOT NULL DEFAULT '[]'
        )
        """)

        conn.commit()  # Save changes

    ensure_extra_columns()
    ensure_messages_table()


def ensure_extra_columns():
    """Ensure new columns exist for active/completed rides."""
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in c.fetchall()]
        if "active_rides" not in columns:
            c.execute("ALTER TABLE users ADD COLUMN active_rides TEXT NOT NULL DEFAULT '[]'")
        if "completed_rides" not in columns:
            c.execute("ALTER TABLE users ADD COLUMN completed_rides TEXT NOT NULL DEFAULT '[]'")
        conn.commit()


def ensure_messages_table():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS ride_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ride_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            recipient TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()


def register_user(
    username: str,
    name: str,
    email: str,
    password: str,
    area: str = None,
    is_driver: int = 0,
    min_passenger_rating: float = 0.0,
    commute_schedule: Dict[str, List[List[str]]] = None
) -> str:
    """Register a new user. Drivers may have commute schedules; passengers do not."""

    # List of days to ensure schedules cover all
    days = [
        "mon_commute", "tue_commute", "wed_commute",
        "thu_commute", "fri_commute", "sat_commute", "sun_commute"
    ]

    with db_lock:  # Lock DB to avoid race conditions
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()

                # If passenger → no commute schedule & no rating filter
                if is_driver != 1:
                    commute_schedule = {d: [] for d in days}  # empty list for each day
                    min_passenger_rating = 0.0
                else:
                    # Ensure schedule dict exists for all days
                    if commute_schedule is None:
                        commute_schedule = {d: [] for d in days}
                    else:
                        for d in days:
                            commute_schedule.setdefault(d, [])

                # Convert schedule dictionaries into JSON strings
                commute_values = [json.dumps(commute_schedule[d]) for d in days]

                # Insert the new user into the database
                c.execute("""
                INSERT INTO users (
                    username, name, email, password, area, is_driver,
                    min_passenger_rating,
                    driver_rating, driver_rating_count,
                    passenger_rating, passenger_rating_count,
                    mon_commute, tue_commute, wed_commute, thu_commute,
                    fri_commute, sat_commute, sun_commute,
                    active_rides, completed_rides
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    username, name, email, password, area, is_driver,
                    float(min_passenger_rating),
                    5.0, 1,            # driver rating + count
                    5.0, 1,            # passenger rating + count
                    *commute_values,   # unpack commute schedule JSON
                    "[]", "[]"
                ))

                conn.commit()  # Save DB

            return "User registered successfully."

        except sqlite3.IntegrityError as e:  # duplicate username or email
            if "UNIQUE" in str(e):
                return "Username or email already exists."
            return f"Database error: {e}"

        except sqlite3.Error as e:  # generic SQLite error
            return f"Database error: {e}"


def _normalize_commute_entry(raw_value):
    """Convert stored commute JSON into a dict with 'from'/'to' keys."""
    if not raw_value or raw_value == "[]":
        return {"from": None, "to": None}

    try:
        data = json.loads(raw_value)
    except json.JSONDecodeError:
        return {"from": None, "to": None}

    if isinstance(data, dict):
        return {"from": data.get("from"), "to": data.get("to")}

    if isinstance(data, list):
        from_time = data[0] if len(data) > 0 else None
        to_time = data[1] if len(data) > 1 else None
        return {"from": from_time, "to": to_time}

    return {"from": None, "to": None}


def login_user(username: str, password: str) -> str:
    """Validate username/password and return packed user info."""

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()

        # Retrieve user info
        c.execute("""
        SELECT *
        FROM users WHERE username=?
        """, (username,))

        row = c.fetchone()

        # User does not exist
        if not row:
            return "error:User not found."

        (username_db, name, email, stored_pw, area, is_driver,
         min_passenger_rating,
         driver_rating, driver_rating_count, pending_requests,
         passenger_rating, passenger_rating_count,
         mon_commute, tue_commute, wed_commute, thu_commute,
            fri_commute, sat_commute, sun_commute, active_rides_json, completed_rides_json) = row

        # Password incorrect
        if stored_pw != password:
            return "error:Incorrect password."

        try:
            pending_list = json.loads(pending_requests or "[]")
        except json.JSONDecodeError:
            pending_list = []

        day_map = [
            ("Mon", mon_commute),
            ("Tue", tue_commute),
            ("Wed", wed_commute),
            ("Thu", thu_commute),
            ("Fri", fri_commute),
            ("Sat", sat_commute),
            ("Sun", sun_commute),
        ]

        availability = {day: _normalize_commute_entry(raw) for day, raw in day_map}

        try:
            active_rides = json.loads(active_rides_json or "[]")
        except json.JSONDecodeError:
            active_rides = []

        try:
            completed_rides = json.loads(completed_rides_json or "[]")
        except json.JSONDecodeError:
            completed_rides = []

        payload = {
            "username": username_db,
            "name": name,
            "email": email,
            "area": area,
            "is_driver": bool(is_driver),
            "min_passenger_rating": min_passenger_rating,
            "driver_rating": driver_rating,
            "passenger_rating": passenger_rating,
            "pending_requests": pending_list,
            "availability": availability,
            "active_rides": active_rides,
            "completed_rides": completed_rides
        }

        # Return JSON payload to client
        return "success:" + json.dumps(payload)


def get_user_display_name(username: str) -> str:
    """Return the stored full name for a username (falling back to username)."""
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM users WHERE username=?", (username,))
        row = c.fetchone()
        if row and row[0]:
            return row[0]
    return username


def edit_fields(username: str, fields: Dict[str, Any]) -> str:
    """Update specific user fields (except ratings)."""

    if not fields:
        return "No fields provided to update."

    # List of editable columns
    valid_columns = {
        "name", "password", "area", "is_driver", "min_passenger_rating",
        "mon_commute", "tue_commute", "wed_commute",
        "thu_commute", "fri_commute", "sat_commute", "sun_commute"
    }

    # Only keep valid fields
    updates = {k: v for k, v in fields.items() if k in valid_columns}

    if not updates:
        return "No valid fields to update."

    # Convert commute schedule lists to JSON strings
    for d in updates:
        if "commute" in d:
            updates[d] = json.dumps(updates[d])

    # Build SQL SET clause
    set_clause = ", ".join(f"{k}=?" for k in updates)

    # Build value list for SQL
    values = list(updates.values()) + [username]

    with db_lock:  # Lock DB for safety
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()

                # Update user
                c.execute(f"UPDATE users SET {set_clause} WHERE username=?", values)
                conn.commit()

                # If no rows were affected → user does not exist
                if c.rowcount == 0:
                    return "User not found."

                return "User updated successfully."

        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e):  # email already used
                return "Email already exists."
            return f"Database error: {e}"

        except sqlite3.Error as e:  # generic DB error
            return f"Database error: {e}"


def search_valid_drivers(area: str, day: str, time: str, min_rating: float = 0.0):
    """Find drivers in an area who have a commute time that exactly matches the given time."""

    valid_days = [
        "mon_commute", "tue_commute", "wed_commute",
        "thu_commute", "fri_commute", "sat_commute", "sun_commute"
    ]

    if day not in valid_days:
        return "Invalid day provided."

    with db_lock:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()

                # Query drivers in the area who allow passengers with >= min_rating
                c.execute(f"""
                SELECT username, name, area, {day}, min_passenger_rating
                FROM users
                WHERE is_driver = 1
                  AND area = ?
                  AND min_passenger_rating <= ?
                """, (area, min_rating))

                matched_drivers = []

                for username, name, ar, commute_json, req_rating in c.fetchall():
                    # Parse commute JSON safely
                    try:
                        commute_data = json.loads(commute_json or "[]")
                    except:
                        commute_data = []

                    #
                    # ---- Normalize commute data into a flat list of expected-times ----
                    #
                    commute_times = []

                    # Case 1: stored as a single object {"from": "...", "to": "..."}
                    if isinstance(commute_data, dict):
                        if "from" in commute_data:
                            commute_times.append(commute_data["from"])
                        if "to" in commute_data:
                            commute_times.append(commute_data["to"])

                    # Case 2: stored as a list
                    elif isinstance(commute_data, list):
                        for entry in commute_data:

                            # ["08:00", "20:00"] format
                            if isinstance(entry, list) and len(entry) == 2:
                                commute_times.extend(entry)

                            # {"from": "...", "to": "..."} format
                            elif isinstance(entry, dict):
                                if "from" in entry:
                                    commute_times.append(entry["from"])
                                if "to" in entry:
                                    commute_times.append(entry["to"])

                    #
                    # ---- Check if requested time EXACTLY matches any commute time ----
                    #
                    if time in commute_times:
                        matched_drivers.append({
                            "username": username,
                            "name": name,
                            "area": ar,
                            "min_passenger_rating": req_rating,
                            "commute_times": commute_times
                        })

                return "No valid drivers found." if not matched_drivers else matched_drivers

        except sqlite3.Error as e:
            return f"Database error: {e}"


def calculate_rating(current: float, count: int, new: float) -> Tuple[float, int]:
    """Recalculate average rating given a new rating input."""
    new = max(0.0, min(5.0, float(new)))  # clamp rating to 0–5
    total = current * count               # sum of previous ratings

    count += 1                            # increment rating count
    updated = (total + new) / count       # compute new average

    return round(updated, 2), count       # return updated values


def _rate_user(username: str, new_rating: float, role: str) -> str:
    """Internal helper to rate a driver or passenger."""

    rating_col = f"{role}_rating"               # column storing rating value
    count_col = f"{role}_rating_count"          # column storing rating count

    with db_lock:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()

                # Fetch current rating and count
                c.execute(f"""
                SELECT {rating_col}, {count_col}
                FROM users
                WHERE username=?
                """, (username,))

                row = c.fetchone()

                # User not found
                if not row:
                    return "User not found."

                current, count = row

                # Recalculate rating
                new_avg, new_count = calculate_rating(current, count, new_rating)

                # Update the database with new rating
                c.execute(f"""
                UPDATE users
                SET {rating_col} = ?, {count_col} = ?
                WHERE username = ?
                """, (new_avg, new_count, username))

                conn.commit()

                return f"{role.capitalize()} rating updated."

        except sqlite3.Error as e:  # DB error
            return f"Database error: {e}"


def rate_driver(username: str, new_rating: float) -> str:
    """Public function to rate a driver."""
    return _rate_user(username, new_rating, "driver")


def rate_passenger(username: str, new_rating: float) -> str:
    """Public function to rate a passenger."""
    return _rate_user(username, new_rating, "passenger")


def get_pending_requests(driver_username: str):
    """Return the list of pending ride requests for the given driver."""

    with db_lock:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()

                # Get pending requests JSON
                c.execute(
                    "SELECT pending_requests, is_driver FROM users WHERE username=?",
                    (driver_username,),
                )
                row = c.fetchone()

                # User not found
                if not row:
                    return "Driver not found."

                pending_json, is_driver = row

                # Not a driver
                if not is_driver:
                    return "User is not registered as a driver."

                # Return parsed JSON list
                try:
                    return json.loads(pending_json or "[]")
                except json.JSONDecodeError:
                    return []

        except sqlite3.Error as e:  # DB error
            return f"Database error: {e}"


def add_pending_request(driver_username: str, request: dict) -> str:
    """Append a pending ride request to the driver's queue."""

    request_json = json.dumps(request)  # convert dict → JSON string

    with db_lock:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()

                # Fetch current pending requests
                c.execute(
                    "SELECT pending_requests, is_driver FROM users WHERE username=?",
                    (driver_username,),
                )
                row = c.fetchone()

                # User not found
                if not row:
                    return "Driver not found."

                pending_json, is_driver = row

                # Ensure user is driver
                if not is_driver:
                    return "User is not registered as a driver."

                # Parse JSON safely
                try:
                    pending_requests = json.loads(pending_json or "[]")
                except json.JSONDecodeError:
                    pending_requests = []

                # Append request
                pending_requests.append(json.loads(request_json))

                # Save updated list to DB
                c.execute(
                    "UPDATE users SET pending_requests=? WHERE username=?",
                    (json.dumps(pending_requests), driver_username),
                )
                conn.commit()

                return "Request added to pending queue."

        except sqlite3.Error as e:  # DB error
            return f"Database error: {e}"


def delete_pending_request(driver_username: str, index: int) -> str:
    """Delete a pending request from a driver's queue by index."""

    with db_lock:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()

                # Fetch current pending requests
                c.execute(
                    "SELECT pending_requests, is_driver FROM users WHERE username=?",
                    (driver_username,),
                )
                row = c.fetchone()

                # User not found
                if not row:
                    return "Driver not found."

                pending_json, is_driver = row

                # User is not a driver
                if not is_driver:
                    return "User is not registered as a driver."

                # Parse JSON list
                try:
                    pending_requests = json.loads(pending_json or "[]")
                except json.JSONDecodeError:
                    pending_requests = []

                # Check invalid index
                if index < 0 or index >= len(pending_requests):
                    return "Invalid request index."

                # Remove item → remaining items shift automatically
                pending_requests.pop(index)

                # Save back the updated list
                c.execute(
                    "UPDATE users SET pending_requests=? WHERE username=?",
                    (json.dumps(pending_requests), driver_username),
                )
                conn.commit()

                return "Request deleted."

        except sqlite3.Error as e:  # DB error
            return f"Database error: {e}"


def accept_pending_request(driver_username: str, request_id: str) -> str:
    """Mark a request as accepted for one driver and remove it from others."""

    if not request_id:
        return "Invalid request ID."

    with db_lock:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()

                c.execute("SELECT is_driver FROM users WHERE username=?", (driver_username,))
                row = c.fetchone()
                if not row:
                    return "Driver not found."
                if not row[0]:
                    return "User is not registered as a driver."

                driver_name = get_user_display_name(driver_username)

                c.execute("SELECT username, pending_requests FROM users WHERE is_driver=1")
                rows = c.fetchall()

                found = False
                passenger = None
                ride_for_passenger = None

                for uname, pending_json in rows:
                    try:
                        pending_requests = json.loads(pending_json or "[]")
                    except json.JSONDecodeError:
                        pending_requests = []

                    changed = False

                    if uname == driver_username:
                        for req in pending_requests:
                            if req.get("id") == request_id:
                                req["status"] = "active"
                                req["accepted_by"] = driver_username
                                passenger = req.get("passenger")
                                passenger_name = req.get("passenger_name") or get_user_display_name(passenger)
                                ride_for_passenger = {
                                    "id": request_id,
                                    "driver": driver_username,
                                    "driver_name": driver_name,
                                    "area": req.get("area"),
                                    "day": req.get("day"),
                                    "time": req.get("time"),
                                    "status": "active",
                                    "passenger": passenger,
                                    "passenger_name": passenger_name,
                                }
                                changed = True
                                found = True
                                break
                    else:
                        filtered = [req for req in pending_requests if req.get("id") != request_id]
                        if len(filtered) != len(pending_requests):
                            pending_requests = filtered
                            changed = True

                    if changed:
                        c.execute(
                            "UPDATE users SET pending_requests=? WHERE username=?",
                            (json.dumps(pending_requests), uname),
                        )

                conn.commit()

                if found and passenger:
                    add_active_ride(passenger, ride_for_passenger)

                return "Request accepted." if found else "Request not found."

        except sqlite3.Error as e:
            return f"Database error: {e}"


def complete_pending_request(driver_username: str, request_id: str) -> str:
    """Remove a pending/active request from the accepting driver's queue."""

    if not request_id:
        return "Invalid request ID."

    with db_lock:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()

                c.execute(
                    "SELECT pending_requests, is_driver FROM users WHERE username=?",
                    (driver_username,),
                )
                row = c.fetchone()

                if not row:
                    return "Driver not found."

                pending_json, is_driver = row
                if not is_driver:
                    return "User is not registered as a driver."

                try:
                    pending_requests = json.loads(pending_json or "[]")
                except json.JSONDecodeError:
                    pending_requests = []

                passenger_username = None
                passenger_ride = None
                new_pending = []
                for req in pending_requests:
                    if req.get("id") == request_id:
                        passenger_username = req.get("passenger")
                        passenger_ride = {
                            "id": request_id,
                            "driver": req.get("accepted_by") or driver_username,
                            "driver_name": req.get("driver_name") or get_user_display_name(req.get("accepted_by") or driver_username),
                            "area": req.get("area"),
                            "day": req.get("day"),
                            "time": req.get("time"),
                            "status": "completed",
                            "passenger": passenger_username,
                            "passenger_name": req.get("passenger_name") or get_user_display_name(passenger_username or "")
                        }
                        continue
                    new_pending.append(req)

                if len(new_pending) == len(pending_requests):
                    return "Request not found."

                c.execute(
                    "UPDATE users SET pending_requests=? WHERE username=?",
                    (json.dumps(new_pending), driver_username),
                )
                conn.commit()
                if passenger_username:
                    remove_active_ride(passenger_username, request_id)
                    if passenger_ride:
                        add_completed_ride(passenger_username, passenger_ride)
                return "Request completed."

        except sqlite3.Error as e:
            return f"Database error: {e}"
def get_active_rides(username: str):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT active_rides FROM users WHERE username=?", (username,))
        row = c.fetchone()
        if not row:
            return "User not found."
        try:
            return json.loads(row[0] or "[]")
        except json.JSONDecodeError:
            return []


def get_completed_rides(username: str):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT completed_rides FROM users WHERE username=?", (username,))
        row = c.fetchone()
        if not row:
            return "User not found."
        try:
            return json.loads(row[0] or "[]")
        except json.JSONDecodeError:
            return []


def add_active_ride(passenger_username: str, ride: dict):
    with db_lock:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()
                c.execute("SELECT active_rides FROM users WHERE username=?", (passenger_username,))
                row = c.fetchone()
                if not row:
                    return
                try:
                    rides = json.loads(row[0] or "[]")
                except json.JSONDecodeError:
                    rides = []
                rides = [r for r in rides if r.get("id") != ride.get("id")]
                rides.append(ride)
                c.execute("UPDATE users SET active_rides=? WHERE username=?", (json.dumps(rides), passenger_username))
                conn.commit()
        except sqlite3.Error:
            return


def remove_active_ride(passenger_username: str, request_id: str):
    if not request_id:
        return
    with db_lock:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()
                c.execute("SELECT active_rides FROM users WHERE username=?", (passenger_username,))
                row = c.fetchone()
                if not row:
                    return
                try:
                    rides = json.loads(row[0] or "[]")
                except json.JSONDecodeError:
                    rides = []
                new_rides = [r for r in rides if r.get("id") != request_id]
                if len(new_rides) == len(rides):
                    return
                c.execute("UPDATE users SET active_rides=? WHERE username=?", (json.dumps(new_rides), passenger_username))
                conn.commit()
        except sqlite3.Error:
            return


def add_completed_ride(passenger_username: str, ride: dict):
    if not ride.get("id"):
        return
    with db_lock:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()
                c.execute("SELECT completed_rides FROM users WHERE username=?", (passenger_username,))
                row = c.fetchone()
                if not row:
                    return
                try:
                    rides = json.loads(row[0] or "[]")
                except json.JSONDecodeError:
                    rides = []
                rides = [r for r in rides if r.get("id") != ride["id"]]
                rides.append(ride)
                c.execute(
                    "UPDATE users SET completed_rides=? WHERE username=?",
                    (json.dumps(rides), passenger_username),
                )
                conn.commit()
        except sqlite3.Error:
            return


def remove_completed_ride(passenger_username: str, request_id: str):
    if not request_id:
        return
    with db_lock:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()
                c.execute("SELECT completed_rides FROM users WHERE username=?", (passenger_username,))
                row = c.fetchone()
                if not row:
                    return
                try:
                    rides = json.loads(row[0] or "[]")
                except json.JSONDecodeError:
                    rides = []
                new_rides = [r for r in rides if r.get("id") != request_id]
                if len(new_rides) == len(rides):
                    return
                c.execute(
                    "UPDATE users SET completed_rides=? WHERE username=?",
                    (json.dumps(new_rides), passenger_username),
                )
                conn.commit()
        except sqlite3.Error:
            return


def add_ride_message(ride_id: str, sender: str, recipient: str, message: str):
    if not ride_id or not sender or not recipient or message is None:
        return "Invalid message data."
    with db_lock:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()
                c.execute(
                    """
                    INSERT INTO ride_messages (ride_id, sender, recipient, message)
                    VALUES (?, ?, ?, ?)
                    """,
                    (ride_id, sender, recipient, message),
                )
                conn.commit()
                return "Message sent."
        except sqlite3.Error as e:
            return f"Database error: {e}"


def get_ride_messages(ride_id: str):
    if not ride_id:
        return "Invalid ride ID."
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT sender, recipient, message, created_at
            FROM ride_messages
            WHERE ride_id=?
            ORDER BY created_at ASC, id ASC
            """,
            (ride_id,),
        )
        rows = c.fetchall()
        messages = []
        for sender, recipient, message, created_at in rows:
            messages.append(
                {
                    "sender": sender,
                    "sender_name": get_user_display_name(sender),
                    "recipient": recipient,
                    "message": message,
                    "timestamp": created_at,
                }
            )
        return messages
