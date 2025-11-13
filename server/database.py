import sqlite3
import threading
import json 

DB_FILE = 'AUBus.db'
db_lock = threading.Lock()

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        password TEXT NOT NULL,
        area TEXT,
        is_driver INTEGER NOT NULL DEFAULT 0,
        mon_commute TEXT DEFAULT '[]',
        tue_commute TEXT DEFAULT '[]',
        wed_commute TEXT DEFAULT '[]',
        thu_commute TEXT DEFAULT '[]',
        fri_commute TEXT DEFAULT '[]',
        sat_commute TEXT DEFAULT '[]',
        sun_commute TEXT DEFAULT '[]'
                ,rating REAL NOT NULL DEFAULT 5.0,
                rating_count INTEGER NOT NULL DEFAULT 0
    )
    """)
        conn.commit()

def register_user(username: str, name: str, email: str, password: str,
                  area: str = None, is_driver: int = 0, commute_schedule: dict = None) -> str:
    with db_lock:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()

                days = ["mon_commute", "tue_commute", "wed_commute",
                        "thu_commute", "fri_commute", "sat_commute", "sun_commute"]

                if is_driver != 1:
                    commute_schedule = {day: [] for day in days}
                else:
                    if commute_schedule is None:
                        commute_schedule = {day: [] for day in days}
                    else:
                        for day in days:
                            commute_schedule.setdefault(day, [])

                commute_values = [json.dumps(commute_schedule[day]) for day in days]

                c.execute(f"""
                    INSERT INTO users (
                        username, name, email, password, area, is_driver,
                        mon_commute, tue_commute, wed_commute, thu_commute,
                        fri_commute, sat_commute, sun_commute
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (username, name, email, password, area, is_driver, *commute_values))

                conn.commit()
            return "User registered successfully."

        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint" in str(e):
                return "Username or email already exists."
            return f"Database error: {e}"
        except sqlite3.Error as e:
            return f"Database error: {e}"

        
def login_user(username: str, password: str) -> str:
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username=?", (username,))
        result = c.fetchone()
        if not result:
            return "User not found."
        if result[0] == password:
            return "Login successful."
        return "Incorrect password."
def edit_fields(username: str, fields: dict) -> str:
    if not fields:
        return "No fields provided to update."
        
    valid_columns = {
        "name", "password", "area", "is_driver",
        "mon_commute", "tue_commute", "wed_commute",
        "thu_commute", "fri_commute", "sat_commute", "sun_commute"
    }

    updates = {k: v for k, v in fields.items() if k in valid_columns}

    if not updates:
        return "No valid fields to update."

    for day in ["mon_commute", "tue_commute", "wed_commute",
                "thu_commute", "fri_commute", "sat_commute", "sun_commute"]:
        if day in updates:
            updates[day] = json.dumps(updates[day])

    set_clause = ", ".join(f"{col}=?" for col in updates.keys())
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
            if "UNIQUE constraint" in str(e):
                return "Email already exists."
            return f"Database error: {e}"
def search_valid_drivers(area: str, day: str, time: str, min_rating: float = 0.0):
    """
    Search for eligible drivers in a specific area and day whose commute includes the given time.
    Drivers must have:
      - is_driver = 1
      - matching area
      - rating >= min_rating
      - a (start, end) commute interval that includes 'time'
    """
    with db_lock:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()

                # Validate the day argument
                valid_days = ["mon_commute", "tue_commute", "wed_commute",
                              "thu_commute", "fri_commute", "sat_commute", "sun_commute"]
                if day not in valid_days:
                    return "Invalid day provided."

                # Query all eligible drivers in the same area and above rating threshold
                c.execute(f"""
                    SELECT username, name, area, {day}
                    FROM users
                    WHERE is_driver = 1 AND area = ? AND rating >= ?
                """, (area, min_rating))

                drivers = []
                for username, name, driver_area, commute_json in c.fetchall():
                    try:
                        commutes = json.loads(commute_json or "[]")  # Parse commute JSON
                    except json.JSONDecodeError:
                        commutes = []

                    # Check if passenger's requested time fits within any (start, end) commute interval
                    for interval in commutes:
                        if len(interval) == 2:  # Ensure valid (start, end) pair
                            start, end = interval
                            if start <= time <= end:
                                drivers.append({
                                    "username": username,
                                    "name": name,
                                    "area": driver_area,
                                    "available_from": start,
                                    "available_to": end
                                })
                                break  # Found a matching slot, stop checking further

                if not drivers:
                    return "No valid drivers found."
                return drivers

        except sqlite3.Error as e:
            return f"Database error: {e}"
