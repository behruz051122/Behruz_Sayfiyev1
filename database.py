# database.py
# Barcha ma'lumotlar bazasi funksiyalari (v4 — ulanishlar puli bilan)
#
# XAVFSIZLIK/ARXITEKTURA YANGILANISHI:
# Endi har bir funksiya sqlite3.connect()/close() ni to'g'ridan-to'g'ri chaqirmaydi,
# buning o'rniga db_pool.get_connection() orqali puldagi tayyor ulanishlardan
# birini oladi va ishlatib bo'lgach avtomatik qaytaradi. Funksiyalarning tashqi
# xatti-harakati (qabul qiladigan parametrlar, qaytaradigan natijalar) BUTUNLAY
# O'ZGARMAGAN — faqat ulanish bilan ishlash usuli yaxshilandi.

import sqlite3
import datetime

from db_pool import get_connection, init_pool
from config import DB_PATH


def init_db():
    init_pool()
    with get_connection() as conn:
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

        try:
            cur.execute("ALTER TABLE lessons ADD COLUMN image_url TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

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

        try:
            cur.execute("ALTER TABLE enrollments ADD COLUMN reminder_sent_at TIMESTAMP")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

        cur.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_telegram_id INTEGER NOT NULL,
                referred_telegram_id INTEGER UNIQUE NOT NULL,
                confirmed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

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

        # Nazorat testlari — o'qituvchi tomonidan o'z kursiga yozilgan
        # o'quvchilar uchun beriladigan, alohida oylik reytingga ega maxsus
        # testlar. Bir xil "tests" jadvalidan foydalanadi, faqat shu ikki
        # ustun bilan ajratiladi.
        try:
            cur.execute("ALTER TABLE tests ADD COLUMN is_control_test INTEGER DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

        try:
            cur.execute("ALTER TABLE tests ADD COLUMN course_id INTEGER")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

        # Nazorat testiga TO'G'RIDAN-TO'G'RI (kursdan mustaqil) tayinlangan
        # o'quvchilar ro'yxati. Admin panelda o'qituvchi aynan qaysi
        # talabalarga shu nazorat testini topshirishga ruxsat berishni
        # birma-bir tanlaydi — bu kursga yozilishdan alohida, qo'shimcha
        # kirish yo'li (ikkalasi ham ishlaydi: kurs ORQALI yoki to'g'ridan-to'g'ri tayinlash orqali).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS control_test_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER NOT NULL,
                telegram_id INTEGER NOT NULL,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(test_id, telegram_id),
                FOREIGN KEY (test_id) REFERENCES tests (id) ON DELETE CASCADE
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
                table_data TEXT,
                FOREIGN KEY (test_id) REFERENCES tests (id) ON DELETE CASCADE
            )
        """)

        # Word'dan ommaviy import qilinganda savol ichida haqiqiy Word jadvali
        # (masalan davriy jadval ma'lumotlari, izotoplar foizi) bo'lishi mumkin.
        # Buni matn sifatida qo'shib yubormasdan, JSON qatorlar ro'yxati
        # ({"tables": [{"rows": [[...], ...]}, ...]}) sifatida saqlaymiz — shunda
        # frontend uni ORIGINAL katak-katak jadval ko'rinishida chizadi. Fayl
        # yuqoridagi CREATE TABLE'da yangi o'rnatishlar uchun ustunni to'g'ridan
        # to'g'ri qo'shadi; ALLAQACHON DEPLOY QILINGAN (Railway'dagi) bazalarda
        # esa jadval CREATE TABLE bosqichida o'tkazib yuboriladi (IF NOT EXISTS),
        # shuning uchun bu yerda ALTER TABLE orqali qo'shib qo'yamiz.
        try:
            cur.execute("ALTER TABLE test_questions ADD COLUMN table_data TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

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

        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_question_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                coin_awarded INTEGER DEFAULT 0,
                UNIQUE(telegram_id, question_id)
            )
        """)

        # ---------- DTM/Milliy sertifikat SIMULYATORI ----------
        # Bir nechta fandan tasodifiy tanlangan savollarni birlashtirib,
        # yagona vaqtli imtihon sifatida topshirish tizimi.

        cur.execute("""
            CREATE TABLE IF NOT EXISTS simulators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                time_limit_seconds INTEGER DEFAULT 10800,
                order_num INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS simulator_subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulator_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                question_count INTEGER NOT NULL DEFAULT 10,
                order_num INTEGER DEFAULT 0,
                FOREIGN KEY (simulator_id) REFERENCES simulators (id) ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS simulator_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                simulator_id INTEGER NOT NULL,
                score INTEGER DEFAULT 0,
                total_questions INTEGER DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS simulator_attempt_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                order_num INTEGER DEFAULT 0,
                FOREIGN KEY (attempt_id) REFERENCES simulator_attempts (id) ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS simulator_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                selected_index INTEGER,
                is_correct INTEGER DEFAULT 0,
                FOREIGN KEY (attempt_id) REFERENCES simulator_attempts (id) ON DELETE CASCADE
            )
        """)

        conn.commit()
    print("Baza tayyor (v5 — DTM simulyatori bilan): users, courses, paragraphs, lessons, "
          "lesson_progress, enrollments, referrals, tests, simulators.")


# ---------- USERS ----------

def get_or_create_user(telegram_id: int, first_name: str, username: str = None, referred_by: int = None):
    with get_connection() as conn:
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
        return dict(user)


def set_user_subscribed(telegram_id: int, value: bool = True):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET is_subscribed = ? WHERE telegram_id = ?", (1 if value else 0, telegram_id))
        conn.commit()


def search_users(query: str, limit: int = 20):
    """Admin panelda nazorat testiga talaba tayinlash uchun foydalanuvchi
    qidiradi — ism, username yoki Telegram ID bo'yicha. Bo'sh so'rovda eng
    so'nggi ro'yxatdan o'tganlarni qaytaradi (ro'yxatni boshlash uchun qulay)."""
    query = (query or "").strip()
    with get_connection() as conn:
        cur = conn.cursor()
        if not query:
            cur.execute(
                "SELECT telegram_id, first_name, username FROM users ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return [dict(r) for r in cur.fetchall()]

        if query.isdigit():
            cur.execute(
                """SELECT telegram_id, first_name, username FROM users
                   WHERE telegram_id = ? OR CAST(telegram_id AS TEXT) LIKE ?
                   ORDER BY id DESC LIMIT ?""",
                (int(query), f"%{query}%", limit)
            )
        else:
            like = f"%{query}%"
            cur.execute(
                """SELECT telegram_id, first_name, username FROM users
                   WHERE first_name LIKE ? OR username LIKE ?
                   ORDER BY id DESC LIMIT ?""",
                (like, like, limit)
            )
        return [dict(r) for r in cur.fetchall()]


def add_coins(telegram_id: int, amount: int = 1):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET coins = coins + ? WHERE telegram_id = ?", (amount, telegram_id))
        conn.commit()


# ---------- REFERRALS ----------

def create_pending_referral(referrer_id: int, referred_id: int):
    if referrer_id == referred_id:
        return
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM referrals WHERE referred_telegram_id = ?", (referred_id,))
        if cur.fetchone() is None:
            cur.execute(
                "INSERT INTO referrals (referrer_telegram_id, referred_telegram_id, confirmed) VALUES (?, ?, 0)",
                (referrer_id, referred_id)
            )
            conn.commit()


def confirm_referral(referred_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT referrer_telegram_id, confirmed FROM referrals WHERE referred_telegram_id = ?", (referred_id,))
        row = cur.fetchone()
        if row is None:
            return None
        if row["confirmed"] == 0:
            cur.execute("UPDATE referrals SET confirmed = 1 WHERE referred_telegram_id = ?", (referred_id,))
            conn.commit()
        return row["referrer_telegram_id"]


def get_confirmed_referral_count(telegram_id: int) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM referrals WHERE referrer_telegram_id = ? AND confirmed = 1", (telegram_id,))
        return cur.fetchone()["c"]


def get_referral_progress(telegram_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT r.referred_telegram_id, r.confirmed, u.first_name
            FROM referrals r LEFT JOIN users u ON u.telegram_id = r.referred_telegram_id
            WHERE r.referrer_telegram_id = ? ORDER BY r.created_at DESC
        """, (telegram_id,))
        return [dict(r) for r in cur.fetchall()]


# ---------- COURSES ----------

def get_all_courses(resource_type: str = None, only_active: bool = True):
    with get_connection() as conn:
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
        return [dict(row) for row in cur.fetchall()]


def get_course(course_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_course(data: dict) -> int:
    with get_connection() as conn:
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
        return cur.lastrowid


def update_course(course_id: int, data: dict):
    with get_connection() as conn:
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


def delete_course(course_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        conn.commit()


# ---------- PARAGRAPHS ----------

def get_paragraphs(course_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM paragraphs WHERE course_id = ? ORDER BY order_num ASC, id ASC", (course_id,))
        return [dict(r) for r in cur.fetchall()]


def get_paragraph(paragraph_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM paragraphs WHERE id = ?", (paragraph_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_paragraph(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO paragraphs (course_id, title, order_num) VALUES (?, ?, ?)", (
            int(data["course_id"]), data.get("title", ""), int(data.get("order_num", 0))
        ))
        conn.commit()
        return cur.lastrowid


def update_paragraph(paragraph_id: int, data: dict):
    with get_connection() as conn:
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


def delete_paragraph(paragraph_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM paragraphs WHERE id = ?", (paragraph_id,))
        conn.commit()


# ---------- LESSONS ----------

def get_lessons(paragraph_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM lessons WHERE paragraph_id = ? ORDER BY order_num ASC, id ASC", (paragraph_id,))
        return [dict(r) for r in cur.fetchall()]


def get_lesson(lesson_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_lesson(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO lessons (paragraph_id, title, video_url, image_url, description, order_num)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            int(data["paragraph_id"]), data.get("title", ""), data.get("video_url", ""),
            data.get("image_url", ""), data.get("description", ""), int(data.get("order_num", 0))
        ))
        conn.commit()
        return cur.lastrowid


def update_lesson(lesson_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        for key in ["title", "video_url", "image_url", "description", "order_num"]:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if fields:
            values.append(lesson_id)
            cur.execute(f"UPDATE lessons SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_lesson(lesson_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
        conn.commit()


def count_course_lessons(course_id: int) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as c FROM lessons l
            JOIN paragraphs p ON p.id = l.paragraph_id
            WHERE p.course_id = ?
        """, (course_id,))
        return cur.fetchone()["c"]


def count_paragraph_lessons(paragraph_id: int) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM lessons WHERE paragraph_id = ?", (paragraph_id,))
        return cur.fetchone()["c"]


# ---------- LESSON PROGRESS / COINS ----------

def mark_lesson_watched(telegram_id: int, lesson_id: int) -> bool:
    """Darsni 'ko'rildi' deb belgilaydi va agar birinchi marta bo'lsa 1 coin beradi.
    Coin berilgan bo'lsa True, avval berilgan bo'lsa False qaytaradi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT coin_awarded FROM lesson_progress WHERE telegram_id = ? AND lesson_id = ?",
                    (telegram_id, lesson_id))
        row = cur.fetchone()
        if row is not None:
            return False  # allaqachon ko'rilgan, qayta coin berilmaydi

        cur.execute("INSERT INTO lesson_progress (telegram_id, lesson_id, coin_awarded) VALUES (?, ?, 1)",
                    (telegram_id, lesson_id))
        conn.commit()

    add_coins(telegram_id, 1)  # oldingi 'with' bloki yopilgach — pooldan bo'sh ulanish oladi
    return True


def get_watched_lesson_ids(telegram_id: int, course_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT lp.lesson_id FROM lesson_progress lp
            JOIN lessons l ON l.id = lp.lesson_id
            JOIN paragraphs p ON p.id = l.paragraph_id
            WHERE lp.telegram_id = ? AND p.course_id = ?
        """, (telegram_id, course_id))
        return [r["lesson_id"] for r in cur.fetchall()]


# ---------- ENROLLMENTS (pullik obuna) ----------

def grant_enrollment(telegram_id: int, course_id: int, duration_days: int = None):
    """Foydalanuvchiga kursga obuna beradi (yoki mavjud obunani uzaytiradi).
    duration_days=None bo'lsa, muddatsiz (lifetime) obuna beriladi."""
    with get_connection() as conn:
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


def get_enrollment(telegram_id: int, course_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM enrollments WHERE telegram_id = ? AND course_id = ?", (telegram_id, course_id))
        row = cur.fetchone()
        return dict(row) if row else None


def get_user_enrollments(telegram_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT e.*, c.title, c.thumbnail_emoji, c.subject FROM enrollments e
            JOIN courses c ON c.id = e.course_id
            WHERE e.telegram_id = ? ORDER BY e.created_at DESC
        """, (telegram_id,))
        return [dict(r) for r in cur.fetchall()]


# ---------- OBUNA MUDDATI ESLATMALARI ----------

REMINDER_WINDOW_DAYS = 2  # muddat tugashiga shuncha kun (yoki kamroq) qolganda eslatma yuboriladi


def get_enrollments_needing_reminder():
    """Muddati tez orada tugaydigan (yoki yaqinda tugagan, grace muddatida)
    va hali eslatma yuborilmagan obunalarni topadi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT e.id, e.telegram_id, e.course_id, e.expiry_date, c.title as course_title
            FROM enrollments e
            JOIN courses c ON c.id = e.course_id
            WHERE e.expiry_date IS NOT NULL
              AND e.reminder_sent_at IS NULL
              AND julianday(e.expiry_date) - julianday('now') <= ?
        """, (REMINDER_WINDOW_DAYS,))
        return [dict(r) for r in cur.fetchall()]


def mark_reminder_sent(enrollment_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE enrollments SET reminder_sent_at = CURRENT_TIMESTAMP WHERE id = ?", (enrollment_id,))
        conn.commit()


# ---------- ANALITIKA (o'qituvchi dashboardi) ----------

def get_analytics_summary():
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) as c FROM users")
        total_users = cur.fetchone()["c"]

        cur.execute("SELECT COALESCE(SUM(coins), 0) as s FROM users")
        total_coins = cur.fetchone()["s"]

        cur.execute("SELECT COUNT(*) as c FROM lesson_progress")
        total_lessons_watched = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) as c FROM test_attempts WHERE finished_at IS NOT NULL")
        total_test_attempts = cur.fetchone()["c"]

        cur.execute("""
            SELECT AVG(CAST(score AS FLOAT) / NULLIF(total_questions, 0)) as avg
            FROM test_attempts WHERE finished_at IS NOT NULL
        """)
        row = cur.fetchone()
        avg_test_score_percent = round((row["avg"] or 0) * 100, 1)

        cur.execute("SELECT COUNT(*) as c FROM referrals WHERE confirmed = 1")
        confirmed_referrals = cur.fetchone()["c"]

        cur.execute("""
            SELECT c.title, COUNT(lp.id) as watch_count
            FROM lesson_progress lp
            JOIN lessons l ON l.id = lp.lesson_id
            JOIN paragraphs p ON p.id = l.paragraph_id
            JOIN courses c ON c.id = p.course_id
            GROUP BY c.id ORDER BY watch_count DESC LIMIT 5
        """)
        top_courses = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT t.title, COUNT(a.id) as attempt_count
            FROM test_attempts a JOIN tests t ON t.id = a.test_id
            WHERE a.finished_at IS NOT NULL
            GROUP BY t.id ORDER BY attempt_count DESC LIMIT 5
        """)
        top_tests = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT COUNT(*) as cnt, COALESCE(SUM(c2.price), 0) as revenue
            FROM enrollments e JOIN courses c2 ON c2.id = e.course_id
            WHERE c2.price > 0
        """)
        row = cur.fetchone()

        return {
            "total_users": total_users,
            "total_coins": total_coins,
            "total_lessons_watched": total_lessons_watched,
            "total_test_attempts": total_test_attempts,
            "avg_test_score_percent": avg_test_score_percent,
            "confirmed_referrals": confirmed_referrals,
            "top_courses": top_courses,
            "top_tests": top_tests,
            "paid_enrollments_count": row["cnt"],
            "estimated_revenue": row["revenue"],
        }


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
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT telegram_id, first_name, coins FROM users
            WHERE coins > 0 ORDER BY coins DESC, id ASC LIMIT ?
        """, (limit,))
        return [dict(r) for r in cur.fetchall()]


def get_user_rank(telegram_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT coins FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        if not row:
            return None
        my_coins = row["coins"]
        cur.execute("SELECT COUNT(*) as c FROM users WHERE coins > ?", (my_coins,))
        return cur.fetchone()["c"] + 1


# ---------- TESTLAR ----------

DIFFICULTY_TIME_SECONDS = {
    "oson": 300,      # 5 daqiqa
    "orta": 600,      # 10 daqiqa
    "qiyin": 900,     # 15 daqiqa
}


def get_all_tests(subject: str = None, only_active: bool = True, include_control: bool = True):
    with get_connection() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM tests WHERE 1=1"
        params = []
        if subject:
            query += " AND subject = ?"
            params.append(subject)
        if only_active:
            query += " AND is_active = 1"
        if not include_control:
            query += " AND (is_control_test IS NULL OR is_control_test = 0)"
        query += " ORDER BY order_num ASC, id ASC"
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def get_test(test_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM tests WHERE id = ?", (test_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def count_test_questions(test_id: int) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM test_questions WHERE test_id = ?", (test_id,))
        return cur.fetchone()["c"]


def create_test(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        difficulty = data.get("difficulty", "orta")
        time_limit = data.get("time_limit_seconds") or DIFFICULTY_TIME_SECONDS.get(difficulty, 600)
        cur.execute("""
            INSERT INTO tests (subject, title, difficulty, time_limit_seconds, order_num, is_active, is_control_test, course_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("subject", ""), data.get("title", ""), difficulty, int(time_limit),
            int(data.get("order_num", 0)), int(data.get("is_active", 1)),
            int(data.get("is_control_test", 0)), data.get("course_id") or None
        ))
        conn.commit()
        return cur.lastrowid


def update_test(test_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        for key in ["subject", "title", "difficulty", "time_limit_seconds", "order_num", "is_active",
                    "is_control_test", "course_id"]:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key] if data[key] != "" else None)
        if fields:
            values.append(test_id)
            cur.execute(f"UPDATE tests SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_test(test_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM tests WHERE id = ?", (test_id,))
        conn.commit()


# ---------- SAVOLLAR ----------

def get_questions(test_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM test_questions WHERE test_id = ? ORDER BY order_num ASC, id ASC", (test_id,))
        return [dict(r) for r in cur.fetchall()]


def get_question(question_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM test_questions WHERE id = ?", (question_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_question(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO test_questions (test_id, question_text, image_url, option_1, option_2, option_3, option_4, correct_index, order_num, table_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            int(data["test_id"]), data.get("question_text", ""), data.get("image_url", ""),
            data.get("option_1", ""), data.get("option_2", ""), data.get("option_3", ""), data.get("option_4", ""),
            int(data.get("correct_index", 1)), int(data.get("order_num", 0)), data.get("table_data") or None
        ))
        conn.commit()
        return cur.lastrowid


def update_question(question_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        for key in ["question_text", "image_url", "option_1", "option_2", "option_3", "option_4", "correct_index", "order_num", "table_data"]:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if fields:
            values.append(question_id)
            cur.execute(f"UPDATE test_questions SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_question(question_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM test_questions WHERE id = ?", (question_id,))
        conn.commit()


# ---------- TEST TOPSHIRISH (attempt) ----------

def start_attempt(telegram_id: int, test_id: int) -> int:
    total = count_test_questions(test_id)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO test_attempts (telegram_id, test_id, total_questions) VALUES (?, ?, ?)
        """, (telegram_id, test_id, total))
        conn.commit()
        return cur.lastrowid


def submit_answer(telegram_id: int, attempt_id: int, question_id: int, selected_index: int):
    """Javobni tekshiradi, yozib qo'yadi, va agar bu savolga birinchi marta to'g'ri
    javob berilgan bo'lsa 1 coin beradi. {'correct': bool, 'correct_index': int, 'coin_awarded': bool} qaytaradi."""
    question = get_question(question_id)
    if not question:
        return {"correct": False, "correct_index": None, "coin_awarded": False}

    is_correct = int(selected_index) == int(question["correct_index"])

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO test_answers (attempt_id, question_id, selected_index, is_correct)
            VALUES (?, ?, ?, ?)
        """, (attempt_id, question_id, selected_index, 1 if is_correct else 0))
        if is_correct:
            cur.execute("UPDATE test_attempts SET score = score + 1 WHERE id = ?", (attempt_id,))
        conn.commit()

    coin_awarded = False
    if is_correct:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM user_question_progress WHERE telegram_id = ? AND question_id = ?",
                        (telegram_id, question_id))
            already = cur.fetchone()
            if already is None:
                cur.execute("INSERT INTO user_question_progress (telegram_id, question_id, coin_awarded) VALUES (?, ?, 1)",
                            (telegram_id, question_id))
                conn.commit()
                coin_awarded = True
        if coin_awarded:
            add_coins(telegram_id, 1)  # 'with' bloki yopilgach chaqiriladi — pool bandlanib qolmaydi

    return {"correct": is_correct, "correct_index": question["correct_index"], "coin_awarded": coin_awarded}


def finish_attempt(attempt_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE test_attempts SET finished_at = CURRENT_TIMESTAMP WHERE id = ?", (attempt_id,))
        conn.commit()
        cur.execute("SELECT * FROM test_attempts WHERE id = ?", (attempt_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_attempt(attempt_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM test_attempts WHERE id = ?", (attempt_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_user_test_results(telegram_id: int):
    """Foydalanuvchining har bir test bo'yicha eng yaxshi natijasini qaytaradi (Natijalar bo'limi uchun)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.id as test_id, t.title, t.subject, MAX(a.score) as best_score, a.total_questions
            FROM test_attempts a
            JOIN tests t ON t.id = a.test_id
            WHERE a.telegram_id = ? AND a.finished_at IS NOT NULL
            GROUP BY t.id
            ORDER BY t.order_num ASC
        """, (telegram_id,))
        return [dict(r) for r in cur.fetchall()]


# ---------- SAMPLE DATA ----------

def add_sample_courses():
    with get_connection() as conn:
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


# ---------- DTM/MILLIY SERTIFIKAT SIMULYATORI ----------

def get_subject_pools():
    """Har bir fan bo'yicha savollar to'plamida jami nechta savol borligini
    qaytaradi — admin simulyator sozlashda "yetarlimi" ni ko'rish uchun.
    Fan nomlari registr va bo'shliqqa sezgir bo'lmasdan birlashtiriladi
    (masalan "Kimyo" va "kimyo " bir xil fan sifatida hisoblanadi)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT TRIM(t.subject) as subject, COUNT(q.id) as question_count
            FROM tests t JOIN test_questions q ON q.test_id = t.id
            GROUP BY LOWER(TRIM(t.subject)) ORDER BY subject
        """)
        return [dict(r) for r in cur.fetchall()]


def get_all_simulators(only_active: bool = True):
    with get_connection() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM simulators WHERE 1=1"
        if only_active:
            query += " AND is_active = 1"
        query += " ORDER BY order_num ASC, id ASC"
        cur.execute(query)
        return [dict(r) for r in cur.fetchall()]


def get_simulator(simulator_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM simulators WHERE id = ?", (simulator_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_simulator(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO simulators (title, description, time_limit_seconds, order_num, is_active)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data.get("title", ""), data.get("description", ""),
            int(data.get("time_limit_seconds", 10800)),
            int(data.get("order_num", 0)), int(data.get("is_active", 1))
        ))
        conn.commit()
        return cur.lastrowid


def update_simulator(simulator_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        for key in ["title", "description", "time_limit_seconds", "order_num", "is_active"]:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if fields:
            values.append(simulator_id)
            cur.execute(f"UPDATE simulators SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_simulator(simulator_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM simulators WHERE id = ?", (simulator_id,))
        conn.commit()


def get_simulator_subjects(simulator_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM simulator_subjects WHERE simulator_id = ? ORDER BY order_num ASC, id ASC
        """, (simulator_id,))
        return [dict(r) for r in cur.fetchall()]


def add_simulator_subject(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO simulator_subjects (simulator_id, subject, question_count, order_num)
            VALUES (?, ?, ?, ?)
        """, (
            int(data["simulator_id"]), data.get("subject", "").strip(),
            int(data.get("question_count", 10)), int(data.get("order_num", 0))
        ))
        conn.commit()
        return cur.lastrowid


def delete_simulator_subject(entry_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM simulator_subjects WHERE id = ?", (entry_id,))
        conn.commit()


def start_simulator_attempt(telegram_id: int, simulator_id: int):
    """Har bir fandan tasodifiy savollarni tanlab, yangi simulyator urinishini
    boshlaydi. Tanlangan savollar 'suratga olinadi' (snapshot) — shu bilan
    urinish davomida savollar o'zgarmasligi va to'g'ri baholash kafolatlanadi."""
    subjects = get_simulator_subjects(simulator_id)
    if not subjects:
        return None

    selected_questions = []  # [(question_id, subject), ...]
    with get_connection() as conn:
        cur = conn.cursor()
        for s in subjects:
            cur.execute("""
                SELECT q.id FROM test_questions q
                JOIN tests t ON t.id = q.test_id
                WHERE LOWER(TRIM(t.subject)) = LOWER(TRIM(?))
                ORDER BY RANDOM() LIMIT ?
            """, (s["subject"], s["question_count"]))
            for row in cur.fetchall():
                selected_questions.append((row["id"], s["subject"]))

        if not selected_questions:
            return None

        cur.execute("""
            INSERT INTO simulator_attempts (telegram_id, simulator_id, total_questions)
            VALUES (?, ?, ?)
        """, (telegram_id, simulator_id, len(selected_questions)))
        attempt_id = cur.lastrowid

        for idx, (question_id, subject) in enumerate(selected_questions):
            cur.execute("""
                INSERT INTO simulator_attempt_questions (attempt_id, question_id, subject, order_num)
                VALUES (?, ?, ?, ?)
            """, (attempt_id, question_id, subject, idx))
        conn.commit()

    return {"attempt_id": attempt_id, "total_questions": len(selected_questions)}


def get_simulator_attempt_questions(attempt_id: int):
    """Shu urinish uchun 'suratga olingan' savollarni, to'g'ri javobsiz, tartib
    bo'yicha qaytaradi (foydalanuvchiga ko'rsatish uchun xavfsiz)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT saq.order_num, saq.subject, q.id, q.question_text, q.image_url, q.table_data,
                   q.option_1, q.option_2, q.option_3, q.option_4
            FROM simulator_attempt_questions saq
            JOIN test_questions q ON q.id = saq.question_id
            WHERE saq.attempt_id = ?
            ORDER BY saq.order_num ASC
        """, (attempt_id,))
        return [dict(r) for r in cur.fetchall()]


def submit_simulator_answer(telegram_id: int, attempt_id: int, question_id: int, selected_index: int):
    """Oddiy testlardagi bilan bir xil mantiq — coin berish uchun ham xuddi
    shu 'user_question_progress' jadvali ishlatiladi, shuning uchun bir marta
    biror savolga (oddiy testda yoki simulyatorda) to'g'ri javob berilgan
    bo'lsa, ikkinchisida qayta coin berilmaydi (adolatli va izchil)."""
    question = get_question(question_id)
    if not question:
        return {"correct": False, "correct_index": None, "coin_awarded": False}

    is_correct = int(selected_index) == int(question["correct_index"])

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO simulator_answers (attempt_id, question_id, selected_index, is_correct)
            VALUES (?, ?, ?, ?)
        """, (attempt_id, question_id, selected_index, 1 if is_correct else 0))
        if is_correct:
            cur.execute("UPDATE simulator_attempts SET score = score + 1 WHERE id = ?", (attempt_id,))
        conn.commit()

    coin_awarded = False
    if is_correct:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM user_question_progress WHERE telegram_id = ? AND question_id = ?",
                        (telegram_id, question_id))
            already = cur.fetchone()
            if already is None:
                cur.execute("INSERT INTO user_question_progress (telegram_id, question_id, coin_awarded) VALUES (?, ?, 1)",
                            (telegram_id, question_id))
                conn.commit()
                coin_awarded = True
        if coin_awarded:
            add_coins(telegram_id, 1)

    return {"correct": is_correct, "correct_index": question["correct_index"], "coin_awarded": coin_awarded}


def finish_simulator_attempt(attempt_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE simulator_attempts SET finished_at = CURRENT_TIMESTAMP WHERE id = ?", (attempt_id,))
        conn.commit()
        cur.execute("SELECT * FROM simulator_attempts WHERE id = ?", (attempt_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_simulator_attempt(attempt_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM simulator_attempts WHERE id = ?", (attempt_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_user_simulator_results(telegram_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT s.id as simulator_id, s.title, MAX(a.score) as best_score, a.total_questions
            FROM simulator_attempts a
            JOIN simulators s ON s.id = a.simulator_id
            WHERE a.telegram_id = ? AND a.finished_at IS NOT NULL
            GROUP BY s.id
            ORDER BY s.order_num ASC
        """, (telegram_id,))
        return [dict(r) for r in cur.fetchall()]


# ---------- NATIJALAR DINAMIKASI (progress grafigi) ----------

def get_user_progress_history(telegram_id: int, limit: int = 30):
    """Oddiy testlar VA simulyator urinishlarini birlashtirib, xronologik
    tartibda (eng eskisidan eng yangisigacha) qaytaradi — 'natijalar
    dinamikasi' grafigini chizish uchun."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT a.finished_at as finished_at, a.score as score,
                   a.total_questions as total_questions, t.title as title, 'test' as kind
            FROM test_attempts a JOIN tests t ON t.id = a.test_id
            WHERE a.telegram_id = ? AND a.finished_at IS NOT NULL

            UNION ALL

            SELECT sa.finished_at as finished_at, sa.score as score,
                   sa.total_questions as total_questions, s.title as title, 'simulator' as kind
            FROM simulator_attempts sa JOIN simulators s ON s.id = sa.simulator_id
            WHERE sa.telegram_id = ? AND sa.finished_at IS NOT NULL

            ORDER BY finished_at ASC
            LIMIT ?
        """, (telegram_id, telegram_id, limit))
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            r["percent"] = round((r["score"] / r["total_questions"]) * 100, 1) if r["total_questions"] else 0
        return rows


# ---------- NAZORAT TESTLARI (talabaga tayinlangan va/yoki kursga bog'langan, oylik reytingli) ----------

def user_has_control_test_access(test_id: int, telegram_id: int) -> bool:
    """Ushbu talaba shu nazorat testiga ADMIN tomonidan to'g'ridan-to'g'ri
    tayinlanganmi (kursdan mustaqil)?"""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM control_test_access WHERE test_id = ? AND telegram_id = ?",
            (test_id, telegram_id)
        )
        return cur.fetchone() is not None


def compute_control_test_access(telegram_id: int, test: dict):
    """Nazorat testiga kirish huquqini hisoblaydi. Ikki mustaqil yo'l bor —
    ULARDAN BIRI YETARLI:
      1) Admin panelda o'quvchi shu testga BEVOSITA tayinlangan bo'lsa
         (control_test_access jadvali) — bu asosiy, tavsiya etilgan usul.
      2) Test bir kursga bog'langan bo'lsa (course_id) va o'quvchi shu
         kursga kirish huquqiga ega bo'lsa (bepul/referal/pullik obuna).
    Qaytaradi: {'unlocked': bool, 'reason': 'assigned'|'course'|'locked', 'course_title': str|None}
    """
    if user_has_control_test_access(test["id"], telegram_id):
        course = get_course(test["course_id"]) if test.get("course_id") else None
        return {"unlocked": True, "reason": "assigned", "course_title": course["title"] if course else None}

    course = get_course(test["course_id"]) if test.get("course_id") else None
    if course:
        access = compute_course_access(telegram_id, course)
        if access["unlocked"]:
            return {"unlocked": True, "reason": "course", "course_title": course["title"]}
        return {"unlocked": False, "reason": "locked", "course_title": course["title"]}

    return {"unlocked": False, "reason": "locked", "course_title": None}


def get_control_tests_for_user(telegram_id: int):
    """Barcha faol nazorat testlarini, har biri uchun foydalanuvchining
    kirish huquqi bor-yo'qligini (tayinlash yoki kurs orqali) hisoblab qaytaradi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM tests
            WHERE is_control_test = 1 AND is_active = 1
            ORDER BY order_num ASC, id ASC
        """)
        rows = [dict(r) for r in cur.fetchall()]

    result = []
    for t in rows:
        access = compute_control_test_access(telegram_id, t)
        t["unlocked"] = access["unlocked"]
        t["access_reason"] = access["reason"]
        t["course_title"] = access["course_title"]
        t["question_count"] = count_test_questions(t["id"])
        result.append(t)
    return result


# ---------- NAZORAT TESTI — TALABALARNI TAYINLASH (admin) ----------

def assign_control_test_access(test_id: int, telegram_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO control_test_access (test_id, telegram_id) VALUES (?, ?)",
            (test_id, telegram_id)
        )
        conn.commit()


def revoke_control_test_access(test_id: int, telegram_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM control_test_access WHERE test_id = ? AND telegram_id = ?",
            (test_id, telegram_id)
        )
        conn.commit()


def get_control_test_access_list(test_id: int):
    """Shu nazorat testiga tayinlangan barcha talabalarni (ism/username bilan) qaytaradi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT ca.telegram_id as telegram_id, ca.assigned_at as assigned_at,
                   u.first_name as first_name, u.username as username
            FROM control_test_access ca
            LEFT JOIN users u ON u.telegram_id = ca.telegram_id
            WHERE ca.test_id = ?
            ORDER BY ca.assigned_at DESC
        """, (test_id,))
        return [dict(r) for r in cur.fetchall()]


def get_attempt_answers_grid(attempt_id: int):
    """Bitta urinishning har bir savoli bo'yicha to'g'ri/noto'g'ri holatini,
    savol tartib raqami bilan qaytaradi — natija jadvalini (savollar
    to'ri/noto'g'ri katakchalari) chizish uchun."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT q.order_num as order_num, ta.is_correct as is_correct
            FROM test_answers ta
            JOIN test_questions q ON q.id = ta.question_id
            WHERE ta.attempt_id = ?
            ORDER BY q.order_num ASC, ta.id ASC
        """, (attempt_id,))
        rows = [dict(r) for r in cur.fetchall()]
    return [{"question_number": i + 1, "is_correct": bool(r["is_correct"])} for i, r in enumerate(rows)]


def get_control_test_monthly_leaderboard(year: int, month: int, limit: int = 100):
    """Berilgan oy uchun nazorat testlari reytingini qaytaradi.
    Saralash mezoni: 1) o'rtacha foiz natija (yuqori — yaxshi),
    2) teng natijada — o'rtacha sarflangan vaqt (kam — yaxshi, ya'ni
    bir xil ball to'plagan ikki talaba orasida tezroq ishlagani yuqorida turadi)."""
    month_str = f"{year:04d}-{month:02d}"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT u.telegram_id as telegram_id, u.first_name as first_name,
                   AVG(CAST(a.score AS FLOAT) / NULLIF(a.total_questions, 0)) * 100 as avg_percent,
                   AVG((julianday(a.finished_at) - julianday(a.started_at)) * 86400) as avg_seconds,
                   COUNT(a.id) as attempts_count
            FROM test_attempts a
            JOIN tests t ON t.id = a.test_id
            JOIN users u ON u.telegram_id = a.telegram_id
            WHERE t.is_control_test = 1
              AND a.finished_at IS NOT NULL
              AND strftime('%Y-%m', a.finished_at) = ?
            GROUP BY u.telegram_id
            ORDER BY avg_percent DESC, avg_seconds ASC
            LIMIT ?
        """, (month_str, limit))
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            r["avg_percent"] = round(r["avg_percent"] or 0, 1)
            r["avg_seconds"] = round(r["avg_seconds"] or 0)
        return rows


def get_my_control_test_rank(telegram_id: int, year: int, month: int):
    """Foydalanuvchining shu oydagi nazorat testlari reytingidagi o'rnini
    topadi (agar u shu oy hech narsa topshirmagan bo'lsa — None)."""
    leaderboard = get_control_test_monthly_leaderboard(year, month, limit=100000)
    for idx, row in enumerate(leaderboard):
        if row["telegram_id"] == telegram_id:
            return {
                "rank": idx + 1,
                "avg_percent": row["avg_percent"],
                "avg_seconds": row["avg_seconds"],
                "attempts_count": row["attempts_count"],
                "total_participants": len(leaderboard),
            }
    return None
