# utils/db.py
import sqlite3
from datetime import datetime

DB_PATH = "database.db"


def connect():
    return sqlite3.connect(DB_PATH)


# === Jadval yaratish ===
def init_db():
    conn = connect()
    cur = conn.cursor()

    # === Foydalanuvchilar jadvallari ===
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        premium INTEGER DEFAULT 0,
        blocked INTEGER DEFAULT 0,
        state TEXT,
        subject TEXT,
        grade TEXT,
        free_uses INTEGER DEFAULT 0
    )
    """)

    # === Tarix jadvallari ===
    cur.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        subject TEXT,
        grade TEXT,
        topic TEXT,
        file_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # === To‘lovlar jadvallari ===
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        photo_id TEXT,
        approved INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # === Oxirgi so‘rovlar jadvallari ===
    cur.execute("""
    CREATE TABLE IF NOT EXISTS last_requests (
        user_id INTEGER PRIMARY KEY,
        subject TEXT,
        grade TEXT,
        topic TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


# === Oxirgi so‘rovlar ===
def save_last_request(user_id: int, subject: str, grade: str, topic: str):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO last_requests (user_id, subject, grade, topic, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET 
            subject=excluded.subject,
            grade=excluded.grade,
            topic=excluded.topic,
            created_at=excluded.created_at
    """, (user_id, subject, grade, topic, datetime.now()))
    conn.commit()
    conn.close()


def get_last_request(user_id: int):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT subject, grade, topic FROM last_requests WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row


# === Foydalanuvchilar ===
def add_user(user_id: int, username: str):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO users (user_id, username, free_uses) VALUES (?, ?, 0)",
        (user_id, username)
    )
    conn.commit()
    conn.close()


def is_premium(user_id: int) -> bool:
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT premium FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row and row[0] == 1


def set_premium(user_id: int, status: int = 1):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE users SET premium=? WHERE user_id=?", (status, user_id))
    conn.commit()
    conn.close()


def block_user(user_id: int):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE users SET blocked=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def unblock_user(user_id: int):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE users SET blocked=0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def is_blocked(user_id: int) -> bool:
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT blocked FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row and row[0] == 1


def get_users_count():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


# === State boshqaruvi ===
def set_state(user_id: int, state: str):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE users SET state=? WHERE user_id=?", (state, user_id))
    conn.commit()
    conn.close()


def get_state(user_id: int):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT state FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


# === Fan / sinf ===
def set_subject(user_id: int, subject: str):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE users SET subject=? WHERE user_id=?", (subject, user_id))
    conn.commit()
    conn.close()


def get_subject(user_id: int):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT subject FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def set_grade(user_id: int, grade: str):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE users SET grade=? WHERE user_id=?", (grade, user_id))
    conn.commit()
    conn.close()


def get_grade(user_id: int):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT grade FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


# === Tarix ===
def save_history(user_id: int, subject: str, grade: str, topic: str, file_path: str):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO history (user_id, subject, grade, topic, file_path) VALUES (?, ?, ?, ?, ?)",
        (user_id, subject, grade, topic, file_path)
    )
    conn.commit()
    conn.close()


def get_history(user_id: int):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM history WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


# === To‘lovlar ===
def add_payment(user_id: int, username: str, photo_id: str):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO payments (user_id, username, photo_id, approved, created_at)
        VALUES (?, ?, ?, 0, ?)
    """, (user_id, username, photo_id, datetime.now()))
    payment_id = cur.lastrowid
    conn.commit()
    conn.close()
    return payment_id


def get_pending_payments():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM payments WHERE approved=0")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_payment_by_id(payment_id: int):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, user_id, username, photo_id, approved, created_at FROM payments WHERE id=?", (payment_id,))
    row = cur.fetchone()
    conn.close()
    return row


def approve_payment(payment_id: int):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE payments SET approved=1 WHERE id=?", (payment_id,))
    conn.commit()
    conn.close()


def reject_payment(payment_id: int):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE payments SET approved=-1 WHERE id=?", (payment_id,))
    conn.commit()
    conn.close()


# === Bepul foydalanish (limit) ===
def get_free_uses(user_id: int):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT free_uses FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


def increment_free_use(user_id: int):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE users SET free_uses = free_uses + 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
