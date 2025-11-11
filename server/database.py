import sqlite3

connection = sqlite3.connect('AUBus.db')
cursor = connection.cursor()

cursor.execute('PRAGMA foreign_keys = ON;')

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	name TEXT NOT NULL,
	email TEXT UNIQUE,
	username TEXT UNIQUE NOT NULL,
	password TEXT NOT NULL,
	area TEXT,
	is_driver INTEGER NOT NULL DEFAULT 0,
	created_at TEXT DEFAULT (datetime('now'))
)
""")
connection.commit()
print("Users table created/opened successfully.")

connection.close()



