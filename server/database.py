import sqlite3
import threading
import json
from typing import Tuple, List, Dict, Any

DB_FILE = "AUBus.db"
db_lock = threading.Lock()  # Prevents race conditions during DB writes


def init_db():
    """Create the users table if it doesn't exist."""
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()

        # Main table storing all user info
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            password TEXT NOT NULL,
            area TEXT,
            is_driver INTEGER NOT NULL DEFAULT 0,
            min_passenger_rating REAL NOT NULL DEFAULT 0.0,   -- rating threshold for drivers

            driver_rating REAL NOT NULL DEFAULT 5.0,
            driver_rating_count INTEGER NOT NULL DEFAULT 1,
            passenger_rating REAL NOT NULL DEFAULT 5.0,
            passenger_rating_count INTEGER NOT NULL DEFAULT 1,

            -- commute schedules stored as JSON strings
            mon_commute TEXT DEFAULT '[]',
            tue_commute TEXT DEFAULT '[]',
            wed_commute TEXT DEFAULT '[]',
            thu_commute TEXT DEFAULT '[]',
            fri_commute TEXT DEFAULT '[]',
            sat_commute TEXT DEFAULT '[]',
            sun_commute TEXT DEFAULT '[]'
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

    days = [
        "mon_commute", "tue_commute", "wed_commute",
        "thu_commute", "fri_commute", "sat_commute", "sun_commute"
    ]

    with db_lock:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()

                # Passengers never have commute schedules or passenger rating filters
                if is_driver != 1:
                    commute_schedule = {d: [] for d in days}
                    min_passenger_rating = 0.0
                else:
                    # Ensure every day has a list (even if empty)
                    if commute_schedule is None:
                        commute_schedule = {d: [] for d in days}
                    else:
                        for d in days:
                            commute_schedule.setdefault(d, [])

                # Convert schedules to JSON strings for SQLite
                commute_values = [json.dumps(commute_schedule[d]) for d in days]

                # Insert new user
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
                    0.0, 0,           # driver rating + count
                    0.0, 0,           # passenger rating + count
                    *commute_values
                ))

                conn.commit()

            return "User registered successfully."

        except sqlite3.IntegrityError as e:
            # UNIQUE constraint: username or email already used
            if "UNIQUE" in str(e):
                return "Username or email already exists."
            return f"Database error: {e}"

        except sqlite3.Error as e:
            return f"Database error: {e}"


def login_user(username: str, password: str) -> str:
    """Validate username/password and return packed user info."""

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()

        c.execute("""
        SELECT name, email, area, is_driver, password
        FROM users WHERE username=?
        """, (username,))

        row = c.fetchone()
        if not row:
            return "error:User not found."

        name, email, area, is_driver, stored_pw = row

        if stored_pw != password:
            return "error:Incorrect password."

        # Format expected by your client
        return f"success:{name}:{email}:{area}:{is_driver}"


def edit_fields(username: str, fields: Dict[str, Any]) -> str:
    """Update specific user fields (except ratings)."""

    if not fields:
        return "No fields provided to update."

    # Allowed fields to edit
    valid_columns = {
        "name", "password", "area", "is_driver", "min_passenger_rating",
        "mon_commute", "tue_commute", "wed_commute",
        "thu_commute", "fri_commute", "sat_commute", "sun_commute"
    }

    updates = {k: v for k, v in fields.items() if k in valid_columns}
    if not updates:
        return "No valid fields to update."

    # Convert commute arrays to JSON strings
    for d in updates:
        if "commute" in d:
            updates[d] = json.dumps(updates[d])

    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [username]

    with db_lock:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()

                c.execute(f"UPDATE users SET {set_clause} WHERE username=?", values)
                conn.commit()

                if c.rowcount == 0:
                    return "User not found."

                return "User updated successfully."

        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e):
                return "Email already exists."
            return f"Database error: {e}"

        except sqlite3.Error as e:
            return f"Database error: {e}"


def search_valid_drivers(area: str, day: str, time: str, min_rating: float = 0.0):
    """Find drivers in an area whose commute matches a given time and rating threshold."""

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

                # Fetch all drivers matching area + rating requirements
                c.execute(f"""
                SELECT username, name, area, {day}, min_passenger_rating
                FROM users
                WHERE is_driver = 1
                  AND area = ?
                  AND min_passenger_rating <= ?
                """, (area, min_rating))

                drivers = []

                for username, name, ar, commute_json, req_rating in c.fetchall():
                    try:
                        commutes = json.loads(commute_json or "[]")
                    except:
                        commutes = []

                    # Check if requested time falls inside any (start, end) interval
                    for interval in commutes:
                        if len(interval) == 2:
                            start, end = interval
                            if start <= time <= end:
                                drivers.append({
                                    "username": username,
                                    "name": name,
                                    "area": ar,
                                    "min_passenger_rating": req_rating,
                                    "available_from": start,
                                    "available_to": end
                                })
                                break

                return "No valid drivers found." if not drivers else drivers

        except sqlite3.Error as e:
            return f"Database error: {e}"


def calculate_rating(current: float, count: int, new: float) -> Tuple[float, int]:
    """Recalculate average rating given a new rating input."""
    new = max(0.0, min(5.0, float(new)))  # clamp rating to valid range
    total = current * count

    count += 1
    updated = (total + new) / count

    return round(updated, 2), count


def _rate_user(username: str, new_rating: float, role: str) -> str:
    """Internal helper to rate a driver or passenger."""

    rating_col = f"{role}_rating"
    count_col = f"{role}_rating_count"

    with db_lock:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()

                # Fetch current rating + count
                c.execute(f"""
                SELECT {rating_col}, {count_col}
                FROM users
                WHERE username=?
                """, (username,))

                row = c.fetchone()
                if not row:
                    return "User not found."

                current, count = row
                new_avg, new_count = calculate_rating(current, count, new_rating)

                # Update with new rating
                c.execute(f"""
                UPDATE users
                SET {rating_col} = ?, {count_col} = ?
                WHERE username = ?
                """, (new_avg, new_count, username))

                conn.commit()

                return f"{role.capitalize()} rating updated."

        except sqlite3.Error as e:
            return f"Database error: {e}"


def rate_driver(username: str, new_rating: float) -> str:
    """Public function to rate a driver."""
    return _rate_user(username, new_rating, "driver")


def rate_passenger(username: str, new_rating: float) -> str:
    """Public function to rate a passenger."""
    return _rate_user(username, new_rating, "passenger")
