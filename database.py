# database.py
# Barcha ma'lumotlar bazasi funksiyalari

import sqlite3
from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            first_name TEXT,
            username TEXT,
            points INTEGER DEFAULT 10,
            coins INTEGER DEFAULT 5,
            referred_by INTEGER,
            is_subscribed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # resource_type: 'course' (video darslar kursi) yoki 'book' (kitob/masala to'plami)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subject TEXT NOT NULL,
            resource_type TEXT DEFAULT 'course',
            description TEXT,
            is_free INTEGER DEFAULT 1,
            required_referrals INTEGER DEFAULT 0,
            duration_text TEXT,
            students_count INTEGER DEFAULT 0,
            thumbnail_emoji TEXT DEFAULT '📘',
            order_num INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            video_url TEXT,
            description TEXT,
            order_num INTEGER DEFAULT 0,
            FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
        )
    """)

    # Referal tizimi: kim kimni taklif qildi, tasdiqlanganmi (kanalga obuna bo'lganmi)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_telegram_id INTEGER NOT NULL,
            referred_telegram_id INTEGER UNIQUE NOT NULL,
            confirmed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("Baza tayyor: users, courses, lessons, referrals jadvallari.")


# ---------- USERS ----------

def get_or_create_user(telegram_id: int, first_name: str, username: str = None, referred_by: int = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cur.fetchone()

    if user is None:
        cur.execute(
            "INSERT INTO users (telegram_id, first_name, username, referred_by) VALUES (?, ?, ?, ?)",
            (telegram_id, first_name, username, referred_by)
        )
        conn.commit()
        cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cur.fetchone()

    conn.close()
    return dict(user)


def set_user_subscribed(telegram_id: int, value: bool = True):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_subscribed = ? WHERE telegram_id = ?", (1 if value else 0, telegram_id))
    conn.commit()
    conn.close()


# ---------- REFERRALS ----------

def create_pending_referral(referrer_id: int, referred_id: int):
    """Yangi referalni yozadi (hali tasdiqlanmagan holatda)"""
    if referrer_id == referred_id:
        return
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM referrals WHERE referred_telegram_id = ?", (referred_id,))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO referrals (referrer_telegram_id, referred_telegram_id, confirmed) VALUES (?, ?, 0)",
            (referrer_id, referred_id)
        )
        conn.commit()
    conn.close()


def confirm_referral(referred_id: int) -> int | None:
    """referred_id foydalanuvchi kanalga obuna bo'lganini tasdiqlaydi.
    Referrer_id ni qaytaradi (agar mavjud bo'lsa)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT referrer_telegram_id, confirmed FROM referrals WHERE referred_telegram_id = ?", (referred_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        return None
    if row["confirmed"] == 0:
        cur.execute("UPDATE referrals SET confirmed = 1 WHERE referred_telegram_id = ?", (referred_id,))
        conn.commit()
    referrer_id = row["referrer_telegram_id"]
    conn.close()
    return referrer_id


def get_confirmed_referral_count(telegram_id: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) as c FROM referrals WHERE referrer_telegram_id = ? AND confirmed = 1",
        (telegram_id,)
    )
    count = cur.fetchone()["c"]
    conn.close()
    return count


def get_referral_progress(telegram_id: int):
    """Referrer uchun taklif qilingan odamlar ro'yxati (ism va holati)"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.referred_telegram_id, r.confirmed, u.first_name
        FROM referrals r
        LEFT JOIN users u ON u.telegram_id = r.referred_telegram_id
        WHERE r.referrer_telegram_id = ?
        ORDER BY r.created_at DESC
    """, (telegram_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ---------- COURSES ----------

def get_all_courses(resource_type: str = None, only_active: bool = True):
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT * FROM courses WHERE 1=1"
    params = []
    if resource_type:
        query += " AND resource_type = ?"
        params.append(resource_type)
    if only_active:
        query += " AND is_active = 1"
    query += " ORDER BY order_num ASC, id ASC"
    cur.execute(query, params)
    courses = [dict(row) for row in cur.fetchall()]
    conn.close()
    return courses


def get_course(course_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_course(data: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO courses (title, subject, resource_type, description, is_free,
            required_referrals, duration_text, students_count, thumbnail_emoji, order_num, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("title", ""), data.get("subject", ""), data.get("resource_type", "course"),
        data.get("description", ""), int(data.get("is_free", 1)),
        int(data.get("required_referrals", 0)), data.get("duration_text", ""),
        int(data.get("students_count", 0)), data.get("thumbnail_emoji", "📘"),
        int(data.get("order_num", 0)), int(data.get("is_active", 1))
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_course(course_id: int, data: dict):
    conn = get_connection()
    cur = conn.cursor()
    fields = []
    values = []
    allowed = ["title", "subject", "resource_type", "description", "is_free",
               "required_referrals", "duration_text", "students_count",
               "thumbnail_emoji", "order_num", "is_active"]
    for key in allowed:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if fields:
        values.append(course_id)
        cur.execute(f"UPDATE courses SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    conn.close()


def delete_course(course_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM courses WHERE id = ?", (course_id,))
    conn.commit()
    conn.close()


# ---------- LESSONS ----------

def get_lessons(course_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM lessons WHERE course_id = ? ORDER BY order_num ASC, id ASC", (course_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    # course.lessons_count ni dinamik hisoblaymiz, shuning uchun alohida jadval kerak emas
    return rows


def create_lesson(data: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO lessons (course_id, title, video_url, description, order_num)
        VALUES (?, ?, ?, ?, ?)
    """, (
        int(data["course_id"]), data.get("title", ""), data.get("video_url", ""),
        data.get("description", ""), int(data.get("order_num", 0))
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_lesson(lesson_id: int, data: dict):
    conn = get_connection()
    cur = conn.cursor()
    fields = []
    values = []
    allowed = ["title", "video_url", "description", "order_num"]
    for key in allowed:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if fields:
        values.append(lesson_id)
        cur.execute(f"UPDATE lessons SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    conn.close()


def delete_lesson(lesson_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
    conn.commit()
    conn.close()


def get_lessons_count(course_id: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM lessons WHERE course_id = ?", (course_id,))
    c = cur.fetchone()["c"]
    conn.close()
    return c


def add_sample_courses():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM courses")
    count = cur.fetchone()["c"]
    if count == 0:
        sample = [
            ("Mavzulashtirilgan masala kursi", "Kimyo", "course", "2000 dan ortiq masalalar", 0, 1, "3 oy", 0, "🧪", 1, 1),
            ("Super nazariya", "Biologiya", "course", "Barcha mavzulardan nazariy videolar", 0, 2, "6 oy", 0, "🧬", 2, 1),
            ("Yechilgan masalalar to'plami", "Kimyo", "book", "Men shaxsan yechgan masalalar to'plami", 1, 0, "", 0, "📗", 3, 1),
        ]
        cur.executemany("""
            INSERT INTO courses (title, subject, resource_type, description, is_free,
                required_referrals, duration_text, students_count, thumbnail_emoji, order_num, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample)
        conn.commit()
        print("Namuna kurslar qo'shildi.")
    conn.close()
