import sqlite3
import threading
import json
from typing import Tuple, List, Dict, Any

DB_FILE = "AUBus.db"  # Database file name
db_lock = threading.Lock()  # Prevents concurrent write access issues

 
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
            sun_commute TEXT DEFAULT '[]'                       -- daily commute schedules stored as JSON arrays
        )
        """)

        conn.commit()  # Save changes


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
                    fri_commute, sat_commute, sun_commute
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    username, name, email, password, area, is_driver,
                    float(min_passenger_rating),
                    0.0, 0,            # driver rating + count
                    0.0, 0,            # passenger rating + count
                    *commute_values    # unpack commute schedule JSON
                ))

                conn.commit()  # Save DB

            return "User registered successfully."

        except sqlite3.IntegrityError as e:  # duplicate username or email
            if "UNIQUE" in str(e):
                return "Username or email already exists."
            return f"Database error: {e}"

        except sqlite3.Error as e:  # generic SQLite error
            return f"Database error: {e}"


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
         fri_commute, sat_commute, sun_commute) = row


        # Password incorrect
        if stored_pw != password:
            return "error:Incorrect password."

        # Return packed data to client
        return f"success:{name}:{email}:{area}:{is_driver}:{min_passenger_rating}:{driver_rating}:
        {passenger_rating}:{pending_requests}:{driver_rating}:{passenger_rating}: 
        {mon_commute}:{tue_commute}:{wed_commute}:{thu_commute}:{fri_commute}:{sat_commute}:{sun_commute}"


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
    """Find drivers in an area whose commute matches a given time and rating threshold."""

    # List of valid commute-day columns
    valid_days = [
        "mon_commute", "tue_commute", "wed_commute",
        "thu_commute", "fri_commute", "sat_commute", "sun_commute"
    ]

    # Day not valid
    if day not in valid_days:
        return "Invalid day provided."

    with db_lock:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()

                # Query drivers in the same area meeting rating requirement
                c.execute(f"""
                SELECT username, name, area, {day}, min_passenger_rating
                FROM users
                WHERE is_driver = 1
                  AND area = ?
                  AND min_passenger_rating <= ?
                """, (area, min_rating))

                drivers = []  # list to store matched drivers

                for username, name, ar, commute_json, req_rating in c.fetchall():

                    # Parse commute JSON
                    try:
                        commutes = json.loads(commute_json or "[]")
                    except:
                        commutes = []

                    # Check if requested time fits inside any commute interval
                    for interval in commutes:
                        if len(interval) == 2:
                            start, end = interval

                            # time within interval
                            if start <= time <= end:
                                drivers.append({
                                    "username": username,
                                    "name": name,
                                    "area": ar,
                                    "min_passenger_rating": req_rating,
                                    "available_from": start,
                                    "available_to": end
                                })
                                break  # stop checking intervals

                return "No valid drivers found." if not drivers else drivers

        except sqlite3.Error as e:  # DB error
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
