import sqlite3
import os
from datetime import datetime

DB_FILE = "midman.db"

def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def _table_exists(conn, table_name):
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cur.fetchone() is not None

def _get_columns(conn, table_name):
    cur = conn.execute(f"PRAGMA table_info({table_name})")
    return {row["name"] for row in cur.fetchall()}

def _migrate_autopost_tables():
    conn = get_conn()
    
    if not _table_exists(conn, "autopost_tasks"):
        conn.execute("""
            CREATE TABLE autopost_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                message TEXT NOT NULL,
                interval_minutes INTEGER NOT NULL,
                user_token TEXT NOT NULL DEFAULT '',
                loop_counter INTEGER DEFAULT 0,
                last_post TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
        return
    
    cols = _get_columns(conn, "autopost_tasks")
    required_cols = {"channel_id", "message", "interval_minutes", "user_token", "loop_counter", "last_post", "is_active", "created_at"}
    
    if required_cols.issubset(cols):
        conn.close()
        return
    
    rows = conn.execute("SELECT * FROM autopost_tasks").fetchall()
    conn.execute("DROP TABLE autopost_tasks")
    conn.commit()
    
    conn.execute("""
        CREATE TABLE autopost_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL,
            message TEXT NOT NULL,
            interval_minutes INTEGER NOT NULL,
            user_token TEXT NOT NULL DEFAULT '',
            loop_counter INTEGER DEFAULT 0,
            last_post TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    
    for row in rows:
        from datetime import datetime
        conn.execute(
            "INSERT INTO autopost_tasks (channel_id, message, interval_minutes, user_token, loop_counter, last_post, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (row["channel_id"], row["message"], row["interval_minutes"], row.get("user_token", ""), row.get("loop_counter", 0), row.get("last_post"), row.get("is_active", 1), datetime.now().isoformat())
        )
    conn.commit()
    conn.close()

def init_autopost_tables():
    _migrate_autopost_tables()
    
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS autopost_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            message TEXT,
            status TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def get_autopost_tasks():
    conn = get_conn()
    cur = conn.execute("SELECT * FROM autopost_tasks ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_autopost_task(task_id):
    conn = get_conn()
    cur = conn.execute("SELECT * FROM autopost_tasks WHERE id = ?", (task_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def add_autopost_task(channel_id: str, message: str, interval_minutes: int, user_token: str):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO autopost_tasks 
           (channel_id, message, interval_minutes, user_token, loop_counter, last_post, is_active, created_at)
           VALUES (?, ?, ?, ?, 0, NULL, 1, ?)""",
        (channel_id, message, interval_minutes, user_token, datetime.now().isoformat())
    )
    conn.commit()
    task_id = cur.lastrowid
    conn.close()
    return task_id

def update_autopost_counter(task_id: int, loop_counter: int):
    conn = get_conn()
    conn.execute("UPDATE autopost_tasks SET loop_counter = ? WHERE id = ?", (loop_counter, task_id))
    conn.commit()
    conn.close()

def update_autopost_last_post(task_id: int):
    conn = get_conn()
    conn.execute("UPDATE autopost_tasks SET last_post = ?, loop_counter = 0 WHERE id = ?",
                (datetime.now().isoformat(), task_id))
    conn.commit()
    conn.close()

def toggle_autopost_task(task_id: int):
    conn = get_conn()
    conn.execute(
        "UPDATE autopost_tasks SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?",
        (task_id,)
    )
    conn.commit()
    conn.close()

def delete_autopost_task(task_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM autopost_tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

def update_autopost_task(task_id: int, message: str = None, interval_minutes: int = None, user_token: str = None):
    conn = get_conn()
    if message is not None:
        conn.execute("UPDATE autopost_tasks SET message = ? WHERE id = ?", (message, task_id))
    if interval_minutes is not None:
        conn.execute("UPDATE autopost_tasks SET interval_minutes = ? WHERE id = ?", (interval_minutes, task_id))
    if user_token is not None:
        conn.execute("UPDATE autopost_tasks SET user_token = ? WHERE id = ?", (user_token, task_id))
    conn.commit()
    conn.close()

def log_autopost_history(task_id: int, message: str, status: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO autopost_history (task_id, message, status, created_at) VALUES (?, ?, ?, ?)",
        (task_id, message, status, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_autopost_history(task_id: int = None, limit: int = 50):
    conn = get_conn()
    if task_id:
        cur = conn.execute(
            "SELECT * FROM autopost_history WHERE task_id = ? ORDER BY id DESC LIMIT ?",
            (task_id, limit)
        )
    else:
        cur = conn.execute("SELECT * FROM autopost_history ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]
