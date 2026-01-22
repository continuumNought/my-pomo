import sqlite3
import datetime

DB_NAME = "timers.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timer_id INTEGER NOT NULL,
            start_timestamp TEXT NOT NULL,
            stop_timestamp TEXT,
            sessions_completed INTEGER DEFAULT 0,
            short_breaks_completed INTEGER DEFAULT 0,
            long_breaks_completed INTEGER DEFAULT 0,
            FOREIGN KEY (timer_id) REFERENCES timers (id)
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

def update_timer(timer_id, name, session_length, short_break, long_break, short_per_long, total_sessions):
    conn = get_db_connection()
    try:
        conn.execute(
            """
            UPDATE timers
            SET name = ?,
                session_length = ?,
                short_break = ?,
                long_break = ?,
                short_per_long = ?,
                total_sessions = ?
            WHERE id = ?
            """,
            (name, session_length, short_break, long_break, short_per_long, total_sessions, timer_id)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Timer with this name already exists
        pass
    finally:
        conn.close()

def create_session(timer_id):
    conn = get_db_connection()
    start_time = datetime.datetime.now().isoformat()
    cursor = conn.execute(
        "INSERT INTO sessions (timer_id, start_timestamp) VALUES (?, ?)",
        (timer_id, start_time)
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id

def update_session(session_id, stop_timestamp, sessions_completed, short_breaks_completed, long_breaks_completed):
    conn = get_db_connection()
    conn.execute(
        """
        UPDATE sessions
        SET stop_timestamp = ?,
            sessions_completed = ?,
            short_breaks_completed = ?,
            long_breaks_completed = ?
        WHERE id = ?
        """,
        (stop_timestamp, sessions_completed, short_breaks_completed, long_breaks_completed, session_id)
    )
    conn.commit()
    conn.close()

def delete_timer(timer_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM timers WHERE id = ?", (timer_id,))
    conn.execute("DELETE FROM sessions WHERE timer_id = ?", (timer_id,))
    conn.commit()
    conn.close()

def get_all_sessions():
    conn = get_db_connection()
    sessions = conn.execute("SELECT * FROM sessions").fetchall()
    conn.close()
    return sessions

