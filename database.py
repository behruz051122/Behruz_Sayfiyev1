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
import json

from db_pool import get_connection, init_pool
from config import DB_PATH

# Bosh sahifa kartalarining STANDART (birinchi marta ishga tushganda
# to'ldiriladigan) qiymatlari — (card_key, title, subtitle, icon, order_num).
# card_key HECH QACHON o'zgarmaydi (frontend shu bo'yicha qaysi ekranga
# olib borishni aniqlaydi), qolgan maydonlar admin panelidan tahrirlanadi.
DASHBOARD_CARD_DEFAULTS = [
    ("courses", "📚 Kurslar", "NAZORATLI · MUSTAQIL · BEPUL", "🎓", 1),
    ("tests", "📝 Testlar", "DTM · MAVZULI · SERTIFIKAT", "📄", 2),
    ("rating", "🏆 Reyting", "SIZNING O'RNINGIZ", "🥇", 3),
    ("books", "📗 Kitoblar", "DO'KON · PROMOKODLAR", "📖", 4),
    ("games", "🎮 O'yinlar", "TEZ ORADA", "🕹️", 5),
    ("results", "🏆 Natijalar", "SERTIFIKAT NATIJALARI · FIKRLAR", "📈", 6),
]


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

        # Kunlik faollik ("streak") ustunlari — o'quvchi ketma-ket necha kun
        # ilovada faol bo'lganini kuzatish uchun. Eski bazalarda bu ustunlar
        # yo'q bo'lgani sababli ALTER TABLE orqali (xatoni jimgina o'tkazib
        # yuborib) qo'shamiz — boshqa joylarda ishlatilgan uslub bilan bir xil.
        for alter_sql in (
            "ALTER TABLE users ADD COLUMN current_streak INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN longest_streak INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN last_activity_date TEXT",
        ):
            try:
                cur.execute(alter_sql)
                conn.commit()
            except sqlite3.OperationalError:
                pass  # ustun allaqachon mavjud — muammo emas

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

        # Test "turi" — oddiy mavzuli testlardan tashqari, endi Attestatsiya
        # (o'qituvchilar uchun rasmiy attestatsiya sinovi, @biologiyamockbot
        # tahlili asosida qurilgan) ham shu "tests" jadvalidan foydalanadi.
        # 'practice' — oddiy/mavzuli test (standart), 'attestation' — Attestatsiya.
        # Kelajakda 'certificate' (Milliy sertifikat) uchun ham shu ustun ishlatiladi.
        try:
            cur.execute("ALTER TABLE tests ADD COLUMN test_kind TEXT DEFAULT 'practice'")
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

        # O'quvchi endi bitta savolga javobini ERKIN o'zgartira oladi (savollar
        # orasida ham erkin harakatlanadi) — shuning uchun bitta (urinish, savol)
        # juftligi uchun FAQAT BITTA javob qatori bo'lishi kerak (eskisi
        # yangisi bilan YANGILANADI, qayta qo'shilmaydi). Avval har bir
        # o'zgartirish YANGI qator sifatida qo'shilardi — bu endi noto'g'ri
        # (bir savol bir necha marta hisoblanib, ball noto'g'ri chiqishi
        # mumkin edi). Avval, agar eski (dublikat qatorli) ma'lumotlar bo'lsa,
        # ularni tozalab (har juftlik uchun faqat ENG OXIRGISINI qoldirib),
        # keyin UNIQUE indeks qo'yamiz — shundan keyin INSERT ... ON CONFLICT
        # DO UPDATE (upsert) ishlata olamiz.
        cur.execute("""
            DELETE FROM test_answers
            WHERE id NOT IN (SELECT MAX(id) FROM test_answers GROUP BY attempt_id, question_id)
        """)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_test_answers_attempt_question
            ON test_answers(attempt_id, question_id)
        """)

        # "Belgilash" (flag) — Attestatsiya testida talaba savolni "keyinroq
        # qaytaman" deb belgilashi mumkin (@biologiyamockbot'dagi kabi).
        # Javob berilmasdan ham belgilanishi mumkin bo'lgani uchun
        # test_answers'ning o'zida (selected_index bo'sh bo'lishi mumkin).
        try:
            cur.execute("ALTER TABLE test_answers ADD COLUMN is_flagged INTEGER DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

        # "E'tiroz bildirish" — talaba biror savolga e'tiroz/shikoyat
        # yozishi mumkin (@biologiyamockbot'dagi kabi), admin panelda
        # o'qituvchi bu e'tirozlarni ko'rib chiqadi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS question_objections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                telegram_id INTEGER NOT NULL,
                comment TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (attempt_id) REFERENCES test_attempts (id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES test_questions (id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            DELETE FROM simulator_answers
            WHERE id NOT IN (SELECT MAX(id) FROM simulator_answers GROUP BY attempt_id, question_id)
        """)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_simulator_answers_attempt_question
            ON simulator_answers(attempt_id, question_id)
        """)

        # ---------- Bosh sahifa kartalari (dashboard) ----------
        # Bosh sahifadagi 6 ta katakli menyu (Kurslar, Testlar, Reyting,
        # Kitoblar, O'yinlar, Natijalar) — har birining SARLAVHASI, TEG
        # matni va belgisi (emoji) shu jadvalda saqlanadi va admin panelidan
        # o'zgartiriladi. Qaysi ekranga olib borishi (nav) esa FUNKSIONAL
        # bog'lanish bo'lgani uchun frontend kodida qattiq belgilangan —
        # faqat KO'RINISHI (matn/belgi) shu yerdan boshqariladi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dashboard_cards (
                card_key TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                subtitle TEXT DEFAULT '',
                icon TEXT DEFAULT '✨',
                is_active INTEGER DEFAULT 1,
                order_num INTEGER DEFAULT 0
            )
        """)
        for card_key, title, subtitle, icon, order_num in DASHBOARD_CARD_DEFAULTS:
            cur.execute("""
                INSERT OR IGNORE INTO dashboard_cards (card_key, title, subtitle, icon, is_active, order_num)
                VALUES (?, ?, ?, ?, 1, ?)
            """, (card_key, title, subtitle, icon, order_num))

        # Coin berilgan har bir hodisaning VAQT tarixi — Reyting bo'limida
        # "Haftalik"/"Oylik" davr bo'yicha reyting hisoblash uchun kerak
        # (batafsili izoh add_coins() ichida).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS coin_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_coin_history_telegram_created
            ON coin_history(telegram_id, created_at)
        """)

        # ---------- O'YINLAR: 1x1 Battle (ELO reytingli, asinxron) ----------
        # "Asinxron" — ikkala o'yinchi BIR VAQTDA onlayn bo'lishi shart emas:
        # 1-o'yinchi "O'ynash"ni bosganda kutayotgan boshqa jang bo'lmasa,
        # yangi jang (savollar to'plami bilan) yaratiladi va DARHOL javob
        # beradi ("waiting" holatida qoladi); keyinroq 2-o'yinchi shu jangga
        # qo'shilib, xuddi shu savollarga javob beradi — shundan so'ng
        # natijalar taqqoslanib, ELO ikkalasi uchun ham yangilanadi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_battles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                question_ids TEXT NOT NULL,
                player1_telegram_id INTEGER NOT NULL,
                player1_score INTEGER,
                player1_time_seconds INTEGER,
                player1_finished_at TIMESTAMP,
                player2_telegram_id INTEGER,
                player2_score INTEGER,
                player2_time_seconds INTEGER,
                player2_finished_at TIMESTAMP,
                status TEXT DEFAULT 'waiting',
                winner_telegram_id INTEGER,
                player1_elo_before INTEGER,
                player1_elo_after INTEGER,
                player2_elo_before INTEGER,
                player2_elo_after INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP,
                notified INTEGER DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_game_battles_subject_status
            ON game_battles(subject, status)
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_ratings (
                telegram_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                elo INTEGER DEFAULT 1000,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0,
                PRIMARY KEY (telegram_id, subject)
            )
        """)

        # ---------- Sertifikatlar (kurs 100% tugallanganda) ----------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS certificates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                certificate_number TEXT UNIQUE NOT NULL,
                issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(telegram_id, course_id)
            )
        """)

        # ---------- Yutuq nishonlari (achievements) ----------
        # Nishon TA'RIFLARI (nomi, tavsifi, sharti) kodda — ACHIEVEMENT_DEFS
        # ro'yxatida — saqlanadi (hozircha admin panelidan tahrirlanmaydi,
        # eng muhim ~10 ta standart yutuq bilan boshlaymiz). Bu jadval
        # faqat KIM QACHON qaysi nishonni QO'LGA KIRITGANINI saqlaydi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                achievement_key TEXT NOT NULL,
                earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(telegram_id, achievement_key)
            )
        """)

        # ---------- Kitoblar do'koni (bosma kitoblar) ----------
        # E'TIBOR: bu "courses" jadvalidagi resource_type='book' (RAQAMLI
        # o'qish kontenti — bo'lim/dars strukturasi bilan) dan BUTUNLAY
        # ALOHIDA tushuncha — bu yerda BOSMA (pochta orqali yetkaziladigan)
        # kitoblar sotiladi. Hozircha to'lov tizimi (Payme/Click) ULANMAGAN
        # — "Xarid qilish" tugmasi shunchaki talabani shu kitobga biriktirilgan
        # (yoki bo'sh bo'lsa umumiy) admin Telegram kontaktiga olib boradi,
        # xarid o'sha yerda qo'lda kelishiladi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS book_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                subtitle TEXT DEFAULT '',
                description TEXT DEFAULT '',
                category TEXT DEFAULT '',
                price INTEGER DEFAULT 0,
                image_url TEXT,
                badge_text TEXT DEFAULT '',
                is_bundle INTEGER DEFAULT 0,
                contact_username TEXT DEFAULT '',
                order_num INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # "Video yechim" bog'lanishi — kitob mahsuloti (bosma) bilan
        # courses jadvalidagi biror kursni ("bo'lim") bog'lash uchun.
        # Talaba do'konda "Video yechim" tugmasini bossa, aynan shu
        # kursning ichiga (miniappda) olib boriladi. Eski bazalarda bu ustun
        # yo'q bo'lgani uchun ALTER TABLE orqali (xatoni jimgina o'tkazib
        # yuborib) qo'shamiz.
        try:
            cur.execute("ALTER TABLE book_products ADD COLUMN linked_course_id INTEGER")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

        # FAQ / Yordam bo'limi — tez-tez so'raladigan savol-javoblar, admin
        # paneldan to'liq boshqariladi (qo'shish/tahrirlash/o'chirish/tartib).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS faq_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                order_num INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # "Natijalar" — o'quvchilarning kurs/dars haqidagi fikri va
        # sertifikat (masalan Milliy sertifikat, DTM) natijalari. Bu — reyting
        # (leaderboard)dan BUTUNLAY ALOHIDA, admin qo'lda to'ldiradigan
        # "muvaffaqiyat hikoyalari" lentasi (Kelajak Mediklari botidagi
        # "Natijalar" bo'limi kabi). Reyting endi faqat bosh sahifadagi
        # "🏆 Reyting" kartasi orqali ochiladi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS student_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                subject TEXT DEFAULT '',
                image_url TEXT,
                result_text TEXT DEFAULT '',
                feedback_text TEXT DEFAULT '',
                order_num INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
    print("Baza tayyor (v5 — DTM simulyatori bilan): users, courses, paragraphs, lessons, "
          "lesson_progress, enrollments, referrals, tests, simulators.")


# ---------- DASHBOARD CARDS (bosh sahifa kartalari) ----------

def get_dashboard_cards(only_active: bool = False):
    """Bosh sahifadagi 6 ta katakli menyu kartalarini tartib bo'yicha
    qaytaradi. only_active=True bo'lsa, faqat admin "faol" deb belgilagan
    kartalar qaytadi (student-facing Mini App shu variantdan foydalanadi)."""
    with get_connection() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM dashboard_cards"
        if only_active:
            query += " WHERE is_active = 1"
        query += " ORDER BY order_num ASC, card_key ASC"
        cur.execute(query)
        return [dict(row) for row in cur.fetchall()]


def update_dashboard_card(card_key: str, data: dict):
    """Bitta kartaning sarlavha/teg/belgi/faollik/tartib qiymatlarini
    yangilaydi. card_key o'zi o'zgarmaydi (jadvalning asosiy kaliti)."""
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        allowed = ["title", "subtitle", "icon", "is_active", "order_num"]
        for key in allowed:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if fields:
            values.append(card_key)
            cur.execute(f"UPDATE dashboard_cards SET {', '.join(fields)} WHERE card_key = ?", values)
            conn.commit()


# ---------- YUTUQ NISHONLARI (achievements) ----------
#
# Har bir nishon: (key, title, description, icon, shart-funksiya). Shart-
# funksiya foydalanuvchi statistikasi (dict) qabul qilib, True/False
# qaytaradi. check_and_award_achievements() har safar muhim harakatdan
# keyin (dars ko'rish, test tugatish, Battle g'alaba, referal tasdiqlanishi)
# chaqiriladi — statistikani qayta hisoblab, hali berilmagan, LEKIN endi
# shartga mos nishonlarni avtomatik beradi.

ACHIEVEMENT_DEFS = [
    {"key": "first_lesson", "title": "Birinchi qadam", "description": "Birinchi darsni tomosha qildingiz",
     "icon": "🎬", "check": lambda s: s["lessons_watched"] >= 1},
    {"key": "lessons_10", "title": "Bilim ishqibozi", "description": "10 ta darsni tomosha qildingiz",
     "icon": "📚", "check": lambda s: s["lessons_watched"] >= 10},
    {"key": "lessons_50", "title": "Bilim changali", "description": "50 ta darsni tomosha qildingiz",
     "icon": "🎓", "check": lambda s: s["lessons_watched"] >= 50},
    {"key": "first_test", "title": "Birinchi sinov", "description": "Birinchi testni yakunladingiz",
     "icon": "📝", "check": lambda s: s["tests_finished"] >= 1},
    {"key": "tests_10", "title": "Test ustasi", "description": "10 ta testni yakunladingiz",
     "icon": "🏅", "check": lambda s: s["tests_finished"] >= 10},
    {"key": "perfect_score", "title": "Mukammal natija", "description": "Biror testda 100% natija ko'rsatdingiz",
     "icon": "💯", "check": lambda s: s["has_perfect_score"]},
    {"key": "control_test_done", "title": "Nazoratdan o'tdi", "description": "Birinchi nazorat testini topshirdingiz",
     "icon": "🎯", "check": lambda s: s["control_tests_finished"] >= 1},
    {"key": "first_battle_win", "title": "Jangchi", "description": "Birinchi Battle g'alabangiz",
     "icon": "⚔️", "check": lambda s: s["battle_wins"] >= 1},
    {"key": "battle_wins_10", "title": "Chempion", "description": "10 ta Battle g'alaba qozondingiz",
     "icon": "🏆", "check": lambda s: s["battle_wins"] >= 10},
    {"key": "coins_50", "title": "Tejamkor", "description": "50 ta coin to'pladingiz",
     "icon": "🪙", "check": lambda s: s["coins"] >= 50},
    {"key": "referrals_5", "title": "Do'stlar yetakchisi", "description": "5 ta do'stingizni taklif qildingiz",
     "icon": "🎁", "check": lambda s: s["confirmed_referrals"] >= 5},
    {"key": "streak_3", "title": "Qizigan boshlanish", "description": "3 kun ketma-ket faol bo'ldingiz",
     "icon": "🔥", "check": lambda s: s["longest_streak"] >= 3},
    {"key": "streak_7", "title": "Haftalik intizom", "description": "7 kun ketma-ket faol bo'ldingiz",
     "icon": "🔥", "check": lambda s: s["longest_streak"] >= 7},
    {"key": "streak_30", "title": "Temir intizom", "description": "30 kun ketma-ket faol bo'ldingiz",
     "icon": "🔥", "check": lambda s: s["longest_streak"] >= 30},
]


def _gather_achievement_stats(telegram_id: int) -> dict:
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) as c FROM lesson_progress WHERE telegram_id = ?", (telegram_id,))
        lessons_watched = cur.fetchone()["c"]

        cur.execute("""
            SELECT COUNT(*) as c FROM test_attempts ta JOIN tests t ON t.id = ta.test_id
            WHERE ta.telegram_id = ? AND ta.finished_at IS NOT NULL AND t.is_control_test = 0
        """, (telegram_id,))
        tests_finished = cur.fetchone()["c"]

        cur.execute("""
            SELECT COUNT(*) as c FROM test_attempts ta JOIN tests t ON t.id = ta.test_id
            WHERE ta.telegram_id = ? AND ta.finished_at IS NOT NULL AND t.is_control_test = 1
        """, (telegram_id,))
        control_tests_finished = cur.fetchone()["c"]

        cur.execute("""
            SELECT COUNT(*) as c FROM test_attempts
            WHERE telegram_id = ? AND finished_at IS NOT NULL AND total_questions > 0 AND score = total_questions
        """, (telegram_id,))
        has_perfect_score = cur.fetchone()["c"] > 0

        cur.execute("SELECT COALESCE(SUM(wins), 0) as w FROM game_ratings WHERE telegram_id = ?", (telegram_id,))
        battle_wins = cur.fetchone()["w"]

        cur.execute("SELECT coins, longest_streak FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        coins = row["coins"] if row else 0
        longest_streak = (row["longest_streak"] or 0) if row else 0

        cur.execute("SELECT COUNT(*) as c FROM referrals WHERE referrer_telegram_id = ? AND confirmed = 1", (telegram_id,))
        confirmed_referrals = cur.fetchone()["c"]

        return {
            "lessons_watched": lessons_watched,
            "tests_finished": tests_finished,
            "control_tests_finished": control_tests_finished,
            "has_perfect_score": has_perfect_score,
            "battle_wins": battle_wins,
            "coins": coins,
            "confirmed_referrals": confirmed_referrals,
            "longest_streak": longest_streak,
        }


def check_and_award_achievements(telegram_id: int):
    """Statistikani qayta hisoblab, hali berilmagan lekin endi shartga mos
    nishonlarni beradi. Natija: YANGI berilgan nishonlar ro'yxati (bo'sh
    bo'lishi ham mumkin)."""
    stats = _gather_achievement_stats(telegram_id)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT achievement_key FROM user_achievements WHERE telegram_id = ?", (telegram_id,))
        already_earned = {r["achievement_key"] for r in cur.fetchall()}

        newly_earned = []
        for ach in ACHIEVEMENT_DEFS:
            if ach["key"] in already_earned:
                continue
            try:
                qualifies = ach["check"](stats)
            except Exception:
                qualifies = False
            if qualifies:
                cur.execute(
                    "INSERT OR IGNORE INTO user_achievements (telegram_id, achievement_key) VALUES (?, ?)",
                    (telegram_id, ach["key"])
                )
                newly_earned.append(ach)
        if newly_earned:
            conn.commit()
        return newly_earned


def get_user_achievements(telegram_id: int):
    """Barcha nishonlarni (qo'lga kiritilgan yoki yo'q) qaytaradi — Profil
    ekranida to'liq "nishonlar devori" ko'rsatish uchun."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT achievement_key, earned_at FROM user_achievements WHERE telegram_id = ?", (telegram_id,))
        earned_map = {r["achievement_key"]: r["earned_at"] for r in cur.fetchall()}

    result = []
    for ach in ACHIEVEMENT_DEFS:
        result.append({
            "key": ach["key"], "title": ach["title"], "description": ach["description"], "icon": ach["icon"],
            "earned": ach["key"] in earned_map,
            "earned_at": earned_map.get(ach["key"]),
        })
    return result


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


def record_daily_activity(telegram_id: int) -> dict:
    """O'quvchi biror "faol" harakat qilganda (dars ko'rish, test/simulyator
    yakunlash, o'yin o'ynash) chaqiriladi va kunlik "streak"ni yangilaydi:

    - Bugun allaqachon faol bo'lgan bo'lsa — hech narsa o'zgarmaydi.
    - Kecha faol bo'lgan bo'lsa — streak +1 (ketma-ketlik davom etadi).
    - Aks holda (uzilish yoki birinchi marta) — streak 1 dan boshlanadi.

    Sana UTC bo'yicha ('YYYY-MM-DD') solishtiriladi — bazadagi boshqa
    vaqt hisoblari (masalan coin_history) bilan bir xil andozada.
    """
    today = datetime.datetime.utcnow().date()
    today_str = today.isoformat()
    yesterday_str = (today - datetime.timedelta(days=1)).isoformat()

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT current_streak, longest_streak, last_activity_date FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        row = cur.fetchone()
        if row is None:
            return {"current_streak": 0, "longest_streak": 0}

        current_streak = row["current_streak"] or 0
        longest_streak = row["longest_streak"] or 0
        last_date = row["last_activity_date"]

        if last_date == today_str:
            pass  # bugun allaqachon hisoblangan
        elif last_date == yesterday_str:
            current_streak += 1
        else:
            current_streak = 1

        longest_streak = max(longest_streak, current_streak)

        cur.execute(
            "UPDATE users SET current_streak = ?, longest_streak = ?, last_activity_date = ? WHERE telegram_id = ?",
            (current_streak, longest_streak, today_str, telegram_id)
        )
        conn.commit()

    return {"current_streak": current_streak, "longest_streak": longest_streak}


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
        # Har bir coin berilishini VAQTI bilan birga alohida yozib boramiz
        # ("umumiy hisob"dan farqli) — shu orqali Reyting bo'limida
        # "Haftalik"/"Oylik" kabi DAVR bo'yicha reyting hisoblash mumkin
        # bo'ladi (users.coins faqat "Butun davr" umumiy yig'indisini bilar
        # edi, qachon berilganini bilmasdi).
        cur.execute(
            "INSERT INTO coin_history (telegram_id, amount) VALUES (?, ?)",
            (telegram_id, amount)
        )
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
    newly_confirmed = False
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT referrer_telegram_id, confirmed FROM referrals WHERE referred_telegram_id = ?", (referred_id,))
        row = cur.fetchone()
        if row is None:
            return None
        if row["confirmed"] == 0:
            cur.execute("UPDATE referrals SET confirmed = 1 WHERE referred_telegram_id = ?", (referred_id,))
            conn.commit()
            newly_confirmed = True
        referrer_id = row["referrer_telegram_id"]

    if newly_confirmed:
        check_and_award_achievements(referrer_id)
    return referrer_id


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


# ---------- KITOBLAR DO'KONI (bosma kitoblar, courses'dan alohida) ----------

def get_book_products(category: str = None, only_active: bool = True):
    with get_connection() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM book_products WHERE 1=1"
        params = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if only_active:
            query += " AND is_active = 1"
        query += " ORDER BY order_num ASC, id DESC"
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def get_book_product(product_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM book_products WHERE id = ?", (product_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_book_product(data: dict) -> int:
    linked_course_id = data.get("linked_course_id")
    linked_course_id = int(linked_course_id) if linked_course_id not in (None, "", 0, "0") else None
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO book_products (title, subtitle, description, category, price,
                image_url, badge_text, is_bundle, contact_username, order_num, is_active,
                linked_course_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("title", ""), data.get("subtitle", ""), data.get("description", ""),
            data.get("category", ""), int(data.get("price", 0) or 0),
            data.get("image_url") or None, data.get("badge_text", ""),
            int(data.get("is_bundle", 0)), data.get("contact_username", ""),
            int(data.get("order_num", 0)), int(data.get("is_active", 1)),
            linked_course_id
        ))
        conn.commit()
        return cur.lastrowid


def update_book_product(product_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        allowed = ["title", "subtitle", "description", "category", "price", "image_url",
                   "badge_text", "is_bundle", "contact_username", "order_num", "is_active",
                   "linked_course_id"]
        for key in allowed:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key] if data[key] != "" else ("" if key in ("subtitle", "description", "category", "badge_text", "contact_username") else None))
        if fields:
            values.append(product_id)
            cur.execute(f"UPDATE book_products SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_book_product(product_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM book_products WHERE id = ?", (product_id,))
        conn.commit()


# ---------- FAQ / YORDAM BO'LIMI ----------

def get_faq_items(only_active: bool = True):
    with get_connection() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM faq_items"
        if only_active:
            query += " WHERE is_active = 1"
        query += " ORDER BY order_num ASC, id ASC"
        cur.execute(query)
        return [dict(row) for row in cur.fetchall()]


def get_faq_item(faq_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM faq_items WHERE id = ?", (faq_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_faq_item(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO faq_items (question, answer, order_num, is_active)
            VALUES (?, ?, ?, ?)
        """, (
            data.get("question", ""), data.get("answer", ""),
            int(data.get("order_num", 0)), int(data.get("is_active", 1))
        ))
        conn.commit()
        return cur.lastrowid


def update_faq_item(faq_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        allowed = ["question", "answer", "order_num", "is_active"]
        for key in allowed:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if fields:
            values.append(faq_id)
            cur.execute(f"UPDATE faq_items SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_faq_item(faq_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM faq_items WHERE id = ?", (faq_id,))
        conn.commit()


# ---------- NATIJALAR (o'quvchi fikri + sertifikat natijalari) ----------

def get_student_results(only_active: bool = True):
    with get_connection() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM student_results"
        if only_active:
            query += " WHERE is_active = 1"
        query += " ORDER BY order_num ASC, id DESC"
        cur.execute(query)
        return [dict(row) for row in cur.fetchall()]


def get_student_result(result_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM student_results WHERE id = ?", (result_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_student_result(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO student_results (student_name, subject, image_url, result_text,
                feedback_text, order_num, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("student_name", ""), data.get("subject", ""),
            data.get("image_url") or None, data.get("result_text", ""),
            data.get("feedback_text", ""),
            int(data.get("order_num", 0)), int(data.get("is_active", 1))
        ))
        conn.commit()
        return cur.lastrowid


def update_student_result(result_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        allowed = ["student_name", "subject", "image_url", "result_text",
                   "feedback_text", "order_num", "is_active"]
        for key in allowed:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if fields:
            values.append(result_id)
            cur.execute(f"UPDATE student_results SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_student_result(result_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM student_results WHERE id = ?", (result_id,))
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
    record_daily_activity(telegram_id)
    check_and_award_achievements(telegram_id)
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


# ---------- SERTIFIKATLAR (kurs 100% tugallanganda) ----------

def get_course_completion(telegram_id: int, course_id: int) -> dict:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as c FROM lessons l JOIN paragraphs p ON p.id = l.paragraph_id
            WHERE p.course_id = ?
        """, (course_id,))
        total = cur.fetchone()["c"]
    watched = len(get_watched_lesson_ids(telegram_id, course_id))
    percent = round((watched / total) * 100) if total > 0 else 0
    return {
        "total_lessons": total, "watched_lessons": watched,
        "percent": percent, "is_complete": total > 0 and watched >= total,
    }


def _generate_certificate_number(course_id: int) -> str:
    year = datetime.datetime.utcnow().year
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM certificates")
        seq = cur.fetchone()["c"] + 1
    return f"KM-{year}-{course_id:03d}{seq:05d}"


def get_or_issue_certificate(telegram_id: int, course_id: int):
    """Kurs 100% tugallangan bo'lsagina sertifikat 'beradi' — ALLAQACHON
    berilgan bo'lsa, ESKISINI qaytaradi (raqami o'zgarmaydi, qayta-qayta
    yuklab olganda ham HAR DOIM bir xil sertifikat raqami chiqishi kerak)."""
    completion = get_course_completion(telegram_id, course_id)
    if not completion["is_complete"]:
        return None

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM certificates WHERE telegram_id = ? AND course_id = ?",
            (telegram_id, course_id)
        )
        row = cur.fetchone()
        if row:
            return dict(row)

        cert_number = _generate_certificate_number(course_id)
        cur.execute(
            "INSERT INTO certificates (telegram_id, course_id, certificate_number) VALUES (?, ?, ?)",
            (telegram_id, course_id, cert_number)
        )
        conn.commit()
        cur.execute("SELECT * FROM certificates WHERE id = ?", (cur.lastrowid,))
        return dict(cur.fetchone())


def get_my_certificates(telegram_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.*, co.title as course_title, co.subject as course_subject
            FROM certificates c JOIN courses co ON co.id = c.course_id
            WHERE c.telegram_id = ?
            ORDER BY c.issued_at DESC
        """, (telegram_id,))
        return [dict(r) for r in cur.fetchall()]


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

# "Haftalik" — so'nggi 7 kun (aylanma oyna), "Oylik" — joriy oyning 1-kunidan
# beri (taqvim oyi, nazorat testi oylik reytingi bilan bir xil mantiq).
# "Butun davr" uchun users.coins jadvalidagi UMUMIY yig'indi ishlatiladi —
# chunki coin_history faqat shu funksiya qo'shilgan kundan boshlab yozib
# borilyapti, undan oldingi coinlar tarixda "yo'qolib qolmasin" uchun.
_PERIOD_SQL_FILTERS = {
    "week": "created_at >= datetime('now', '-7 days')",
    "month": "created_at >= datetime('now', 'start of month')",
}


def get_leaderboard(limit: int = 100, period: str = "all"):
    with get_connection() as conn:
        cur = conn.cursor()
        if period in _PERIOD_SQL_FILTERS:
            cur.execute(f"""
                SELECT u.telegram_id, u.first_name, COALESCE(SUM(ch.amount), 0) as coins
                FROM coin_history ch
                JOIN users u ON u.telegram_id = ch.telegram_id
                WHERE ch.{_PERIOD_SQL_FILTERS[period]}
                GROUP BY u.telegram_id
                HAVING coins > 0
                ORDER BY coins DESC, u.id ASC
                LIMIT ?
            """, (limit,))
        else:
            cur.execute("""
                SELECT telegram_id, first_name, coins FROM users
                WHERE coins > 0 ORDER BY coins DESC, id ASC LIMIT ?
            """, (limit,))
        return [dict(r) for r in cur.fetchall()]


def get_user_rank(telegram_id: int, period: str = "all"):
    with get_connection() as conn:
        cur = conn.cursor()
        if period in _PERIOD_SQL_FILTERS:
            cur.execute(f"""
                SELECT COALESCE(SUM(amount), 0) as coins FROM coin_history
                WHERE telegram_id = ? AND {_PERIOD_SQL_FILTERS[period]}
            """, (telegram_id,))
            row = cur.fetchone()
            my_coins = row["coins"] if row else 0
            if my_coins <= 0:
                return None
            cur.execute(f"""
                SELECT COUNT(*) as c FROM (
                    SELECT telegram_id, SUM(amount) as total FROM coin_history
                    WHERE {_PERIOD_SQL_FILTERS[period]}
                    GROUP BY telegram_id
                    HAVING total > ?
                )
            """, (my_coins,))
            return cur.fetchone()["c"] + 1

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


def get_all_tests(subject: str = None, only_active: bool = True, include_control: bool = True, test_kind: str = None):
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
        if test_kind:
            if test_kind == "practice":
                # Eski (test_kind ustuni qo'shilishidan oldingi) testlar NULL
                # bo'lib qoladi — ularni ham "oddiy" hisoblaymiz.
                query += " AND (test_kind IS NULL OR test_kind = 'practice')"
            else:
                query += " AND test_kind = ?"
                params.append(test_kind)
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
            INSERT INTO tests (subject, title, difficulty, time_limit_seconds, order_num, is_active, is_control_test, course_id, test_kind)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("subject", ""), data.get("title", ""), difficulty, int(time_limit),
            int(data.get("order_num", 0)), int(data.get("is_active", 1)),
            int(data.get("is_control_test", 0)), data.get("course_id") or None,
            data.get("test_kind") or "practice"
        ))
        conn.commit()
        return cur.lastrowid


def update_test(test_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        for key in ["subject", "title", "difficulty", "time_limit_seconds", "order_num", "is_active",
                    "is_control_test", "course_id", "test_kind"]:
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
    """Javobni tekshiradi va yozib qo'yadi (yoki — agar bu savolga bu urinishda
    ALLAQACHON javob berilgan bo'lsa, uni YANGILAYDI, chunki o'quvchi savollar
    orasida erkin harakatlanib, javobini istalgancha o'zgartirishi mumkin).
    Agar bu savolga birinchi marta to'g'ri javob berilgan bo'lsa 1 coin
    beradi. {'correct': bool, 'correct_index': int, 'coin_awarded': bool}
    qaytaradi. Urinishning umumiy bali (score) BU YERDA emas — yakunlash
    (finish_attempt) vaqtida, barcha javoblar asosida qayta hisoblanadi."""
    question = get_question(question_id)
    if not question:
        return {"correct": False, "correct_index": None, "coin_awarded": False}

    is_correct = int(selected_index) == int(question["correct_index"])

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO test_answers (attempt_id, question_id, selected_index, is_correct)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(attempt_id, question_id)
            DO UPDATE SET selected_index = excluded.selected_index, is_correct = excluded.is_correct
        """, (attempt_id, question_id, selected_index, 1 if is_correct else 0))
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


def set_answer_flag(attempt_id: int, question_id: int, flagged: bool):
    """Attestatsiya testida "Belgilash" — savolni javob berilgan-berilmaganidan
    qat'i nazar "keyinroq qaytaman" deb belgilash/bekor qilish. Agar bu
    savolga hali umuman javob yozilmagan bo'lsa ham ishlashi kerak, shuning
    uchun selected_index/is_correct'ni YO'QOTMASDAN (mavjud bo'lsa saqlab
    qolib) faqat is_flagged ustunini upsert qilamiz."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO test_answers (attempt_id, question_id, selected_index, is_correct, is_flagged)
            VALUES (?, ?, NULL, 0, ?)
            ON CONFLICT(attempt_id, question_id)
            DO UPDATE SET is_flagged = excluded.is_flagged
        """, (attempt_id, question_id, 1 if flagged else 0))
        conn.commit()
    return {"flagged": bool(flagged)}


def get_attempt_flags(attempt_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT question_id FROM test_answers
            WHERE attempt_id = ? AND is_flagged = 1
        """, (attempt_id,))
        return [r["question_id"] for r in cur.fetchall()]


# ---------- E'TIROZ BILDIRISH (savolga shikoyat) ----------

def create_objection(attempt_id: int, question_id: int, telegram_id: int, comment: str) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO question_objections (attempt_id, question_id, telegram_id, comment)
            VALUES (?, ?, ?, ?)
        """, (attempt_id, question_id, telegram_id, comment))
        conn.commit()
        return cur.lastrowid


def get_objections(status: str = None):
    with get_connection() as conn:
        cur = conn.cursor()
        query = """
            SELECT o.id as id, o.attempt_id as attempt_id, o.question_id as question_id,
                   o.telegram_id as telegram_id, o.comment as comment, o.status as status,
                   o.created_at as created_at,
                   q.question_text as question_text, t.id as test_id, t.title as test_title,
                   u.first_name as first_name, u.username as username
            FROM question_objections o
            LEFT JOIN test_questions q ON q.id = o.question_id
            LEFT JOIN tests t ON t.id = q.test_id
            LEFT JOIN users u ON u.telegram_id = o.telegram_id
            WHERE 1=1
        """
        params = []
        if status:
            query += " AND o.status = ?"
            params.append(status)
        query += " ORDER BY o.created_at DESC"
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]


def update_objection_status(objection_id: int, status: str):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE question_objections SET status = ? WHERE id = ?", (status, objection_id))
        conn.commit()


def finish_attempt(attempt_id: int):
    """Urinishni yakunlaydi. Ball (score) aynan shu yerda, BARCHA saqlangan
    javoblar bo'yicha qayta hisoblanadi — chunki javoblar erkin o'zgartirilishi
    mumkin edi, oraliqda saqlangan "score" ustuni ishonchli emas."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM test_answers WHERE attempt_id = ? AND is_correct = 1", (attempt_id,))
        score = cur.fetchone()["c"]
        cur.execute("UPDATE test_attempts SET score = ?, finished_at = CURRENT_TIMESTAMP WHERE id = ?", (score, attempt_id))
        conn.commit()
        cur.execute("SELECT * FROM test_attempts WHERE id = ?", (attempt_id,))
        row = cur.fetchone()
        result = dict(row) if row else None
    if result:
        record_daily_activity(result["telegram_id"])
        check_and_award_achievements(result["telegram_id"])
    return result


def is_first_finished_attempt(attempt_id: int) -> bool:
    """Nazorat testida talaba mashq uchun xohlagancha qayta ishlashi mumkin,
    LEKIN oylik REYTINGGA faqat shu (talaba, test) juftligi bo'yicha ENG
    BIRINCHI yakunlangan urinish hisoblanadi (keyingi urinishlar shaxsiy
    mashq — reytingga ta'sir qilmaydi). Shu funksiya berilgan urinish aynan
    o'sha "hisoblanadigan" birinchi urinishmi ekanini tekshiradi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT telegram_id, test_id FROM test_attempts WHERE id = ?", (attempt_id,))
        row = cur.fetchone()
        if not row:
            return False
        cur.execute("""
            SELECT id FROM test_attempts
            WHERE telegram_id = ? AND test_id = ? AND finished_at IS NOT NULL
            ORDER BY started_at ASC, id ASC LIMIT 1
        """, (row["telegram_id"], row["test_id"]))
        first = cur.fetchone()
        return bool(first and first["id"] == attempt_id)


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


# ---------- O'YINLAR: 1x1 BATTLE (ELO reytingli, asinxron) ----------
#
# Savollar ALOHIDA bank sifatida saqlanmaydi — o'qituvchi allaqachon
# to'ldirgan "Testlar" bo'limidagi savol bazasidan, FAN bo'yicha tasodifiy
# tanlab olinadi. Shu sababli Battle rejimi ishlashi uchun o'qituvchi hech
# qanday QO'SHIMCHA kontent tayyorlashi shart emas.

BATTLE_QUESTIONS_PER_ROUND = 5
BATTLE_ELO_K_FACTOR = 32
BATTLE_STARTING_ELO = 1000

ELO_TIERS = [
    (0, "Temir"), (900, "Bronza"), (1100, "Kumush"),
    (1300, "Oltin"), (1500, "Platina"), (1700, "Olmos"),
]


def elo_tier_name(elo: int) -> str:
    name = ELO_TIERS[0][1]
    for threshold, tier in ELO_TIERS:
        if elo >= threshold:
            name = tier
    return name


def get_battle_subjects_with_pool():
    """Battle o'ynash mumkin bo'lgan fanlar ro'yxatini qaytaradi — ya'ni
    kamida BATTLE_QUESTIONS_PER_ROUND ta savoli bor fanlar (aks holda
    o'yin savolsiz qolib, buzilib qoladi)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.subject as subject, COUNT(q.id) as cnt
            FROM tests t JOIN test_questions q ON q.test_id = t.id
            WHERE t.is_active = 1
            GROUP BY t.subject
            HAVING cnt >= ?
        """, (BATTLE_QUESTIONS_PER_ROUND,))
        return [dict(r) for r in cur.fetchall()]


def _pick_random_question_ids(subject: str, count: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT q.id FROM test_questions q
            JOIN tests t ON t.id = q.test_id
            WHERE t.subject = ? AND t.is_active = 1
            ORDER BY RANDOM() LIMIT ?
        """, (subject, count))
        return [r["id"] for r in cur.fetchall()]


def get_or_create_rating(telegram_id: int, subject: str) -> dict:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM game_ratings WHERE telegram_id = ? AND subject = ?", (telegram_id, subject))
        row = cur.fetchone()
        if row:
            return dict(row)
        cur.execute(
            "INSERT INTO game_ratings (telegram_id, subject, elo) VALUES (?, ?, ?)",
            (telegram_id, subject, BATTLE_STARTING_ELO)
        )
        conn.commit()
        return {"telegram_id": telegram_id, "subject": subject, "elo": BATTLE_STARTING_ELO,
                "wins": 0, "losses": 0, "draws": 0}


def join_or_create_battle(telegram_id: int, subject: str) -> dict:
    """Shu fan bo'yicha kutayotgan (2-o'yinchisiz) jang bo'lsa (va u SHU
    o'yinchining o'zi yaratmagan bo'lsa) — o'shanga 2-o'yinchi sifatida
    qo'shiladi. Bo'lmasa, yangi jang (1-o'yinchi sifatida, yangi tasodifiy
    savollar bilan) yaratadi. Natija: {"battle_id", "role", "question_ids"}"""
    get_or_create_rating(telegram_id, subject)  # reyting yozuvi oldindan mavjud bo'lishini ta'minlaydi

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM game_battles
            WHERE subject = ? AND status = 'waiting' AND player1_telegram_id != ?
            ORDER BY created_at ASC LIMIT 1
        """, (subject, telegram_id))
        waiting = cur.fetchone()

        if waiting:
            cur.execute(
                "UPDATE game_battles SET player2_telegram_id = ? WHERE id = ?",
                (telegram_id, waiting["id"])
            )
            conn.commit()
            return {
                "battle_id": waiting["id"],
                "role": "player2",
                "question_ids": json.loads(waiting["question_ids"]),
            }

        question_ids = _pick_random_question_ids(subject, BATTLE_QUESTIONS_PER_ROUND)
        cur.execute("""
            INSERT INTO game_battles (subject, question_ids, player1_telegram_id, status)
            VALUES (?, ?, ?, 'waiting')
        """, (subject, json.dumps(question_ids), telegram_id))
        conn.commit()
        return {"battle_id": cur.lastrowid, "role": "player1", "question_ids": question_ids}


def _calc_elo(rating_a: int, rating_b: int, score_a: float) -> int:
    """Standart ELO formulasi. score_a: 1 (g'alaba), 0.5 (durrang), 0 (mag'lubiyat)."""
    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    return round(rating_a + BATTLE_ELO_K_FACTOR * (score_a - expected_a))


def submit_battle_result(battle_id: int, telegram_id: int, score: int, time_seconds: int):
    """O'yinchining natijasini yozadi. Ikkala o'yinchi ham tugatgan bo'lsa,
    g'olibni aniqlab, ELO'ni ikkalasi uchun ham yangilaydi va jangni
    'finished' deb belgilaydi. Natija: yangilangan battle dict."""
    players_to_check_achievements = []
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM game_battles WHERE id = ?", (battle_id,))
        battle = cur.fetchone()
        if not battle:
            return None
        battle = dict(battle)

        if battle["player1_telegram_id"] == telegram_id:
            cur.execute("""
                UPDATE game_battles SET player1_score = ?, player1_time_seconds = ?,
                    player1_finished_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (score, time_seconds, battle_id))
        elif battle["player2_telegram_id"] == telegram_id:
            cur.execute("""
                UPDATE game_battles SET player2_score = ?, player2_time_seconds = ?,
                    player2_finished_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (score, time_seconds, battle_id))
        else:
            return None
        conn.commit()

        cur.execute("SELECT * FROM game_battles WHERE id = ?", (battle_id,))
        battle = dict(cur.fetchone())

        both_finished = (
            battle["player1_finished_at"] is not None
            and battle["player2_telegram_id"] is not None
            and battle["player2_finished_at"] is not None
        )
        if both_finished and battle["status"] == "waiting":
            p1, p2 = battle["player1_telegram_id"], battle["player2_telegram_id"]
            r1 = get_or_create_rating(p1, battle["subject"])
            r2 = get_or_create_rating(p2, battle["subject"])

            s1, t1 = battle["player1_score"], battle["player1_time_seconds"]
            s2, t2 = battle["player2_score"], battle["player2_time_seconds"]
            if s1 > s2 or (s1 == s2 and t1 < t2):
                winner, score_a = p1, 1
            elif s2 > s1 or (s2 == s1 and t2 < t1):
                winner, score_a = p2, 0
            else:
                winner, score_a = None, 0.5

            new_elo1 = _calc_elo(r1["elo"], r2["elo"], score_a)
            new_elo2 = _calc_elo(r2["elo"], r1["elo"], 1 - score_a)

            cur.execute("""
                UPDATE game_battles SET status = 'finished', winner_telegram_id = ?,
                    player1_elo_before = ?, player1_elo_after = ?,
                    player2_elo_before = ?, player2_elo_after = ?,
                    finished_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (winner, r1["elo"], new_elo1, r2["elo"], new_elo2, battle_id))

            cur.execute("""
                UPDATE game_ratings SET elo = ?,
                    wins = wins + ?, losses = losses + ?, draws = draws + ?
                WHERE telegram_id = ? AND subject = ?
            """, (
                new_elo1,
                1 if winner == p1 else 0, 1 if winner == p2 else 0, 1 if winner is None else 0,
                p1, battle["subject"]
            ))
            cur.execute("""
                UPDATE game_ratings SET elo = ?,
                    wins = wins + ?, losses = losses + ?, draws = draws + ?
                WHERE telegram_id = ? AND subject = ?
            """, (
                new_elo2,
                1 if winner == p2 else 0, 1 if winner == p1 else 0, 1 if winner is None else 0,
                p2, battle["subject"]
            ))
            conn.commit()

            cur.execute("SELECT * FROM game_battles WHERE id = ?", (battle_id,))
            battle = dict(cur.fetchone())
            players_to_check_achievements = [p1, p2]

    # Yutuq tekshiruvi ATAYLAB yuqoridagi 'with' bloki (va uning ulanishi)
    # yopilgandan KEYIN qilinadi — check_and_award_achievements() o'zi ham
    # pool'dan ulanish so'raydi, ikkalasini bir vaqtda ochiq ushlab turish
    # shart emas.
    for player_id in players_to_check_achievements:
        record_daily_activity(player_id)
        check_and_award_achievements(player_id)

    return battle


def get_battle(battle_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM game_battles WHERE id = ?", (battle_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_my_battles(telegram_id: int, limit: int = 20):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM game_battles
            WHERE player1_telegram_id = ? OR player2_telegram_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (telegram_id, telegram_id, limit))
        return [dict(r) for r in cur.fetchall()]


def get_my_ratings(telegram_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM game_ratings WHERE telegram_id = ?", (telegram_id,))
        return [dict(r) for r in cur.fetchall()]


def get_battles_needing_notification():
    """Endigina 'finished' bo'lgan, lekin ikkala o'yinchiga ham hali
    Telegram orqali xabar YUBORILMAGAN janglar — bot.py'dagi fon vazifasi
    (background loop) shularni topib, xabar yuborgach 'notified'ga
    belgilaydi (batafsili izoh bot.py'da)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM game_battles WHERE status = 'finished' AND notified = 0")
        return [dict(r) for r in cur.fetchall()]


def mark_battle_notified(battle_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE game_battles SET notified = 1 WHERE id = ?", (battle_id,))
        conn.commit()


def get_battle_leaderboard(subject: str, limit: int = 50):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT gr.telegram_id, u.first_name, gr.elo, gr.wins, gr.losses, gr.draws
            FROM game_ratings gr
            JOIN users u ON u.telegram_id = gr.telegram_id
            WHERE gr.subject = ?
            ORDER BY gr.elo DESC LIMIT ?
        """, (subject, limit))
        return [dict(r) for r in cur.fetchall()]


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
            ON CONFLICT(attempt_id, question_id)
            DO UPDATE SET selected_index = excluded.selected_index, is_correct = excluded.is_correct
        """, (attempt_id, question_id, selected_index, 1 if is_correct else 0))
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
    """Ball (score) shu yerda, BARCHA saqlangan javoblar bo'yicha qayta
    hisoblanadi — sabab test attempts bilan bir xil (javoblar erkin
    o'zgartirilishi mumkin edi)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM simulator_answers WHERE attempt_id = ? AND is_correct = 1", (attempt_id,))
        score = cur.fetchone()["c"]
        cur.execute("UPDATE simulator_attempts SET score = ?, finished_at = CURRENT_TIMESTAMP WHERE id = ?", (score, attempt_id))
        conn.commit()
        cur.execute("SELECT * FROM simulator_attempts WHERE id = ?", (attempt_id,))
        row = cur.fetchone()
        result = dict(row) if row else None
    if result:
        record_daily_activity(result["telegram_id"])
        check_and_award_achievements(result["telegram_id"])
    return result


def get_simulator_attempt_grid(attempt_id: int):
    """Simulyator urinishidagi HAR BIR savol (javob berilgan yoki
    berilmagan — o'quvchi endi savollarni o'tkazib yuborishi ham mumkin)
    bo'yicha to'g'ri/noto'g'ri/javobsiz holatini qaytaradi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT saq.order_num as order_num, sa.selected_index as selected_index, sa.is_correct as is_correct
            FROM simulator_attempt_questions saq
            LEFT JOIN simulator_answers sa ON sa.question_id = saq.question_id AND sa.attempt_id = saq.attempt_id
            WHERE saq.attempt_id = ?
            ORDER BY saq.order_num ASC
        """, (attempt_id,))
        rows = [dict(r) for r in cur.fetchall()]
    return [
        {
            "question_number": i + 1,
            "answered": r["selected_index"] is not None,
            "is_correct": bool(r["is_correct"]) if r["selected_index"] is not None else None,
        }
        for i, r in enumerate(rows)
    ]


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


def get_control_test_results(test_id: int):
    """Berilgan BITTA nazorat testini ishlagan har bir talabaning necha
    to'g'ri javob berganini qaytaradi. Talaba testni bir necha marta qayta
    ishlagan bo'lsa ham, faqat REYTINGGA hisoblangan (eng birinchi
    yakunlangan) urinishi ko'rsatiladi — qayta urinishlar (mashq) bu yerda
    hisobga olinmaydi. Natija — ball bo'yicha kamayish tartibida."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            WITH first_attempts AS (
                SELECT a.*,
                       ROW_NUMBER() OVER (
                           PARTITION BY a.telegram_id
                           ORDER BY a.started_at ASC, a.id ASC
                       ) as rn
                FROM test_attempts a
                WHERE a.test_id = ? AND a.finished_at IS NOT NULL
            )
            SELECT u.telegram_id as telegram_id, u.first_name as first_name, u.username as username,
                   fa.score as score, fa.total_questions as total_questions, fa.finished_at as finished_at
            FROM first_attempts fa
            JOIN users u ON u.telegram_id = fa.telegram_id
            WHERE fa.rn = 1
            ORDER BY fa.score DESC, fa.finished_at ASC
        """, (test_id,))
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            r["percent"] = round((r["score"] / r["total_questions"]) * 100, 1) if r["total_questions"] else 0
        return rows


def get_attempt_rank(attempt_id: int):
    """Berilgan (Attestatsiya) urinish uchun — shu variantni ishlagan
    barcha talabalar orasida nechanchi o'rinda ekanini qaytaradi
    (@biologiyamockbot'dagi "80-o'rin / 90 talaba ichida" bilan bir xil
    mantiq). get_control_test_results bilan bir xil "faqat birinchi
    yakunlangan urinish hisoblanadi" qoidasidan foydalanadi. Agar bu urinish
    reytingga hisoblanmasa (mashq/qayta urinish) — None qaytaradi."""
    attempt = get_attempt(attempt_id)
    if not attempt or not attempt.get("finished_at"):
        return None
    if not is_first_finished_attempt(attempt_id):
        return None
    ranked = get_control_test_results(attempt["test_id"])
    for i, r in enumerate(ranked):
        if r["telegram_id"] == attempt["telegram_id"]:
            return {"rank": i + 1, "total": len(ranked)}
    return None


def get_attempt_answers_grid(attempt_id: int):
    """Bitta urinishning HAR BIR savoli (javob berilgan yoki berilmagan —
    o'quvchi endi savollar orasida erkin harakatlanib, ba'zilarini
    o'tkazib yuborishi ham mumkin) bo'yicha to'g'ri/noto'g'ri/javobsiz
    holatini, savol tartib raqami bilan qaytaradi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT test_id FROM test_attempts WHERE id = ?", (attempt_id,))
        attempt_row = cur.fetchone()
        if not attempt_row:
            return []
        test_id = attempt_row["test_id"]
        cur.execute("""
            SELECT q.order_num as order_num, ta.selected_index as selected_index, ta.is_correct as is_correct
            FROM test_questions q
            LEFT JOIN test_answers ta ON ta.question_id = q.id AND ta.attempt_id = ?
            WHERE q.test_id = ?
            ORDER BY q.order_num ASC, q.id ASC
        """, (attempt_id, test_id))
        rows = [dict(r) for r in cur.fetchall()]
    return [
        {
            "question_number": i + 1,
            "answered": r["selected_index"] is not None,
            "is_correct": bool(r["is_correct"]) if r["selected_index"] is not None else None,
        }
        for i, r in enumerate(rows)
    ]


def get_control_test_monthly_leaderboard(year: int, month: int, limit: int = 100):
    """Berilgan oy uchun nazorat testlari reytingini qaytaradi.
    Talaba bitta nazorat testini MASHQ uchun xohlagancha qayta ishlashi
    mumkin — lekin REYTINGGA har (talaba, test) juftligi bo'yicha faqat ENG
    BIRINCHI yakunlangan urinish kiritiladi (ROW_NUMBER() bilan tanlanadi).
    Keyingi qayta urinishlar shaxsiy mashq hisoblanadi va natijaga ta'sir
    qilmaydi. Saralash mezoni: 1) o'rtacha foiz natija (yuqori — yaxshi),
    2) teng natijada — o'rtacha sarflangan vaqt (kam — yaxshi, ya'ni
    bir xil ball to'plagan ikki talaba orasida tezroq ishlagani yuqorida turadi)."""
    month_str = f"{year:04d}-{month:02d}"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            WITH first_attempts AS (
                SELECT a.*,
                       ROW_NUMBER() OVER (
                           PARTITION BY a.telegram_id, a.test_id
                           ORDER BY a.started_at ASC, a.id ASC
                       ) as rn
                FROM test_attempts a
                JOIN tests t ON t.id = a.test_id
                WHERE t.is_control_test = 1 AND a.finished_at IS NOT NULL
            )
            SELECT u.telegram_id as telegram_id, u.first_name as first_name,
                   AVG(CAST(fa.score AS FLOAT) / NULLIF(fa.total_questions, 0)) * 100 as avg_percent,
                   AVG((julianday(fa.finished_at) - julianday(fa.started_at)) * 86400) as avg_seconds,
                   COUNT(fa.id) as attempts_count
            FROM first_attempts fa
            JOIN users u ON u.telegram_id = fa.telegram_id
            WHERE fa.rn = 1
              AND strftime('%Y-%m', fa.finished_at) = ?
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
