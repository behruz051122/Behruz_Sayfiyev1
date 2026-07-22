# database.py
# Barcha ma'lumotlar bazasi funksiyalari (v2 — paragraf tuzilishi, coin, obuna)

import sqlite3
import datetime
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
            coins INTEGER DEFAULT 0,
            referred_by INTEGER,
            is_subscribed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # resource_type: 'course' yoki 'book'
    # price=0 => bepul (yoki faqat referal orqali, required_referrals bilan)
    # duration_days=NULL => muddatsiz (bepul kurslar uchun), aks holda obuna necha kunga
    cur.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subject TEXT NOT NULL,
            resource_type TEXT DEFAULT 'course',
            description TEXT,
            is_free INTEGER DEFAULT 1,
            required_referrals INTEGER DEFAULT 0,
            price INTEGER DEFAULT 0,
            duration_days INTEGER,
            duration_text TEXT,
            students_count INTEGER DEFAULT 0,
            thumbnail_emoji TEXT DEFAULT '📘',
            order_num INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Paragraf (bo'lim) — har biri ichida bir nechta (masalan 10 tadan) video dars bo'ladi
    cur.execute("""
        CREATE TABLE IF NOT EXISTS paragraphs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            order_num INTEGER DEFAULT 0,
            FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paragraph_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            video_url TEXT,
            description TEXT,
            order_num INTEGER DEFAULT 0,
            FOREIGN KEY (paragraph_id) REFERENCES paragraphs (id) ON DELETE CASCADE
        )
    """)

    # Foydalanuvchi qaysi darsni ko'rib, coin olganini yozib boradi (bir darsga bir marta coin)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lesson_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            lesson_id INTEGER NOT NULL,
            coin_awarded INTEGER DEFAULT 0,
            watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(telegram_id, lesson_id)
        )
    """)

    # Pullik kursga obuna (admin qo'lda tasdiqlaydi yoki keyinchalik Payme/Click orqali avtomatik)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            expiry_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(telegram_id, course_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_telegram_id INTEGER NOT NULL,
            referred_telegram_id INTEGER UNIQUE NOT NULL,
            confirmed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ---------- TEST TIZIMI ----------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            title TEXT NOT NULL,
            difficulty TEXT DEFAULT 'orta',
            time_limit_seconds INTEGER DEFAULT 600,
            order_num INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS test_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            image_url TEXT,
            option_1 TEXT,
            option_2 TEXT,
            option_3 TEXT,
            option_4 TEXT,
            correct_index INTEGER NOT NULL,
            order_num INTEGER DEFAULT 0,
            FOREIGN KEY (test_id) REFERENCES tests (id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS test_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            test_id INTEGER NOT NULL,
            score INTEGER DEFAULT 0,
            total_questions INTEGER DEFAULT 0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS test_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            selected_index INTEGER,
            is_correct INTEGER DEFAULT 0,
            FOREIGN KEY (attempt_id) REFERENCES test_attempts (id) ON DELETE CASCADE
        )
    """)

    # Har bir savolga birinchi marta to'g'ri javob berilganda coin beriladi —
    # qayta ishlashda (retake) coin qayta berilmaydi, bu suiiste'molni oldini oladi.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_question_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            coin_awarded INTEGER DEFAULT 0,
            UNIQUE(telegram_id, question_id)
        )
    """)

    conn.commit()
    conn.close()
    print("Baza tayyor (v3): users, courses, paragraphs, lessons, lesson_progress, enrollments, referrals, tests.")


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


def add_coins(telegram_id: int, amount: int = 1):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET coins = coins + ? WHERE telegram_id = ?", (amount, telegram_id))
    conn.commit()
    conn.close()


# ---------- REFERRALS ----------

def create_pending_referral(referrer_id: int, referred_id: int):
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


def confirm_referral(referred_id: int):
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
    cur.execute("SELECT COUNT(*) as c FROM referrals WHERE referrer_telegram_id = ? AND confirmed = 1", (telegram_id,))
    count = cur.fetchone()["c"]
    conn.close()
    return count


def get_referral_progress(telegram_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.referred_telegram_id, r.confirmed, u.first_name
        FROM referrals r LEFT JOIN users u ON u.telegram_id = r.referred_telegram_id
        WHERE r.referrer_telegram_id = ? ORDER BY r.created_at DESC
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
            required_referrals, price, duration_days, duration_text, students_count,
            thumbnail_emoji, order_num, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("title", ""), data.get("subject", ""), data.get("resource_type", "course"),
        data.get("description", ""), int(data.get("is_free", 1)),
        int(data.get("required_referrals", 0)), int(data.get("price", 0)),
        data.get("duration_days") or None, data.get("duration_text", ""),
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
    fields, values = [], []
    allowed = ["title", "subject", "resource_type", "description", "is_free",
               "required_referrals", "price", "duration_days", "duration_text",
               "students_count", "thumbnail_emoji", "order_num", "is_active"]
    for key in allowed:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key] if data[key] != "" else None)
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


# ---------- PARAGRAPHS ----------

def get_paragraphs(course_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM paragraphs WHERE course_id = ? ORDER BY order_num ASC, id ASC", (course_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_paragraph(paragraph_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM paragraphs WHERE id = ?", (paragraph_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_paragraph(data: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO paragraphs (course_id, title, order_num) VALUES (?, ?, ?)", (
        int(data["course_id"]), data.get("title", ""), int(data.get("order_num", 0))
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_paragraph(paragraph_id: int, data: dict):
    conn = get_connection()
    cur = conn.cursor()
    fields, values = [], []
    for key in ["title", "order_num"]:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if fields:
        values.append(paragraph_id)
        cur.execute(f"UPDATE paragraphs SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    conn.close()


def delete_paragraph(paragraph_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM paragraphs WHERE id = ?", (paragraph_id,))
    conn.commit()
    conn.close()


# ---------- LESSONS ----------

def get_lessons(paragraph_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM lessons WHERE paragraph_id = ? ORDER BY order_num ASC, id ASC", (paragraph_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_lesson(lesson_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_lesson(data: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO lessons (paragraph_id, title, video_url, description, order_num)
        VALUES (?, ?, ?, ?, ?)
    """, (
        int(data["paragraph_id"]), data.get("title", ""), data.get("video_url", ""),
        data.get("description", ""), int(data.get("order_num", 0))
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_lesson(lesson_id: int, data: dict):
    conn = get_connection()
    cur = conn.cursor()
    fields, values = [], []
    for key in ["title", "video_url", "description", "order_num"]:
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


def count_course_lessons(course_id: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) as c FROM lessons l
        JOIN paragraphs p ON p.id = l.paragraph_id
        WHERE p.course_id = ?
    """, (course_id,))
    c = cur.fetchone()["c"]
    conn.close()
    return c


def count_paragraph_lessons(paragraph_id: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM lessons WHERE paragraph_id = ?", (paragraph_id,))
    c = cur.fetchone()["c"]
    conn.close()
    return c


# ---------- LESSON PROGRESS / COINS ----------

def mark_lesson_watched(telegram_id: int, lesson_id: int) -> bool:
    """Darsni 'ko'rildi' deb belgilaydi va agar birinchi marta bo'lsa 1 coin beradi.
    Coin berilgan bo'lsa True, avval berilgan bo'lsa False qaytaradi."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT coin_awarded FROM lesson_progress WHERE telegram_id = ? AND lesson_id = ?",
                (telegram_id, lesson_id))
    row = cur.fetchone()
    if row is not None:
        conn.close()
        return False  # allaqachon ko'rilgan, qayta coin berilmaydi

    cur.execute("INSERT INTO lesson_progress (telegram_id, lesson_id, coin_awarded) VALUES (?, ?, 1)",
                (telegram_id, lesson_id))
    conn.commit()
    conn.close()
    add_coins(telegram_id, 1)
    return True


def get_watched_lesson_ids(telegram_id: int, course_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT lp.lesson_id FROM lesson_progress lp
        JOIN lessons l ON l.id = lp.lesson_id
        JOIN paragraphs p ON p.id = l.paragraph_id
        WHERE lp.telegram_id = ? AND p.course_id = ?
    """, (telegram_id, course_id))
    ids = [r["lesson_id"] for r in cur.fetchall()]
    conn.close()
    return ids


# ---------- ENROLLMENTS (pullik obuna) ----------

def grant_enrollment(telegram_id: int, course_id: int, duration_days: int = None):
    """Foydalanuvchiga kursga obuna beradi (yoki mavjud obunani uzaytiradi).
    duration_days=None bo'lsa, muddatsiz (lifetime) obuna beriladi."""
    conn = get_connection()
    cur = conn.cursor()

    if duration_days is None:
        expiry = None
    else:
        cur.execute("SELECT expiry_date FROM enrollments WHERE telegram_id = ? AND course_id = ?",
                    (telegram_id, course_id))
        row = cur.fetchone()
        now = datetime.datetime.utcnow()
        if row and row["expiry_date"]:
            current_expiry = datetime.datetime.fromisoformat(row["expiry_date"])
            base = current_expiry if current_expiry > now else now
        else:
            base = now
        expiry = (base + datetime.timedelta(days=duration_days)).isoformat()

    cur.execute("""
        INSERT INTO enrollments (telegram_id, course_id, expiry_date)
        VALUES (?, ?, ?)
        ON CONFLICT(telegram_id, course_id) DO UPDATE SET expiry_date = excluded.expiry_date
    """, (telegram_id, course_id, expiry))
    conn.commit()
    conn.close()


def get_enrollment(telegram_id: int, course_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM enrollments WHERE telegram_id = ? AND course_id = ?", (telegram_id, course_id))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_enrollments(telegram_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT e.*, c.title, c.thumbnail_emoji, c.subject FROM enrollments e
        JOIN courses c ON c.id = e.course_id
        WHERE e.telegram_id = ? ORDER BY e.created_at DESC
    """, (telegram_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


GRACE_PERIOD_DAYS = 2


def compute_course_access(telegram_id: int, course: dict):
    """Kurs uchun kirish holatini hisoblaydi.
    Qaytaradi: {'unlocked': bool, 'reason': 'free'|'referral'|'enrolled'|'grace'|'expired'|'locked',
                'expiry_date': str|None, 'days_left': int|None}
    """
    if course["is_free"]:
        return {"unlocked": True, "reason": "free", "expiry_date": None, "days_left": None}

    if course.get("required_referrals", 0) > 0:
        refs = get_confirmed_referral_count(telegram_id)
        if refs >= course["required_referrals"]:
            return {"unlocked": True, "reason": "referral", "expiry_date": None, "days_left": None}

    if course.get("price", 0) > 0:
        enrollment = get_enrollment(telegram_id, course["id"])
        if enrollment:
            if enrollment["expiry_date"] is None:
                return {"unlocked": True, "reason": "enrolled", "expiry_date": None, "days_left": None}
            expiry = datetime.datetime.fromisoformat(enrollment["expiry_date"])
            now = datetime.datetime.utcnow()
            grace_end = expiry + datetime.timedelta(days=GRACE_PERIOD_DAYS)
            days_left = (expiry - now).days
            if now <= expiry:
                return {"unlocked": True, "reason": "enrolled", "expiry_date": enrollment["expiry_date"], "days_left": days_left}
            elif now <= grace_end:
                return {"unlocked": True, "reason": "grace", "expiry_date": enrollment["expiry_date"], "days_left": days_left}
            else:
                return {"unlocked": False, "reason": "expired", "expiry_date": enrollment["expiry_date"], "days_left": days_left}

    return {"unlocked": False, "reason": "locked", "expiry_date": None, "days_left": None}


# ---------- LEADERBOARD ----------

def get_leaderboard(limit: int = 100):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT telegram_id, first_name, coins FROM users
        WHERE coins > 0 ORDER BY coins DESC, id ASC LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_user_rank(telegram_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT coins FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    my_coins = row["coins"]
    cur.execute("SELECT COUNT(*) as c FROM users WHERE coins > ?", (my_coins,))
    rank = cur.fetchone()["c"] + 1
    conn.close()
    return rank


# ---------- TESTLAR ----------

DIFFICULTY_TIME_SECONDS = {
    "oson": 300,      # 5 daqiqa
    "orta": 600,      # 10 daqiqa
    "qiyin": 900,     # 15 daqiqa
}


def get_all_tests(subject: str = None, only_active: bool = True):
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT * FROM tests WHERE 1=1"
    params = []
    if subject:
        query += " AND subject = ?"
        params.append(subject)
    if only_active:
        query += " AND is_active = 1"
    query += " ORDER BY order_num ASC, id ASC"
    cur.execute(query, params)
    tests = [dict(row) for row in cur.fetchall()]
    conn.close()
    return tests


def get_test(test_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tests WHERE id = ?", (test_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def count_test_questions(test_id: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM test_questions WHERE test_id = ?", (test_id,))
    c = cur.fetchone()["c"]
    conn.close()
    return c


def create_test(data: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    difficulty = data.get("difficulty", "orta")
    time_limit = data.get("time_limit_seconds") or DIFFICULTY_TIME_SECONDS.get(difficulty, 600)
    cur.execute("""
        INSERT INTO tests (subject, title, difficulty, time_limit_seconds, order_num, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data.get("subject", ""), data.get("title", ""), difficulty, int(time_limit),
        int(data.get("order_num", 0)), int(data.get("is_active", 1))
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_test(test_id: int, data: dict):
    conn = get_connection()
    cur = conn.cursor()
    fields, values = [], []
    for key in ["subject", "title", "difficulty", "time_limit_seconds", "order_num", "is_active"]:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if fields:
        values.append(test_id)
        cur.execute(f"UPDATE tests SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    conn.close()


def delete_test(test_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM tests WHERE id = ?", (test_id,))
    conn.commit()
    conn.close()


# ---------- SAVOLLAR ----------

def get_questions(test_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM test_questions WHERE test_id = ? ORDER BY order_num ASC, id ASC", (test_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_question(question_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM test_questions WHERE id = ?", (question_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_question(data: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO test_questions (test_id, question_text, image_url, option_1, option_2, option_3, option_4, correct_index, order_num)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        int(data["test_id"]), data.get("question_text", ""), data.get("image_url", ""),
        data.get("option_1", ""), data.get("option_2", ""), data.get("option_3", ""), data.get("option_4", ""),
        int(data.get("correct_index", 1)), int(data.get("order_num", 0))
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_question(question_id: int, data: dict):
    conn = get_connection()
    cur = conn.cursor()
    fields, values = [], []
    for key in ["question_text", "image_url", "option_1", "option_2", "option_3", "option_4", "correct_index", "order_num"]:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if fields:
        values.append(question_id)
        cur.execute(f"UPDATE test_questions SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    conn.close()


def delete_question(question_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM test_questions WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()


# ---------- TEST TOPSHIRISH (attempt) ----------

def start_attempt(telegram_id: int, test_id: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    total = count_test_questions(test_id)
    cur.execute("""
        INSERT INTO test_attempts (telegram_id, test_id, total_questions) VALUES (?, ?, ?)
    """, (telegram_id, test_id, total))
    conn.commit()
    attempt_id = cur.lastrowid
    conn.close()
    return attempt_id


def submit_answer(telegram_id: int, attempt_id: int, question_id: int, selected_index: int):
    """Javobni tekshiradi, yozib qo'yadi, va agar bu savolga birinchi marta to'g'ri
    javob berilgan bo'lsa 1 coin beradi. {'correct': bool, 'correct_index': int, 'coin_awarded': bool} qaytaradi."""
    question = get_question(question_id)
    if not question:
        return {"correct": False, "correct_index": None, "coin_awarded": False}

    is_correct = int(selected_index) == int(question["correct_index"])

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO test_answers (attempt_id, question_id, selected_index, is_correct)
        VALUES (?, ?, ?, ?)
    """, (attempt_id, question_id, selected_index, 1 if is_correct else 0))
    if is_correct:
        cur.execute("UPDATE test_attempts SET score = score + 1 WHERE id = ?", (attempt_id,))
    conn.commit()
    conn.close()

    coin_awarded = False
    if is_correct:
        conn2 = get_connection()
        cur2 = conn2.cursor()
        cur2.execute("SELECT id FROM user_question_progress WHERE telegram_id = ? AND question_id = ?",
                     (telegram_id, question_id))
        already = cur2.fetchone()
        if already is None:
            cur2.execute("INSERT INTO user_question_progress (telegram_id, question_id, coin_awarded) VALUES (?, ?, 1)",
                         (telegram_id, question_id))
            conn2.commit()
            add_coins(telegram_id, 1)
            coin_awarded = True
        conn2.close()

    return {"correct": is_correct, "correct_index": question["correct_index"], "coin_awarded": coin_awarded}


def finish_attempt(attempt_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE test_attempts SET finished_at = CURRENT_TIMESTAMP WHERE id = ?", (attempt_id,))
    conn.commit()
    cur.execute("SELECT * FROM test_attempts WHERE id = ?", (attempt_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_attempt(attempt_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM test_attempts WHERE id = ?", (attempt_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_test_results(telegram_id: int):
    """Foydalanuvchining har bir test bo'yicha eng yaxshi natijasini qaytaradi (Natijalar bo'limi uchun)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.id as test_id, t.title, t.subject, MAX(a.score) as best_score, a.total_questions
        FROM test_attempts a
        JOIN tests t ON t.id = a.test_id
        WHERE a.telegram_id = ? AND a.finished_at IS NOT NULL
        GROUP BY t.id
        ORDER BY t.order_num ASC
    """, (telegram_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ---------- SAMPLE DATA ----------

def add_sample_courses():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM courses")
    count = cur.fetchone()["c"]
    if count == 0:
        cur.execute("""
            INSERT INTO courses (title, subject, resource_type, description, is_free,
                required_referrals, price, duration_days, duration_text, students_count,
                thumbnail_emoji, order_num, is_active)
            VALUES ('Mavzulashtirilgan masala kursi', 'Kimyo', 'course', '2000 dan ortiq masalalar',
                0, 1, 0, NULL, '3 oy', 0, '🧪', 1, 1)
        """)
        course_id = cur.lastrowid
        cur.execute("INSERT INTO paragraphs (course_id, title, order_num) VALUES (?, ?, ?)",
                    (course_id, "1-§. Kirish", 1))
        conn.commit()
    conn.close()
