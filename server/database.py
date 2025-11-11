import sqlite3
import threading

DB_FILE = 'AUBus.db'
db_lock = threading.Lock()

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('PRAGMA foreign_keys = ON;')
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            password TEXT NOT NULL,
            area TEXT,
            is_driver INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)
        conn.commit()

def register_user(username: str, name: str, email: str, password: str, area: str = None, is_driver: int = 0) -> str:
    with db_lock:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO users (username, name, email, password, area, is_driver)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (username, name, email, password, area, is_driver))
                conn.commit()
            return "User registered successfully."
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint" in str(e):
                return "Username or email already exists."
            return f"Database error: {e}"

def login_user(username: str, password: str) -> str:
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username=?", (username,))
        result = c.fetchone()
        if not result:
            return "User not found."
        if result[0] == hashed_pw:
            return "Login successful."
        return "Incorrect password."
