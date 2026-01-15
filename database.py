import sqlite3

DB_NAME = "timers.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def create_table():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS timers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            session_length INTEGER NOT NULL,
            short_break INTEGER NOT NULL,
            long_break INTEGER NOT NULL,
            short_per_long INTEGER NOT NULL,
            total_sessions INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def add_timer(name, session_length, short_break, long_break, short_per_long, total_sessions):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO timers (name, session_length, short_break, long_break, short_per_long, total_sessions) VALUES (?, ?, ?, ?, ?, ?)",
            (name, session_length, short_break, long_break, short_per_long, total_sessions)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Timer with this name already exists
        pass
    finally:
        conn.close()

def get_all_timers():
    conn = get_db_connection()
    timers = conn.execute("SELECT * FROM timers").fetchall()
    conn.close()
    return timers

def get_timer_by_id(timer_id):
    conn = get_db_connection()
    timer = conn.execute("SELECT * FROM timers WHERE id = ?", (timer_id,)).fetchone()
    conn.close()
    return timer

